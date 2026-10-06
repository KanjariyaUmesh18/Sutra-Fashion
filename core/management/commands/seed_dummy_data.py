"""
SUTRA — Dummy Data Seeder
=========================
Debugging ke liye 10 categories aur 25 products ka dummy data banata hai,
sath me har product ke liye placeholder images (PIL se generate) bhi
create karta hai taaki image-normalisation pipeline test ho sake.

Usage:
    python manage.py seed_dummy_data
    python manage.py seed_dummy_data --flush   # purana catalogue data clear karke fresh seed karega
"""

import io
import math
import random

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Category, Product, ProductImage

from PIL import Image, ImageDraw, ImageFont


CATEGORY_DEFS = [
    ("Sarees", "#B8395F"),
    ("Lehengas", "#7A3B69"),
    ("Kurtis", "#3B6E7A"),
    ("Salwar Suits", "#8A6D3B"),
    ("Gowns", "#4B3B8A"),
    ("Dupattas", "#3B8A5E"),
    ("Ethnic Jackets", "#8A3B3B"),
    ("Blouses", "#3B5E8A"),
    ("Palazzo Sets", "#6E8A3B"),
    ("Bridal Wear", "#8A3B6E"),
]

ADJECTIVES = [
    "Royal", "Elegant", "Classic", "Festive", "Graceful", "Vintage",
    "Regal", "Charming", "Radiant", "Traditional", "Modern", "Divine",
]

FABRICS = [
    "Silk", "Georgette", "Chiffon", "Cotton", "Velvet", "Organza",
    "Banarasi", "Chanderi", "Net", "Crepe",
]

COLOR_CHOICES = [
    "Maroon", "Gold", "Emerald Green", "Royal Blue", "Blush Pink",
    "Ivory", "Mustard Yellow", "Wine Red", "Peacock Blue", "Coral",
]

SIZE_SETS = [
    "XS,S,M,L,XL",
    "S,M,L,XL,XXL",
    "Free Size",
    "34,36,38,40,42",
]

BADGES = ["None", "Bestseller", "New", "Sale"]


def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _lighten(rgb, amount=0.35):
    return tuple(int(c + (255 - c) * amount) for c in rgb)


def _darken(rgb, amount=0.35):
    return tuple(int(c * (1 - amount)) for c in rgb)


def _vertical_gradient(size, top_rgb, bottom_rgb):
    """Simple top-to-bottom gradient background."""
    w, h = size
    img = Image.new("RGB", size, top_rgb)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _embroidery_dots(draw, cx, cy, radius, color, count=14):
    """Small ring of dots to suggest embroidery / zari work."""
    for i in range(count):
        angle = (2 * math.pi / count) * i
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=color)


# ── Garment silhouette drawers ──────────────────────────────────────────
# Each function draws a simple, recognisable garment shape onto the canvas
# so placeholder images look like an actual product photo card rather than
# a flat colour swatch.

def _draw_saree(draw, w, h, fg, accent):
    body_left = w * 0.32
    body_right = w * 0.68
    draw.polygon(
        [(body_left, h * 0.18), (body_right, h * 0.18),
         (w * 0.72, h * 0.9), (w * 0.28, h * 0.9)],
        fill=fg,
    )
    draw.polygon(
        [(w * 0.30, h * 0.20), (w * 0.62, h * 0.15),
         (w * 0.78, h * 0.55), (w * 0.46, h * 0.62)],
        fill=accent,
    )
    for i in range(6):
        x = body_left + (body_right - body_left) * (i / 5)
        draw.line([(x, h * 0.2), (x - (w * 0.02), h * 0.88)], fill=_darken(fg, 0.15), width=3)
    _embroidery_dots(draw, w * 0.5, h * 0.22, w * 0.16, accent, count=10)


