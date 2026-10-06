"""
SUTRA — Management Command: normalise_images
=============================================
Retroactively normalises all existing ProductImage and Category images in the
database using the same pipeline that runs automatically on new uploads.

Usage:
    python manage.py normalise_images             # process everything
    python manage.py normalise_images --dry-run   # report only, no writes
    python manage.py normalise_images --products  # product images only
    python manage.py normalise_images --categories # category images only

This command is idempotent — safe to run multiple times.  Already-normalised
images (exactly 800×1000 for products, 600×600 for categories) are skipped
unless --force is passed.
"""

import os
import sys

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from core.image_utils import (
    normalise_product_image,
    normalise_category_image,
    delete_image_file,
    PRODUCT_TARGET_WIDTH,
    PRODUCT_TARGET_HEIGHT,
    CATEGORY_TARGET_WIDTH,
    CATEGORY_TARGET_HEIGHT,
)
from core.models import ProductImage, Category


class Command(BaseCommand):
    help = "Retroactively normalise all existing product and category images."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Report what would be done without writing any files.",
        )
        parser.add_argument(
            '--products',
            action='store_true',
            help="Process ProductImage records only.",
        )
        parser.add_argument(
            '--categories',
            action='store_true',
            help="Process Category images only.",
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help="Re-process images even if they are already at the correct dimensions.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        products_only = options['products']
        categories_only = options['categories']
        force = options['force']

        # Default: process both unless a flag restricts it
        do_products = products_only or (not products_only and not categories_only)
        do_categories = categories_only or (not products_only and not categories_only)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no files will be modified.\n"))

        if do_products:
            self._process_product_images(dry_run, force)

        if do_categories:
            self._process_category_images(dry_run, force)

    def _process_product_images(self, dry_run: bool, force: bool):
        from PIL import Image as PILImage

        qs = ProductImage.objects.select_related('product').all()
        total = qs.count()
        self.stdout.write(f"\nProcessing {total} ProductImage records…")

        processed = skipped = errors = 0

        for pi in qs:
            if not pi.image:
                self.stdout.write(f"  [SKIP] ProductImage #{pi.pk} — no file attached.")
                skipped += 1
                continue

            try:
                path = pi.image.path
            except Exception:
                self.stdout.write(f"  [SKIP] ProductImage #{pi.pk} — file path unavailable.")
                skipped += 1
                continue

            if not os.path.isfile(path):
                self.stdout.write(
                    self.style.WARNING(
                        f"  [MISSING] ProductImage #{pi.pk}: {pi.image.name}"
                    )
                )
                skipped += 1
                continue

            # Check if already at target dimensions
            if not force:
                try:
                    with PILImage.open(path) as img:
                        if img.size == (PRODUCT_TARGET_WIDTH, PRODUCT_TARGET_HEIGHT):
                            skipped += 1
                            continue
                except Exception:
                    pass  # Can't open — attempt normalisation anyway

            self.stdout.write(f"  [PROCESS] ProductImage #{pi.pk}: {pi.image.name}")

            if dry_run:
                processed += 1
                continue

            try:
                with open(path, 'rb') as f:
                    result = normalise_product_image(f)

                # Build new filename
                base = os.path.splitext(os.path.basename(pi.image.name))[0]
                new_name = f"{base}.jpg"

                # Delete old file before replacing
                delete_image_file(pi.image)

                # Save the new normalised content
                pi.image.save(new_name, ContentFile(result.read()), save=False)
                # Use update() to avoid re-triggering the model's save() pipeline
                ProductImage.objects.filter(pk=pi.pk).update(image=pi.image.name)
                processed += 1

            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  [ERROR] ProductImage #{pi.pk}: {exc}")
                )
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  Done — processed: {processed}, skipped: {skipped}, errors: {errors}"
            )
        )

    def _process_category_images(self, dry_run: bool, force: bool):
        from PIL import Image as PILImage

        qs = Category.objects.exclude(image='').exclude(image__isnull=True)
        total = qs.count()
        self.stdout.write(f"\nProcessing {total} Category image records…")

        processed = skipped = errors = 0

        for cat in qs:
            if not cat.image:
                skipped += 1
                continue

            try:
                path = cat.image.path
            except Exception:
                skipped += 1
                continue

            if not os.path.isfile(path):
                self.stdout.write(
                    self.style.WARNING(f"  [MISSING] Category #{cat.pk}: {cat.image.name}")
                )
                skipped += 1
                continue

            if not force:
                try:
                    with PILImage.open(path) as img:
                        if img.size == (CATEGORY_TARGET_WIDTH, CATEGORY_TARGET_HEIGHT):
                            skipped += 1
                            continue
                except Exception:
                    pass

            self.stdout.write(f"  [PROCESS] Category #{cat.pk}: {cat.name}")

            if dry_run:
                processed += 1
                continue

            try:
                with open(path, 'rb') as f:
                    result = normalise_category_image(f)

                base = os.path.splitext(os.path.basename(cat.image.name))[0]
                new_name = f"{base}.jpg"

                delete_image_file(cat.image)
                cat.image.save(new_name, ContentFile(result.read()), save=False)
                Category.objects.filter(pk=cat.pk).update(image=cat.image.name)
                processed += 1

            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  [ERROR] Category #{cat.pk}: {exc}")
                )
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  Done — processed: {processed}, skipped: {skipped}, errors: {errors}"
            )
        )
