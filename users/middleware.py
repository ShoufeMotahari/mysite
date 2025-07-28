# users/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class MessageAdminAccessMiddleware(MiddlewareMixin):
    """
    Middleware to restrict message admin users to only messaging functionality
    """

    def process_request(self, request):
        """Process incoming request and restrict access for message admins"""

        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return None

        # Skip for superusers (they have full access)
        if request.user.is_superuser:
            return None

        # Check if user is a message admin
        if not self.is_message_admin(request.user):
            return None

        # Get the current path
        path = request.path

        # Define allowed paths for message admins
        allowed_paths = [
            '/users/message_admin/',
            '/users/message_admin/send/',
            '/users/message_admin/my-messages/',
            '/users/message_admin/message/',
            '/users/api/',
            '/logout/',
            '/admin/logout/',
            '/static/',  # Allow static files
            '/media/',  # Allow media files
        ]

        # Check if current path starts with any allowed path
        path_allowed = any(path.startswith(allowed_path) for allowed_path in allowed_paths)

        # Special handling for admin URLs
        if path.startswith('/admin/'):
            # Only allow logout for message admins in admin area
            if path in ['/admin/logout/', '/admin/logout']:
                return None
            else:
                # Redirect message admins away from main admin
                logger.warning(
                    f"Message admin {request.user.get_display_name()} "
                    f"attempted to access restricted admin path: {path}"
                )
                messages.warning(
                    request,
                    'شما تنها به بخش پیام‌رسانی دسترسی دارید.'
                )
                return redirect('users:message_admin_dashboard')

        # If path is not allowed, redirect to message admin dashboard
        if not path_allowed:
            logger.info(
                f"Message admin {request.user.get_display_name()} "
                f"redirected from {path} to message admin dashboard"
            )
            return redirect('users:message_admin_dashboard')

        return None

    def is_message_admin(self, user):
        """Check if user is a message admin"""
        return (
                user.is_staff and
                not user.is_superuser and
                user.user_type and
                user.user_type.slug == 'message_admin'
        )