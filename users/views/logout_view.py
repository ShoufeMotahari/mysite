# users/views/logout_views.py - CREATE THIS NEW FILE

import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def smart_logout_view(request):
    """Smart logout that redirects based on user type"""

    if not request.user.is_authenticated:
        return redirect("/admin/login/")

    # Determine user type before logout
    user_type = None
    redirect_url = "/"  # Default redirect

    if request.user.is_superuser:
        # Superuser admin - redirect to admin login
        user_type = "superuser"
        redirect_url = "/admin/login/"
        logout_message = "مدیر ارشد با موفقیت خارج شد."

    elif (
        request.user.is_staff
        and hasattr(request.user, "user_type")
        and request.user.user_type
        and request.user.user_type.slug == "message_admin"
    ):
        # Message admin - redirect to admin login
        user_type = "message_admin"
        redirect_url = "/admin/login/"
        logout_message = "ادمین پیام‌رسان با موفقیت خارج شد."

    elif request.user.is_staff:
        # Other staff users - redirect to admin login
        user_type = "staff"
        redirect_url = "/admin/login/"
        logout_message = "کاربر ادمین با موفقیت خارج شد."

    else:
        # Regular users - redirect to main site
        user_type = "regular"
        redirect_url = "/"  # or '/users/login/' if you have a custom login page
        logout_message = "با موفقیت خارج شدید."

    # Log the logout for security
    logger.info(f"User logout: {request.user.username} (type: {user_type})")

    # Logout the user
    request.user.username
    logout(request)

    # Add success message
    messages.success(request, logout_message)

    # Redirect based on user type
    return redirect(redirect_url)


def message_admin_logout_view(request):
    """Specific logout for message admins"""

    if not request.user.is_authenticated:
        return redirect("/admin/login/")

    # Verify this is actually a message admin
    if not (
        request.user.is_staff
        and not request.user.is_superuser
        and hasattr(request.user, "user_type")
        and request.user.user_type
        and request.user.user_type.slug == "message_admin"
    ):
        # If not a message admin, use regular logout
        return smart_logout_view(request)

    username = request.user.username
    logout(request)

    logger.info(f"Message admin logout: {username}")
    messages.success(request, "از پنل پیام‌رسانی خارج شدید.")

    return redirect("/admin/login/")


def regular_user_logout_view(request):
    """Logout for regular site users"""

    if not request.user.is_authenticated:
        return redirect("/")

    username = request.user.username
    logout(request)

    logger.info(f"Regular user logout: {username}")
    messages.success(request, "با موفقیت از سایت خارج شدید.")

    # Redirect to main site or custom login page
    return redirect("/")  # Change this to your main site URL


# Alternative: Class-based view approach
from django.contrib.auth.views import LogoutView


class SmartLogoutView(LogoutView):
    """Smart logout view that redirects based on user type"""

    def get_next_page(self):
        """Determine redirect URL based on user type"""

        if not self.request.user.is_authenticated:
            return "/admin/login/"

        if self.request.user.is_superuser:
            return "/admin/login/"
        elif (
            self.request.user.is_staff
            and hasattr(self.request.user, "user_type")
            and self.request.user.user_type
            and self.request.user.user_type.slug == "message_admin"
        ):
            return "/admin/login/"
        elif self.request.user.is_staff:
            return "/admin/login/"
        else:  # Regular users
            return "/"  # Main site

    def dispatch(self, request, *args, **kwargs):
        """Add logging and custom messages"""
        if request.user.is_authenticated:
            user_type = "regular"
            if request.user.is_superuser:
                user_type = "superuser"
            elif (
                request.user.is_staff
                and hasattr(request.user, "user_type")
                and request.user.user_type
                and request.user.user_type.slug == "message_admin"
            ):
                user_type = "message_admin"
            elif request.user.is_staff:
                user_type = "staff"

            logger.info(f"Smart logout: {request.user.username} (type: {user_type})")

        return super().dispatch(request, *args, **kwargs)
