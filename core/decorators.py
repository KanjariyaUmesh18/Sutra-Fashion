from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied


def staff_required(login_url='admin_login'):
    """
    Decorator that ensures the user is authenticated AND is a staff member.
    - Unauthenticated users → redirected to login_url
    - Authenticated non-staff → PermissionDenied (403)
    """
    def check_is_staff(user):
        if user.is_authenticated:
            if user.is_active and user.is_staff:
                return True
            raise PermissionDenied
        return False  # triggers redirect to login_url

    return user_passes_test(check_is_staff, login_url=login_url)
