"""
SUTRA — Context Processors
Inject common data into every template context.
"""

from .models import Category, Cart, Wishlist


def catalogue_context(request):
    """Inject footer categories into every template."""
    footer_categories = Category.objects.filter(is_active=True).order_by('sort_order')[:6]
    return {'footer_categories': footer_categories}


def cart_context(request):
    """Inject cart item count into every template."""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return {'cart_count': cart.item_count}
        except Cart.DoesNotExist:
            pass
    else:
        session_key = request.session.session_key
        if session_key:
            try:
                cart = Cart.objects.get(session_key=session_key, user__isnull=True)
                return {'cart_count': cart.item_count}
            except Cart.DoesNotExist:
                pass
    return {'cart_count': 0}


def wishlist_context(request):
    """Inject wishlist item count into every template."""
    if request.user.is_authenticated:
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            return {'wishlist_count': wishlist.items.count()}
        except Wishlist.DoesNotExist:
            pass
    return {'wishlist_count': 0}


def admin_context(request):
    """Inject unread contact-message count for the admin sidebar badge."""
    if getattr(request.user, 'is_staff', False):
        from .models import ContactInquiry
        return {'unread_messages_count': ContactInquiry.objects.filter(is_read=False).count()}
    return {'unread_messages_count': 0}