def _draw_lehenga(draw, w, h, fg, accent):
    draw.polygon(
        [(w * 0.38, h * 0.15), (w * 0.62, h * 0.15),
         (w * 0.66, h * 0.38), (w * 0.34, h * 0.38)],
        fill=accent,
    )
    draw.polygon(
        [(w * 0.36, h * 0.38), (w * 0.64, h * 0.38),
         (w * 0.92, h * 0.92), (w * 0.08, h * 0.92)],
        fill=fg,
    )
    for i in range(7):
        x0 = w * 0.36 + (w * 0.28) * (i / 6)
        x1 = w * 0.08 + (w * 0.84) * (i / 6)
        draw.line([(x0, h * 0.4), (x1, h * 0.9)], fill=_darken(fg, 0.15), width=2)


def _draw_kurti(draw, w, h, fg, accent):
    draw.polygon(
        [(w * 0.35, h * 0.2), (w * 0.65, h * 0.2),
         (w * 0.78, h * 0.85), (w * 0.22, h * 0.85)],
        fill=fg,
    )
    draw.ellipse([w * 0.44, h * 0.15, w * 0.56, h * 0.24], fill=accent)
    draw.polygon([(w * 0.35, h * 0.22), (w * 0.18, h * 0.4), (w * 0.28, h * 0.44), (w * 0.38, h * 0.28)], fill=fg)
    draw.polygon([(w * 0.65, h * 0.22), (w * 0.82, h * 0.4), (w * 0.72, h * 0.44), (w * 0.62, h * 0.28)], fill=fg)
    _embroidery_dots(draw, w * 0.5, h * 0.32, w * 0.10, accent, count=8)


def _draw_salwar_suit(draw, w, h, fg, accent):
    draw.polygon(
        [(w * 0.34, h * 0.16), (w * 0.66, h * 0.16),
         (w * 0.72, h * 0.55), (w * 0.28, h * 0.55)],
        fill=fg,
    )
    draw.polygon([(w * 0.30, h * 0.55), (w * 0.5, h * 0.55), (w * 0.44, h * 0.92), (w * 0.24, h * 0.92)], fill=accent)
    draw.polygon([(w * 0.70, h * 0.55), (w * 0.5, h * 0.55), (w * 0.56, h * 0.92), (w * 0.76, h * 0.92)], fill=accent)
    _embroidery_dots(draw, w * 0.5, h * 0.26, w * 0.10, _lighten(fg, 0.3), count=6)


def _draw_gown(draw, w, h, fg, accent):
    draw.polygon(
        [(w * 0.4, h * 0.16), (w * 0.6, h * 0.16),
         (w * 0.62, h * 0.45), (w * 0.38, h * 0.45)],
        fill=accent,
    )
    draw.polygon(
        [(w * 0.38, h * 0.45), (w * 0.62, h * 0.45),
         (w * 0.85, h * 0.95), (w * 0.15, h * 0.95)],
        fill=fg,
    )
    for i in range(5):
        x = w * 0.2 + (w * 0.6) * (i / 4)
        draw.line([(w * 0.5, h * 0.45), (x, h * 0.94)], fill=_lighten(fg, 0.15), width=2)


def _draw_dupatta(draw, w, h, fg, accent):
    points = []
    for i in range(30):
        t = i / 29
        x = w * 0.5 + math.sin(t * math.pi * 1.6) * w * 0.22
        y = h * 0.15 + t * h * 0.7
        points.append((x - w * 0.08, y))
    for i in range(29, -1, -1):
        t = i / 29
        x = w * 0.5 + math.sin(t * math.pi * 1.6) * w * 0.22
        y = h * 0.15 + t * h * 0.7
        points.append((x + w * 0.08, y))
    draw.polygon(points, fill=fg)
    draw.rectangle([w * 0.34, h * 0.12, w * 0.58, h * 0.19], fill=accent)
    draw.rectangle([w * 0.34, h * 0.80, w * 0.58, h * 0.87], fill=accent)


