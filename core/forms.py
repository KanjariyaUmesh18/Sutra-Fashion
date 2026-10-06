"""
SUTRA — Core Forms
All forms consolidated into a single file.
"""

from django import forms
from django.contrib.auth.models import User
from .models import (
    UserProfile, Address,
    Order, ContactInquiry,
    Product, Category,
)


# ─────────────────────────────────────────────────────────
# ACCOUNTS
# ─────────────────────────────────────────────────────────

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Min. 6 characters'}),
        min_length=6,
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '').strip()
        if not value:
            raise forms.ValidationError("First name is required.")
        return value

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if password and confirm and password != confirm:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = UserProfile
        fields = ['phone', 'avatar']
        widgets = {
            'phone':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 99999 99999'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
        # Re-order fields for logical display
        field_order = ['first_name', 'last_name', 'email', 'phone', 'avatar']
        self.fields = {k: self.fields[k] for k in field_order if k in self.fields}

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        return email


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['name', 'phone', 'line1', 'line2', 'city', 'state', 'pincode', 'is_default']
        widgets = {
            'name':       forms.TextInput(attrs={'class': 'form-control'}),
            'phone':      forms.TextInput(attrs={'class': 'form-control'}),
            'line1':      forms.TextInput(attrs={'class': 'form-control'}),
            'line2':      forms.TextInput(attrs={'class': 'form-control'}),
            'city':       forms.TextInput(attrs={'class': 'form-control'}),
            'state':      forms.TextInput(attrs={'class': 'form-control'}),
            'pincode':    forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(),
        }


# ─────────────────────────────────────────────────────────
# ORDERS / CHECKOUT
# ─────────────────────────────────────────────────────────

class CheckoutForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect,
        initial='cod',
    )

    class Meta:
        model = Order
        fields = [
            'shipping_name', 'shipping_phone',
            'shipping_address_line1', 'shipping_address_line2',
            'shipping_city', 'shipping_state', 'shipping_pincode',
            'payment_method', 'notes',
        ]
        widgets = {
            'shipping_name':          forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_phone':         forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_city':          forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_state':         forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_pincode':       forms.TextInput(attrs={'class': 'form-control'}),
            'notes':                  forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ─────────────────────────────────────────────────────────
# CONTACT
# ─────────────────────────────────────────────────────────

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ['name', 'email', 'message']
        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control'}),
            'email':   forms.EmailInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


class ContactReplyForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ['reply']
        widgets = {
            'reply': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Type your reply to the customer...'}),
        }


# ─────────────────────────────────────────────────────────
# STORE ADMIN
# ─────────────────────────────────────────────────────────

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category', 'name', 'slug', 'description',
            'price', 'original_price', 'stock', 'sku',
            'sizes', 'colors', 'is_active', 'is_featured', 'badge',
            'free_shipping', 'shipping_charge', 'cash_on_delivery',
        ]
        widgets = {
            'category':     forms.Select(attrs={'class': 'form-control'}),
            'name':         forms.TextInput(attrs={'class': 'form-control'}),
            'slug':         forms.TextInput(attrs={'class': 'form-control'}),
            'description':  forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'price':        forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock':        forms.NumberInput(attrs={'class': 'form-control'}),
            'sku':          forms.TextInput(attrs={'class': 'form-control'}),
            'sizes':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XS,S,M,L,XL'}),
            'colors':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Gold,Maroon'}),
            'badge':        forms.Select(attrs={'class': 'form-control'}),
            'shipping_charge': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def clean_slug(self):
        # Allow empty slug — model.save() will auto-generate
        return self.cleaned_data.get('slug', '').strip() or ''

    def clean(self):
        cleaned = super().clean()
        # If the admin marked the product as free shipping, the paid amount
        # is irrelevant — force it back to zero so stale values can't leak
        # onto the storefront if free shipping is re-enabled later.
        if cleaned.get('free_shipping'):
            cleaned['shipping_charge'] = 0
        elif not cleaned.get('shipping_charge'):
            self.add_error('shipping_charge', 'Enter a shipping amount, or enable Free Shipping instead.')
        return cleaned


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'image', 'is_active', 'sort_order']
        widgets = {
            'name':       forms.TextInput(attrs={'class': 'form-control'}),
            'slug':       forms.TextInput(attrs={'class': 'form-control'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_slug(self):
        return self.cleaned_data.get('slug', '').strip() or ''
