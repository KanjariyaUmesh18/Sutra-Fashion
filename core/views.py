"""
SUTRA — Core Views
All views consolidated into a single file.
"""

from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .decorators import staff_required
from .forms import (
    UserRegistrationForm, UserProfileForm, AddressForm,
    CheckoutForm, ContactForm, ContactReplyForm,
    ProductForm, CategoryForm,
)
from .models import (
    UserProfile, Address,
    Category, Product, ProductImage,
    Cart, CartItem,
    Wishlist, WishlistItem,
    Order, OrderItem,
    ContactInquiry,
)


# ─────────────────────────────────────────────────────────
# ACCOUNTS
# ─────────────────────────────────────────────────────────

def _merge_guest_cart(request, user):
    session_key = request.session.session_key
    if not session_key:
        return
    guest_cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
    if guest_cart:
        user_cart, _ = Cart.objects.get_or_create(user=user)
        for item in guest_cart.items.all():
            existing = user_cart.items.filter(product=item.product, size=item.size, color=item.color).first()
            if existing:
                existing.quantity += item.quantity
                existing.save()
            else:
                item.cart = user_cart
                item.save()
        guest_cart.delete()

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            email = form.cleaned_data['email'].strip().lower()
            user.username = email
            user.email = email
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserProfile.objects.get_or_create(user=user)
            messages.success(request, 'Registration successful. Please log in.')
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and next_url.startswith('/'):
                from django.utils.http import urlencode
                return redirect(f"/accounts/login/?{urlencode({'next': next_url})}")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            _merge_guest_cart(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or 'home'
            # Guard against open redirects
            if not next_url.startswith('/'):
                next_url = 'home'
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password. Please try again.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been signed out.')
    return redirect('home')


@login_required
def profile_view(request):
    # BUG FIX: was using order_set (wrong related_name); correct is orders
    orders = request.user.orders.order_by('-created_at')[:5]
    addresses = request.user.addresses.all()
    return render(request, 'accounts/profile.html', {
        'orders': orders,
        'addresses': addresses,
        'active': 'profile',
    })


@login_required
def edit_profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            new_email = form.cleaned_data['email'].strip().lower()
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = new_email
            request.user.username = new_email
            request.user.save()
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form, 'active': 'profile'})


@login_required
def address_list_view(request):
    addresses = request.user.addresses.all()
    return render(request, 'accounts/address_list.html', {'addresses': addresses, 'active': 'profile'})


@login_required
def address_add_view(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Address added successfully.')
            return redirect('address_list')
    else:
        form = AddressForm()
    return render(request, 'accounts/address_form.html', {'form': form, 'active': 'profile'})


@login_required
def address_edit_view(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully.')
            return redirect('address_list')
    else:
        form = AddressForm(instance=address)
    return render(request, 'accounts/address_form.html', {'form': form, 'active': 'profile'})


@login_required
def address_delete_view(request, id):
    address = get_object_or_404(Address, id=id, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted.')
        return redirect('address_list')
    return render(request, 'accounts/address_confirm_delete.html', {'address': address, 'active': 'profile'})


@login_required
def address_set_default_view(request, id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=id, user=request.user)
        address.is_default = True
        address.save()
        messages.success(request, 'Default address updated.')
    return redirect('address_list')


# ─────────────────────────────────────────────────────────
# CATALOGUE
# ─────────────────────────────────────────────────────────

def home_view(request):
    featured_products = Product.objects.filter(
        is_active=True, is_featured=True
    ).prefetch_related('images')[:8]
    new_arrivals = Product.objects.filter(
        is_active=True
    ).prefetch_related('images').order_by('-created_at')[:8]
    categories = Category.objects.filter(is_active=True).order_by('sort_order')[:6]
    return render(request, 'catalogue/index.html', {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'categories': categories,
        'active': 'home',
    })


def categories_view(request):
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('sort_order')
    return render(request, 'catalogue/categories.html', {
        'categories': categories,
        'active': 'categories',
    })


def category_detail_view(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = Product.objects.filter(
        category=category, is_active=True
    ).prefetch_related('images')
    sort = request.GET.get('sort', '')
    if sort == 'new':
        products = products.order_by('-created_at')
    elif sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    return render(request, 'catalogue/category_detail.html', {
        'category': category,
        'products': products,
        'active': 'categories',
    })


def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id).prefetch_related('images')[:4]
    return render(request, 'catalogue/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'active': 'categories',
    })


def search_view(request):
    query = request.GET.get('q', '').strip()
    products = []
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        ).prefetch_related('images')
    return render(request, 'catalogue/search_results.html', {
        'products': products,
        'query': query,
        'active': 'search',
    })


def new_arrivals_view(request):
    products = Product.objects.filter(
        is_active=True
    ).prefetch_related('images').order_by('-created_at')[:24]
    return render(request, 'catalogue/new_arrivals.html', {
        'products': products,
        'active': 'new',
    })


# ─────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────

def _get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key, user__isnull=True)
        return cart

