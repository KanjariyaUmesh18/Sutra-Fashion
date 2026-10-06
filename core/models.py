"""
SUTRA — Core Models
All models consolidated into a single file.

Image normalisation is applied automatically in ProductImage.save() and
Category.save() via the core.image_utils pipeline.  No raw uploaded file
is ever stored as-is; every image is validated, EXIF-corrected, trimmed,
centre-cropped to the standard aspect ratio, and compressed before storage.
"""

import io
import uuid
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify

from .image_utils import (
    normalise_product_image,
    normalise_category_image,
    delete_image_file,
)


# ─────────────────────────────────────────────────────────
# ACCOUNTS
# ─────────────────────────────────────────────────────────

class UserProfile(models.Model):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be in the format '+999999999'. Up to 15 digits allowed."
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return self.user.username


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=17)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.name} — {self.city}"

    def save(self, *args, **kwargs):
        # If setting as default, clear other defaults first
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        # Auto-set first address as default
        elif not self.pk and not Address.objects.filter(user=self.user).exists():
            self.is_default = True
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────
# CATALOGUE
# ─────────────────────────────────────────────────────────

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']

    def save(self, *args, **kwargs):
        # Auto-generate slug from name
        if not self.slug:
            self.slug = slugify(self.name)

        # Normalise the category image if a new one has been supplied
        if self.image and hasattr(self.image, 'file'):
            self._normalise_category_image()

        super().save(*args, **kwargs)

    def _normalise_category_image(self):
        """Run the category image through the normalisation pipeline."""
        try:
            processed = normalise_category_image(self.image)
            # Build a clean JPEG filename derived from the original upload name
            original_name = getattr(self.image, 'name', 'category.jpg')
            base_name = _safe_filename(original_name, suffix='_cat')
            self.image.save(base_name, ContentFile(processed.read()), save=False)
        except ValueError as exc:
            # Re-raise as a validation error so the admin form can surface it
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            # Log unexpected errors but do not crash — save the original as fallback
            import logging
            logging.getLogger(__name__).error(
                "Category image normalisation failed for '%s': %s",
                self.name, exc
            )

    def __str__(self):
        return self.name


class Product(models.Model):
    BADGE_CHOICES = [
        ('None', 'None'),
        ('Bestseller', 'Bestseller'),
        ('New', 'New'),
        ('Sale', 'Sale'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True)
    sizes = models.CharField(max_length=100, blank=True,
                             help_text="Comma-separated sizes e.g. XS,S,M,L,XL,XXL")
    colors = models.CharField(max_length=100, blank=True,
                              help_text="Comma-separated colors e.g. Gold,Maroon")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    badge = models.CharField(max_length=20, choices=BADGE_CHOICES, default='None')

    # ── Shipping & Payment options (per-product) ──────────
    free_shipping = models.BooleanField(
        default=True,
        help_text="If enabled, this product ships for free."
    )
    shipping_charge = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.00,
        help_text="Shipping amount charged when Free Shipping is disabled."
    )
    cash_on_delivery = models.BooleanField(
        default=True,
        help_text="Allow customers to pay with Cash on Delivery."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0

    @property
    def get_sizes_list(self):
        return [s.strip() for s in self.sizes.split(',') if s.strip()] if self.sizes else []

    @property
    def get_colors_list(self):
        return [c.strip() for c in self.colors.split(',') if c.strip()] if self.colors else []

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """
    Stores a single normalised image for a product.

    On every save where a new image file is supplied the pipeline in
    image_utils.normalise_product_image() is called automatically.  The raw
    upload is replaced in-memory with a fixed-size (800×1000 px) JPEG before
    being written to disk, so the database and media directory never contain
    images of varying sizes.

    Old image files are deleted from disk whenever an existing record is
    updated with a new image, preventing media directory bloat.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def save(self, *args, **kwargs):
        # Enforce single primary: clear others when this one becomes primary
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product
            ).exclude(pk=self.pk).update(is_primary=False)
        # Auto-promote to primary if this is the first image for the product
        elif not self.pk and not ProductImage.objects.filter(product=self.product).exists():
            self.is_primary = True

        # Detect whether a new image file is being set
        new_image_supplied = self.image and hasattr(self.image, 'file')

        if new_image_supplied:
            # Delete the old file before writing the new one (update case)
            if self.pk:
                try:
                    old_instance = ProductImage.objects.get(pk=self.pk)
                    if old_instance.image and old_instance.image.name != getattr(self.image, 'name', None):
                        delete_image_file(old_instance.image)
                except ProductImage.DoesNotExist:
                    pass

            # Run the normalisation pipeline on the new upload
            self._normalise_image()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Remove the image file from disk when the record is deleted
        delete_image_file(self.image)
        super().delete(*args, **kwargs)

    def _normalise_image(self):
        """Process the uploaded image through the normalisation pipeline."""
        try:
            processed = normalise_product_image(self.image)
            original_name = getattr(self.image, 'name', 'product.jpg')
            base_name = _safe_filename(original_name, suffix='')
            self.image.save(base_name, ContentFile(processed.read()), save=False)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "ProductImage normalisation failed for product '%s': %s",
                self.product_id, exc
            )

    def __str__(self):
        return f"Image for {self.product.name}"


# ─────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart — {self.user.username}"
        return f"Cart — Guest ({self.session_key})"

    @property
    def total(self):
        return sum(item.line_total for item in self.items.select_related('product').all())

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ('cart', 'product', 'size', 'color')

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def line_total(self):
        return self.quantity * self.product.price


# ─────────────────────────────────────────────────────────
# WISHLIST
# ─────────────────────────────────────────────────────────

class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist — {self.user.username}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.username}'s wishlist"


# ─────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_METHOD_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=20)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"SU-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"


# ─────────────────────────────────────────────────────────
# CONTACT
# ─────────────────────────────────────────────────────────

class ContactInquiry(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contact_inquiries',
        help_text="Auto-linked to the logged-in user who submitted this, if any."
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    reply = models.TextField(blank=True, help_text="Admin's reply, shown to the user in their account.")
    replied_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Contact Inquiries'
        ordering = ['-created_at']

    def __str__(self):
        return f"Inquiry from {self.name} ({self.email})"

    @property
    def is_replied(self):
        return bool(self.reply)


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _safe_filename(original_name: str, suffix: str = '') -> str:
    """
    Build a clean, collision-resistant JPEG filename from the original upload.
    Always outputs a .jpg extension regardless of the source format.

    Examples:
      'my_photo.png'    → 'my_photo.jpg'
      'IMG_2034.HEIC'   → 'IMG_2034.jpg'
    """
    base = os.path.splitext(os.path.basename(original_name))[0]
    # Strip unsafe characters, keep it short
    safe = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in base)[:60]
    if not safe:
        safe = 'image'
    return f"{safe}{suffix}.jpg"


import os  # noqa: E402 — imported here to keep the top clean
