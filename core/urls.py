from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

    # ── CATALOGUE ──────────────────────────────────────────
    path('', views.home_view, name='home'),
    path('categories/', views.categories_view, name='categories'),
    path('categories/<slug:slug>/', views.category_detail_view, name='category_detail'),
    path('products/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('search/', views.search_view, name='search'),
    path('new-arrivals/', views.new_arrivals_view, name='new_arrivals'),

    # ── ACCOUNTS ───────────────────────────────────────────
    path('accounts/register/', views.register_view, name='register'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/profile/', views.profile_view, name='profile'),
    path('accounts/profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('accounts/addresses/', views.address_list_view, name='address_list'),
    path('accounts/addresses/add/', views.address_add_view, name='address_add'),
    path('accounts/addresses/<int:id>/edit/', views.address_edit_view, name='address_edit'),
    path('accounts/addresses/<int:id>/delete/', views.address_delete_view, name='address_delete'),
    path('accounts/addresses/<int:id>/default/', views.address_set_default_view, name='address_set_default'),
    path('accounts/messages/', views.my_messages_view, name='my_messages'),

    # Admin profile (separate from customer profile)
    path('admin-panel/profile/', views.admin_profile_view, name='admin_profile'),
    path('admin-panel/profile/password/', views.admin_change_password_view, name='admin_change_password'),

    # Password change (Django built-in)
    path(
        'accounts/password-change/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/change_password.html',
            success_url='/accounts/profile/',
        ),
        name='password_change',
    ),
    path(
        'accounts/password-change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='accounts/password_change_done.html',
        ),
        name='password_change_done',
    ),

    # Password reset (Django built-in)
    path(
        'accounts/password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'accounts/password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'accounts/password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
        ),
        name='password_reset_confirm',
    ),
    path(
        'accounts/password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),

    # ── CART ───────────────────────────────────────────────
    path('cart/', views.cart_detail_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_view, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart_view, name='clear_cart'),

    # ── WISHLIST ───────────────────────────────────────────
    path('wishlist/', views.wishlist_detail_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist_view, name='toggle_wishlist'),
    path('wishlist/move-to-cart/<int:item_id>/', views.move_to_cart_view, name='move_to_cart'),

    # ── ORDERS ─────────────────────────────────────────────
    path('orders/checkout/', views.checkout_view, name='checkout'),
    path('orders/confirm/<str:order_number>/', views.order_confirm_view, name='order_confirm'),
    path('orders/history/', views.order_history_view, name='order_history'),
    path('orders/<str:order_number>/', views.order_detail_view, name='order_detail'),

    # ── CONTACT ────────────────────────────────────────────
    path('contact/', views.contact_view, name='contact'),

    # ── STORE ADMIN ────────────────────────────────────────
    path('admin-panel/', views.dashboard_view, name='admin_dashboard'),
    path('admin-panel/login/', views.admin_login_view, name='admin_login'),
    path('admin-panel/register/', views.admin_register_view, name='admin_register'),
    path('admin-panel/logout/', views.admin_logout_view, name='admin_logout'),

    path('admin-panel/products/', views.product_list_view, name='admin_product_list'),
    path('admin-panel/products/add/', views.product_add_view, name='admin_product_add'),
    path('admin-panel/products/<int:id>/edit/', views.product_edit_view, name='admin_product_edit'),
    path('admin-panel/products/<int:id>/delete/', views.product_delete_view, name='admin_product_delete'),

    path('admin-panel/categories/', views.category_list_view, name='admin_category_list'),
    path('admin-panel/categories/add/', views.category_add_view, name='admin_category_add'),
    path('admin-panel/categories/<int:id>/edit/', views.category_edit_view, name='admin_category_edit'),
    path('admin-panel/categories/<int:id>/delete/', views.category_delete_view, name='admin_category_delete'),

    path('admin-panel/orders/', views.admin_order_list_view, name='admin_order_list'),
    path('admin-panel/orders/<int:id>/', views.admin_order_detail_view, name='admin_order_detail'),
    path('admin-panel/orders/<int:id>/update-status/', views.admin_order_update_status_view, name='admin_order_update_status'),
    path('admin-panel/orders/<int:id>/invoice/', views.admin_order_invoice_view, name='admin_order_invoice'),
    path('admin-panel/orders/<int:id>/shipping-label/', views.admin_order_shipping_label_view, name='admin_order_shipping_label'),

    path('admin-panel/messages/', views.admin_contact_list_view, name='admin_contact_list'),
    path('admin-panel/messages/<int:id>/', views.admin_contact_detail_view, name='admin_contact_detail'),
]