def _draw_ethnic_jacket(draw, w, h, fg, accent):
    draw.rectangle([w * 0.42, h * 0.2, w * 0.58, h * 0.8], fill=_lighten(fg, 0.4))
    draw.polygon([(w * 0.22, h * 0.18), (w * 0.46, h * 0.18), (w * 0.4, h * 0.82), (w * 0.16, h * 0.82)], fill=fg)
    draw.polygon([(w * 0.78, h * 0.18), (w * 0.54, h * 0.18), (w * 0.6, h * 0.82), (w * 0.84, h * 0.82)], fill=fg)
    draw.polygon([(w * 0.38, h * 0.18), (w * 0.5, h * 0.28), (w * 0.62, h * 0.18)], fill=accent)
    _embroidery_dots(draw, w * 0.25, h * 0.5, w * 0.05, accent, count=6)
    _embroidery_dots(draw, w * 0.75, h * 0.5, w * 0.05, accent, count=6)


def _draw_blouse(draw, w, h, fg, accent):
    draw.polygon(
        [(w * 0.36, h * 0.28), (w * 0.64, h * 0.28),
         (w * 0.70, h * 0.62), (w * 0.30, h * 0.62)],
        fill=fg,
    )
    draw.polygon([(w * 0.36, h * 0.3), (w * 0.22, h * 0.42), (w * 0.3, h * 0.46), (w * 0.4, h * 0.34)], fill=fg)
    draw.polygon([(w * 0.64, h * 0.3), (w * 0.78, h * 0.42), (w * 0.7, h * 0.46), (w * 0.6, h * 0.34)], fill=fg)
    draw.ellipse([w * 0.46, h * 0.25, w * 0.54, h * 0.33], fill=accent)
    _embroidery_dots(draw, w * 0.5, h * 0.45, w * 0.12, accent, count=10)


def _draw_palazzo_set(draw, w, h, fg, accent):
    draw.polygon([(w * 0.38, h * 0.18), (w * 0.62, h * 0.18), (w * 0.65, h * 0.4), (w * 0.35, h * 0.4)], fill=accent)
    draw.polygon([(w * 0.28, h * 0.42), (w * 0.5, h * 0.42), (w * 0.46, h * 0.92), (w * 0.1, h * 0.92)], fill=fg)
    draw.polygon([(w * 0.72, h * 0.42), (w * 0.5, h * 0.42), (w * 0.54, h * 0.92), (w * 0.9, h * 0.92)], fill=fg)


def _draw_bridal_wear(draw, w, h, fg, accent):
    draw.polygon([(w * 0.38, h * 0.14), (w * 0.62, h * 0.14), (w * 0.68, h * 0.4), (w * 0.32, h * 0.4)], fill=accent)
    draw.polygon(
        [(w * 0.34, h * 0.4), (w * 0.66, h * 0.4),
         (w * 0.94, h * 0.94), (w * 0.06, h * 0.94)],
        fill=fg,
    )
    draw.rectangle([w * 0.06, h * 0.86, w * 0.94, h * 0.94], fill=accent)
    _embroidery_dots(draw, w * 0.5, h * 0.22, w * 0.14, _lighten(accent, 0.3), count=14)
    for i in range(9):
        x = w * 0.1 + (w * 0.8) * (i / 8)
        draw.ellipse([x - 5, h * 0.9 - 5, x + 5, h * 0.9 + 5], fill=_lighten(accent, 0.4))


SILHOUETTE_DRAWERS = {
    "Sarees": _draw_saree,
    "Lehengas": _draw_lehenga,
    "Kurtis": _draw_kurti,
    "Salwar Suits": _draw_salwar_suit,
    "Gowns": _draw_gown,
    "Dupattas": _draw_dupatta,
    "Ethnic Jackets": _draw_ethnic_jacket,
    "Blouses": _draw_blouse,
    "Palazzo Sets": _draw_palazzo_set,
    "Bridal Wear": _draw_bridal_wear,
}


