# users/middleware.py - Simplified security logging middleware
# This middleware is OPTIONAL - only use if you need detailed security logging

import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('users.security')


class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Simplified middleware to log security-related events
    Only use this if you need detailed security logging
    """

    def process_request(self, request):
        # Store request start time for performance logging
        request._logging_start_time = time.time()

        # Get client IP
        client_ip = self.get_client_ip(request)

        # Log admin access attempts
        if request.path.startswith('/admin/'):
            security_logger.info(
                f"Admin access - IP: {client_ip}, "
                f"User: {getattr(request.user, 'username', 'Anonymous')}, "
                f"Path: {request.path}"
            )

    def process_response(self, request, response):
        # Log failed requests (4xx, 5xx)
        if response.status_code >= 400:
            client_ip = self.get_client_ip(request)
            security_logger.warning(
                f"Failed request - Status: {response.status_code}, "
                f"Method: {request.method}, Path: {request.path}, "
                f"IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}"
            )

        return response

    def process_exception(self, request, exception):
        # Log exceptions
        client_ip = self.get_client_ip(request)
        security_logger.error(
            f"Exception - Path: {request.path}, IP: {client_ip}, "
            f"User: {getattr(request.user, 'username', 'Anonymous')}, "
            f"Error: {str(exception)}"
        )
        return None

    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip


# Signal handlers for authentication events
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login"""
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

    security_logger.info(
        f"Login successful - User: {user.username}, IP: {client_ip}, "
        f"User-Agent: {user_agent[:100]}..."  # Limit user agent length
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    if user:
        security_logger.info(f"Logout - User: {user.username}, IP: {client_ip}")
    else:
        security_logger.info(f"Anonymous logout - IP: {client_ip}")


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    username = credentials.get('username', 'Unknown')

    security_logger.warning(
        f"Login failed - Username: {username}, IP: {client_ip}, "
        f"User-Agent: {user_agent[:100]}..."
    )


# Utility functions for specific logging needs
def log_sensitive_operation(user, operation, details, request):
    """Log sensitive operations like password changes, data exports, etc."""
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    security_logger.info(
        f"Sensitive operation - User: {user.username if user else 'Anonymous'}, "
        f"Operation: {operation}, Details: {details}, IP: {client_ip}"
    )


def log_permission_denied(user, resource, request):
    """Log permission denied events"""
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    security_logger.warning(
        f"Permission denied - User: {user.username if user else 'Anonymous'}, "
        f"Resource: {resource}, IP: {client_ip}"
    )


def log_suspicious_activity(user, activity_type, details, request):
    """Log suspicious activities"""
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'Unknown'))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    security_logger.warning(
        f"Suspicious activity - User: {user.username if user else 'Anonymous'}, "
        f"Type: {activity_type}, Details: {details}, IP: {client_ip}"
    )