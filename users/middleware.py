# users/middleware.py
import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

# Add this import
from users.models import AdminMessage

logger = logging.getLogger(__name__)


class MessageAdminAccessMiddleware(MiddlewareMixin):
    """
    Middleware to restrict message admin users to only messaging functionality
    AND show admin notifications
    """

    def process_request(self, request):
        """Process incoming request and restrict access for message admins"""

        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return None

        # ADD THIS: Show admin notifications for all staff users on admin pages
        if (
            request.user.is_staff
            and request.path.startswith("/admin/")
            and not request.path.startswith("/admin/logout")
        ):
            self.add_admin_notifications(request)

        # Skip for superusers (they have full access)
        if request.user.is_superuser:
            return None

        # Check if user is a message admin
        if not self.is_message_admin(request.user):
            return None

        # ... rest of your existing code stays the same ...

        # Get the current path
        path = request.path

        # Define allowed paths for message admins
        allowed_paths = [
            "/users/message_admin/",
            "/users/message_admin/send/",
            "/users/message_admin/my-messages/",
            "/users/message_admin/message/",
            "/users/api/",
            "/logout/",
            "/admin/logout/",
            "/static/",  # Allow static files
            "/media/",  # Allow media files
        ]

        # Check if current path starts with any allowed path
        path_allowed = any(
            path.startswith(allowed_path) for allowed_path in allowed_paths
        )

        # Special handling for admin URLs
        if path.startswith("/admin/"):
            # Only allow logout for message admins in admin area
            if path in ["/admin/logout/", "/admin/logout"]:
                return None
            else:
                # Redirect message admins away from main admin
                logger.warning(
                    f"Message admin {request.user.get_display_name()} "
                    f"attempted to access restricted admin path: {path}"
                )
                messages.warning(request, "شما تنها به بخش پیام‌رسانی دسترسی دارید.")
                return redirect("users:message_admin_dashboard")

        # If path is not allowed, redirect to message admin dashboard
        if not path_allowed:
            logger.info(
                f"Message admin {request.user.get_display_name()} "
                f"redirected from {path} to message admin dashboard"
            )
            return redirect("users:message_admin_dashboard")

        return None

    # ADD THIS NEW METHOD:
    def add_admin_notifications(self, request):
        """Add admin message notifications to the request"""
        try:
            unread_messages = AdminMessage.objects.filter(status="unread").order_by(
                "-created_at"
            )
            unread_count = unread_messages.count()

            if unread_count > 0:
                # Get the latest message for preview
                latest_message = unread_messages.first()

                # Create notification message
                notification_text = (
                    f"📨 شما {unread_count} پیام خوانده نشده دارید. "
                    f'آخرین پیام: "{latest_message.subject}" از {latest_message.sender.get_display_name()}. '
                    f'<a href="/admin/users/adminmessage/" style="color: white; text-decoration: underline;">مشاهده پیام‌ها</a>'
                )

                # Add as info message (will appear at top of admin pages)
                messages.info(
                    request, notification_text, extra_tags="safe admin-notification"
                )

        except Exception as e:
            # Silently fail to avoid breaking admin
            logger.error(f"Error adding admin notifications: {str(e)}")

    def is_message_admin(self, user):
        """Check if user is a message admin"""
        return (
            user.is_staff
            and not user.is_superuser
            and user.user_type
            and user.user_type.slug == "message_admin"
        )
