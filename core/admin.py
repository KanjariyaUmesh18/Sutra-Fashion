"""
SUTRA — Django Admin Configuration
All models registered with rich admin panels.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, Address,
    Category, Product, ProductImage,
    Cart, CartItem,
    Wishlist, WishlistItem,
    Order, OrderItem,
    ContactInquiry,
)

admin.site.site_header = "SUTRA Admin"
admin.site.site_title = "SUTRA"
admin.site.index_title = "Store Administration"


# ─────────────────────────────────────────────────────────
# ACCOUNTS
# ─────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'city', 'state', 'is_default']
    list_filter = ['state', 'is_default']
    search_fields = ['user__username', 'name', 'city']


# ─────────────────────────────────────────────────────────
# CATALOGUE
# ─────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'sort_order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'price', 'stock', 'is_active', 'is_featured', 'badge',
        'free_shipping', 'shipping_charge', 'cash_on_delivery', 'created_at',
    ]
    list_filter = ['is_active', 'is_featured', 'badge', 'category', 'free_shipping', 'cash_on_delivery']
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active', 'is_featured', 'stock']
    ordering = ['-created_at']
    fieldsets = (
        ('Basic Info', {
            'fields': ('category', 'name', 'slug', 'description'),
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'original_price', 'stock', 'sku'),
        }),
        ('Variants', {
            'fields': ('sizes', 'colors'),
        }),
        ('Shipping & Payment', {
            'fields': ('free_shipping', 'shipping_charge', 'cash_on_delivery'),
            'description': 'Configure how this product ships and whether Cash on Delivery is allowed.',
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'badge'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


# ─────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_count', 'total', 'updated_at']
    inlines = [CartItemInline]
    readonly_fields = ['created_at', 'updated_at']


# ─────────────────────────────────────────────────────────
# WISHLIST
# ─────────────────────────────────────────────────────────

class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    inlines = [WishlistItemInline]


# ─────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'shipping_name',
        'status', 'payment_method', 'payment_status', 'total', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'payment_status']
    search_fields = ['order_number', 'shipping_name', 'user__email']
    inlines = [OrderItemInline]
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['user', 'subtotal', 'total']
        return self.readonly_fields


# ─────────────────────────────────────────────────────────
# CONTACT
# ─────────────────────────────────────────────────────────

@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'user', 'is_read', 'is_replied', 'created_at']
    list_filter = ['is_read']
    search_fields = ['name', 'email', 'message']
    readonly_fields = ['name', 'email', 'message', 'user', 'created_at', 'replied_at']
    list_editable = ['is_read']
    ordering = ['-created_at']
    fields = ['name', 'email', 'user', 'message', 'is_read', 'reply', 'replied_at', 'created_at']

    def is_replied(self, obj):
        return obj.is_replied
    is_replied.boolean = True

    def save_model(self, request, obj, form, change):
        if 'reply' in form.changed_data and obj.reply:
            from django.utils import timezone
            obj.replied_at = timezone.now()
            obj.is_read = True
        super().save_model(request, obj, form, change)