def cart_detail_view(request):
    cart = _get_cart(request)
    return render(request, 'cart/cart.html', {'cart': cart, 'active': 'cart'})

def add_to_cart_view(request, product_id):
    if request.method != 'POST':
        return redirect('home')
    product = get_object_or_404(Product, id=product_id, is_active=True)
    size = request.POST.get('size', '').strip()
    color = request.POST.get('color', '').strip()
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (ValueError, TypeError):
        quantity = 1

    if not size:
        messages.error(request, 'Please select a size before adding to cart.')
        return redirect('product_detail', slug=product.slug)

    if product.stock < quantity:
        messages.error(request, f'Only {product.stock} units of {product.name} are available.')
        return redirect('product_detail', slug=product.slug)

    cart = _get_cart(request)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, size=size, color=color,
        defaults={'quantity': quantity}
    )
    if not created:
        item.quantity += quantity
        item.save()

    messages.success(request, f'"{product.name}" added to your bag.')
    return redirect('cart')

def update_cart_view(request, item_id):
    if request.method == 'POST':
        cart = _get_cart(request)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        action = request.POST.get('action')
        if action == 'increase':
            item.quantity += 1
            item.save()
        elif action == 'decrease':
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                item.delete()
    return redirect('cart')

def remove_from_cart_view(request, item_id):
    if request.method == 'POST':
        cart = _get_cart(request)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()
        messages.success(request, 'Item removed from your bag.')
    return redirect('cart')

def clear_cart_view(request):
    if request.method == 'POST':
        cart = _get_cart(request)
        cart.items.all().delete()
        messages.success(request, 'Your bag has been cleared.')
    return redirect('cart')


# ─────────────────────────────────────────────────────────
# WISHLIST
# ─────────────────────────────────────────────────────────

@login_required
def wishlist_detail_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'wishlist/wishlist.html', {'wishlist': wishlist, 'active': 'wishlist'})


@login_required
def toggle_wishlist_view(request, product_id):
    if request.method != 'POST':
        return redirect('home')
    product = get_object_or_404(Product, id=product_id, is_active=True)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    item, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
    if not created:
        item.delete()
        messages.info(request, f'"{product.name}" removed from wishlist.')
    else:
        messages.success(request, f'"{product.name}" added to wishlist.')

    # BUG FIX: next_url must be a URL path, not a view name
    next_url = request.POST.get('next', '')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('wishlist')


@login_required
def move_to_cart_view(request, item_id):
    if request.method != 'POST':
        return redirect('wishlist')
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    product = wishlist_item.product

    size = request.POST.get('size', '').strip()
    if not size and product.get_sizes_list:
        size = product.get_sizes_list[0]

    color = request.POST.get('color', '').strip()
    if not color and product.get_colors_list:
        color = product.get_colors_list[0]

    if not size:
        messages.error(request, f'Please select a size for "{product.name}".')
        return redirect('product_detail', slug=product.slug)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, size=size, color=color,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    wishlist_item.delete()
    messages.success(request, f'"{product.name}" moved to your bag.')
    return redirect('wishlist')


# ─────────────────────────────────────────────────────────
# ORDERS / CHECKOUT
# ─────────────────────────────────────────────────────────