def make_placeholder_image(text: str, hex_color: str, category_name: str = "", size=(1000, 1250)) -> ContentFile:
    """
    Illustrated placeholder: gradient background + a recognisable garment
    silhouette for the given category + a bottom label bar with the text.
    Looks like a stylised product card instead of a flat colour swatch.
    """
    base_rgb = _hex_to_rgb(hex_color)
    top_bg = _lighten(base_rgb, 0.55)
    bottom_bg = _lighten(base_rgb, 0.15)

    img = _vertical_gradient(size, top_bg, bottom_bg)
    draw = ImageDraw.Draw(img)

    w, h = size
    fg_color = _darken(base_rgb, 0.05)
    accent_color = _lighten(base_rgb, 0.25)

    drawer = SILHOUETTE_DRAWERS.get(category_name)
    if drawer:
        drawer(draw, w, h, fg_color, accent_color)
    else:
        draw.polygon(
            [(w * 0.35, h * 0.2), (w * 0.65, h * 0.2), (w * 0.8, h * 0.9), (w * 0.2, h * 0.9)],
            fill=fg_color,
        )

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
    except Exception:
        font = ImageFont.load_default()

    bar_h = int(h * 0.09)
    draw.rectangle([0, h - bar_h, w, h], fill=(0, 0, 0))
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((w - text_w) / 2, h - bar_h + (bar_h - text_h) / 2 - bbox[1]),
        text,
        fill="white",
        font=font,
    )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return ContentFile(buf.read(), name=f"{text.replace(' ', '_').lower()}.jpg")


class Command(BaseCommand):
    help = "Seed the database with 10 dummy categories and 25 dummy products (with images) for debugging."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing products/categories before seeding fresh dummy data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Clearing existing Product/Category data...")
            Product.objects.all().delete()
            Category.objects.all().delete()

        self.stdout.write("Creating 10 categories...")
        categories = []
        for i, (name, color) in enumerate(CATEGORY_DEFS):
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={"sort_order": i, "is_active": True},
            )
            if created or not category.image:
                category.image = make_placeholder_image(name, color, category_name=name, size=(700, 700))
                category.save()
            categories.append((category, color))
            self.stdout.write(f"  {'created' if created else 'exists'}: {name}")

        self.stdout.write("Creating 25 products...")
        product_count = 0
        sku_counter = 1000

        # Ensure a roughly even spread of 25 products across 10 categories
        cat_cycle = (categories * 3)[:25]

        for idx, (category, color) in enumerate(cat_cycle, start=1):
            adjective = random.choice(ADJECTIVES)
            fabric = random.choice(FABRICS)
            singular = category.name.rstrip("s") if category.name.endswith("s") else category.name
            name = f"{adjective} {fabric} {singular} #{idx}"

            price = random.choice([1499, 1999, 2499, 2999, 3499, 4499, 5999, 7999, 9999])
            has_discount = random.random() < 0.5
            original_price = round(price * random.uniform(1.15, 1.6), -2) if has_discount else None

            sku_counter += 1
            sku = f"SUT-{sku_counter}"

            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults=dict(
                    category=category,
                    name=name,
                    description=(
                        f"Handpicked {fabric.lower()} {singular.lower()} featuring intricate detailing, "
                        f"perfect for festive and special occasions. Comfortable fit with premium finish."
                    ),
                    price=price,
                    original_price=original_price,
                    stock=random.randint(0, 50),
                    sizes=random.choice(SIZE_SETS),
                    colors=",".join(random.sample(COLOR_CHOICES, k=random.randint(2, 4))),
                    is_active=True,
                    is_featured=random.random() < 0.3,
                    badge=random.choice(BADGES),
                    free_shipping=random.random() < 0.7,
                    shipping_charge=0 if random.random() < 0.7 else random.choice([49, 99, 149]),
                    cash_on_delivery=True,
                ),
            )

            if created:
                # Attach 1-2 placeholder images per product
                num_images = random.choice([1, 2])
                for img_idx in range(num_images):
                    label = f"{category.name} {idx}-{img_idx + 1}"
                    ProductImage.objects.create(
                        product=product,
                        image=make_placeholder_image(label, color, category_name=category.name),
                        alt_text=name,
                        is_primary=(img_idx == 0),
                        sort_order=img_idx,
                    )
                product_count += 1
                self.stdout.write(f"  created: {name} ({sku})")
            else:
                self.stdout.write(f"  exists: {name} ({sku})")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Categories: {Category.objects.count()}, "
            f"Products: {Product.objects.count()} (newly created: {product_count})."
        ))