@login_required
def checkout_view(request):
    cart = get_object_or_404(Cart, user=request.user)
    if not cart.items.exists():
        messages.warning(request, 'Your bag is empty. Add some items before checking out.')
        return redirect('cart')

    addresses = request.user.addresses.all()
    default_address = addresses.filter(is_default=True).first()

    cart_items = cart.items.select_related('product').all()
    # A product ships free unless the admin explicitly set a paid shipping charge for it.
    paid_shipping_items = [i for i in cart_items if not i.product.free_shipping and i.product.shipping_charge > 0]
    computed_shipping_charge = max((i.product.shipping_charge for i in paid_shipping_items), default=0)
    # Cash on Delivery is only offered when every item in the bag allows it.
    cod_available = all(i.product.cash_on_delivery for i in cart_items) if cart_items else True

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if not cod_available:
            form.fields['payment_method'].choices = [('online', 'Online Payment')]
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                subtotal = cart.total
                shipping_charge = computed_shipping_charge
                order.subtotal = subtotal
                order.shipping_charge = shipping_charge
                order.total = subtotal + shipping_charge
                order.payment_status = 'pending'
                order.status = 'pending'
                order.save()

                # Validate stock and create order items
                for cart_item in cart.items.select_related('product').all():
                    product = cart_item.product
                    if product.stock < cart_item.quantity:
                        messages.error(request, f'Not enough stock for "{product.name}" (only {product.stock} left).')
                        transaction.set_rollback(True)
                        return redirect('cart')
                    product.stock -= cart_item.quantity
                    product.save(update_fields=['stock'])
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_sku=product.sku,
                        size=cart_item.size,
                        color=cart_item.color,
                        quantity=cart_item.quantity,
                        unit_price=product.price,
                    )

                # Clear cart
                cart.items.all().delete()

                # Save/refresh the default address so future checkouts don't
                # need the address to be re-typed. The most recently used
                # shipping details always become (or update) the default.
                Address.objects.filter(user=request.user).update(is_default=False)
                Address.objects.update_or_create(
                    user=request.user,
                    name=order.shipping_name,
                    phone=order.shipping_phone,
                    line1=order.shipping_address_line1,
                    city=order.shipping_city,
                    pincode=order.shipping_pincode,
                    defaults={
                        'line2': order.shipping_address_line2,
                        'state': order.shipping_state,
                        'is_default': True,
                    },
                )

            messages.success(request, f'Order #{order.order_number} placed successfully!')
            return redirect('order_confirm', order_number=order.order_number)
    else:
        initial = {}
        if default_address:
            initial = {
                'shipping_name':          default_address.name,
                'shipping_phone':         default_address.phone,
                'shipping_address_line1': default_address.line1,
                'shipping_address_line2': default_address.line2,
                'shipping_city':          default_address.city,
                'shipping_state':         default_address.state,
                'shipping_pincode':       default_address.pincode,
            }
        form = CheckoutForm(initial=initial)
        if not cod_available:
            form.fields['payment_method'].choices = [('online', 'Online Payment')]

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'addresses': addresses,
        'default_address': default_address,
        'shipping_charge': computed_shipping_charge,
        'order_total': cart.total + computed_shipping_charge,
        'cod_available': cod_available,
        'active': 'checkout',
    })


@login_required
def order_confirm_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_confirm.html', {'order': order})


@login_required
def order_history_view(request):
    orders = request.user.orders.order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders, 'active': 'profile'})


@login_required
def order_detail_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order, 'active': 'profile'})


# ─────────────────────────────────────────────────────────
# CONTACT
# ─────────────────────────────────────────────────────────

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            if request.user.is_authenticated:
                inquiry.user = request.user
            inquiry.save()
            messages.success(request, 'Thank you for your message! We will get back to you within 24 hours.')
            return redirect('contact')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'name':  request.user.get_full_name() or request.user.first_name or request.user.username,
                'email': request.user.email,
            }
        form = ContactForm(initial=initial)
    return render(request, 'contact/contact.html', {'form': form, 'active': 'contact'})


@login_required
def my_messages_view(request):
    inquiries = ContactInquiry.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/my_messages.html', {
        'inquiries': inquiries,
        'active': 'messages',
    })


# ─────────────────────────────────────────────────────────
# STORE ADMIN
# ─────────────────────────────────────────────────────────

def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'You do not have permission to access the admin panel.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'store_admin/login.html', {'form': form})


def admin_register_view(request):
    """First-time admin setup — creates a superuser if none exist."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            email = form.cleaned_data['email'].strip().lower()
            user.username = email
            user.email = email
            user.set_password(form.cleaned_data['password'])
            user.is_staff = True
            user.is_superuser = True
            user.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Admin account created successfully. Welcome!')
            return redirect('admin_dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'store_admin/register.html', {'form': form})


@staff_required(login_url='admin_login')
def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')


@staff_required(login_url='admin_login')
def admin_profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            new_email = form.cleaned_data['email'].strip().lower()
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = new_email
            request.user.save()
            form.save()
            messages.success(request, 'Your admin profile has been updated.')
            return redirect('admin_profile')
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    return render(request, 'store_admin/profile.html', {
        'active': 'profile',
        'form': form,
        'profile': profile,
    })


@staff_required(login_url='admin_login')
def admin_change_password_view(request):
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('admin_profile')
    else:
        form = PasswordChangeForm(request.user)
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})
    return render(request, 'store_admin/change_password.html', {
        'active': 'profile',
        'form': form,
    })


@staff_required(login_url='admin_login')
def dashboard_view(request):
    orders = Order.objects.all()
    revenue = orders.filter(
        status__in=['confirmed', 'processing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total'))['total'] or 0
    pending_orders = orders.filter(status='pending').count()
    low_stock_products = Product.objects.filter(stock__lt=10, is_active=True).prefetch_related('images')
    total_products = Product.objects.filter(is_active=True).count()
    total_users = User.objects.filter(is_active=True, is_staff=False).count()
    return render(request, 'store_admin/dashboard.html', {
        'active': 'dashboard',
        'revenue': revenue,
        'pending_orders': pending_orders,
        'pending_orders_count': pending_orders,
        'low_stock_products': low_stock_products,
        'recent_orders': orders.order_by('-created_at')[:5],
        'total_products': total_products,
        'total_users': total_users,
    })


# ── PRODUCTS ──────────────────────────────────────────────

@staff_required(login_url='admin_login')
def product_list_view(request):
    products = Product.objects.select_related('category').prefetch_related('images').order_by('-created_at')
    return render(request, 'store_admin/products/product_list.html', {
        'active': 'products',
        'products': products,
    })


@staff_required(login_url='admin_login')
def product_add_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            images = request.FILES.getlist('images')
            image_errors = []
            for i, image in enumerate(images):
                try:
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        is_primary=(i == 0),
                        sort_order=i,
                    )
                except ValueError as exc:
                    # Normalisation validation error — surface it to the admin
                    image_errors.append(f"Image {i + 1} ({image.name}): {exc}")
            if image_errors:
                messages.warning(
                    request,
                    f'Product "{product.name}" saved, but some images were skipped: '
                    + ' | '.join(image_errors)
                )
            else:
                messages.success(request, f'Product "{product.name}" added successfully.')
            return redirect('admin_product_list')
    else:
        form = ProductForm()
    return render(request, 'store_admin/products/product_form.html', {
        'active': 'products',
        'form': form,
        'title': 'Add Product',
    })


@staff_required(login_url='admin_login')
def product_edit_view(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            images = request.FILES.getlist('images')
            image_errors = []
            for i, image in enumerate(images):
                try:
                    ProductImage.objects.create(product=product, image=image, sort_order=i)
                except ValueError as exc:
                    image_errors.append(f"Image {i + 1} ({image.name}): {exc}")
            if image_errors:
                messages.warning(
                    request,
                    f'Product "{product.name}" updated, but some images were skipped: '
                    + ' | '.join(image_errors)
                )
            else:
                messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('admin_product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store_admin/products/product_form.html', {
        'active': 'products',
        'form': form,
        'product': product,
        'title': 'Edit Product',
    })


@staff_required(login_url='admin_login')
def product_delete_view(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
        return redirect('admin_product_list')
    return render(request, 'store_admin/products/product_confirm_delete.html', {
        'active': 'products',
        'product': product,
    })


# ── CATEGORIES ────────────────────────────────────────────

@staff_required(login_url='admin_login')
def category_list_view(request):
    categories = Category.objects.annotate(product_count=Count('products'))
    return render(request, 'store_admin/categories/category_list.html', {
        'active': 'categories',
        'categories': categories,
    })


@staff_required(login_url='admin_login')
def category_add_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                cat = form.save()
                messages.success(request, f'Category "{cat.name}" added.')
                return redirect('admin_category_list')
            except ValueError as exc:
                messages.error(request, f'Image error: {exc}')
    else:
        form = CategoryForm()
    return render(request, 'store_admin/categories/category_form.html', {
        'active': 'categories',
        'form': form,
        'title': 'Add Category',
    })


@staff_required(login_url='admin_login')
def category_edit_view(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Category "{category.name}" updated.')
                return redirect('admin_category_list')
            except ValueError as exc:
                messages.error(request, f'Image error: {exc}')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'store_admin/categories/category_form.html', {
        'active': 'categories',
        'form': form,
        'category': category,
        'title': 'Edit Category',
    })


@staff_required(login_url='admin_login')
def category_delete_view(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" deleted.')
        return redirect('admin_category_list')
    return render(request, 'store_admin/categories/category_confirm_delete.html', {
        'active': 'categories',
        'category': category,
    })


# ── ORDERS (Admin) ────────────────────────────────────────

@staff_required(login_url='admin_login')
def admin_order_list_view(request):
    orders = Order.objects.select_related('user').order_by('-created_at')
    return render(request, 'store_admin/orders/order_list.html', {
        'active': 'orders',
        'orders': orders,
    })


@staff_required(login_url='admin_login')
def admin_order_detail_view(request, id):
    order = get_object_or_404(Order, id=id)
    return render(request, 'store_admin/orders/order_detail.html', {
        'active': 'orders',
        'order': order,
    })


@staff_required(login_url='admin_login')
def admin_order_invoice_view(request, id):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items'), id=id
    )
    return render(request, 'store_admin/orders/invoice.html', {'order': order})


@staff_required(login_url='admin_login')
def admin_order_shipping_label_view(request, id):
    order = get_object_or_404(Order, id=id)
    return render(request, 'store_admin/orders/shipping_label.html', {'order': order})


@staff_required(login_url='admin_login')
def admin_order_update_status_view(request, id):
    order = get_object_or_404(Order, id=id)
    if request.method == 'POST':
        status = request.POST.get('status')
        valid_statuses = dict(Order.STATUS_CHOICES).keys()
        if status in valid_statuses:
            order.status = status
            order.save(update_fields=['status'])
            messages.success(request, f'Order {order.order_number} updated to "{order.get_status_display()}".')
        else:
            messages.error(request, 'Invalid status value.')
    return redirect('admin_order_detail', id=id)


# ── MESSAGES (Contact Inquiries) ──────────────────────────

@staff_required(login_url='admin_login')
def admin_contact_list_view(request):
    inquiries = ContactInquiry.objects.select_related('user').order_by('is_read', '-created_at')
    return render(request, 'store_admin/messages/message_list.html', {
        'active': 'messages',
        'inquiries': inquiries,
    })


@staff_required(login_url='admin_login')
def admin_contact_detail_view(request, id):
    inquiry = get_object_or_404(ContactInquiry.objects.select_related('user'), id=id)

    if request.method == 'POST':
        form = ContactReplyForm(request.POST, instance=inquiry)
        if form.is_valid():
            reply_obj = form.save(commit=False)
            reply_obj.replied_at = timezone.now()
            reply_obj.is_read = True
            reply_obj.save()
            messages.success(request, f'Reply sent to {inquiry.name}.')
            return redirect('admin_contact_detail', id=id)
    else:
        # Viewing the inquiry marks it as read
        if not inquiry.is_read:
            inquiry.is_read = True
            inquiry.save(update_fields=['is_read'])
        form = ContactReplyForm(instance=inquiry)

    return render(request, 'store_admin/messages/message_detail.html', {
        'active': 'messages',
        'inquiry': inquiry,
        'form': form,
    })
