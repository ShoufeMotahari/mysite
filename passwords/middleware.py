# Create this as passwords/middleware.py

import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.urls import resolve

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('passwords.security')


class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log security-related events and request information
    """

    def process_request(self, request):
        # Log request start
        request._logging_start_time = time.time()

        # Get client information
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

        # Log request details
        logger.debug(
            f"Request started - Method: {request.method}, Path: {request.path}, IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}")

        # Log sensitive operations
        if request.path.startswith('/admin/'):
            security_logger.info(
                f"Admin access attempt - IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}, Path: {request.path}")

        # Log password-related operations
        sensitive_paths = ['/add-password/', '/view-password/', '/edit-password/', '/delete-password/']
        if any(path in request.path for path in sensitive_paths):
            security_logger.info(
                f"Sensitive operation - IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}, Path: {request.path}")

        # Log authentication attempts
        if request.path in ['/login/', '/register/', '/logout/']:
            security_logger.info(f"Auth operation - IP: {client_ip}, Path: {request.path}")

    def process_response(self, request, response):
        # Calculate request duration
        if hasattr(request, '_logging_start_time'):
            duration = time.time() - request._logging_start_time
        else:
            duration = 0

        # Get client information
        client_ip = self.get_client_ip(request)

        # Log response details
        logger.debug(
            f"Request completed - Status: {response.status_code}, Duration: {duration:.3f}s, IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}")

        # Log failed requests
        if response.status_code >= 400:
            security_logger.warning(
                f"Failed request - Status: {response.status_code}, Method: {request.method}, Path: {request.path}, IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}")

        # Log successful sensitive operations
        if response.status_code == 200:
            sensitive_paths = ['/view-password/', '/add-password/', '/edit-password/', '/delete-password/']
            if any(path in request.path for path in sensitive_paths):
                security_logger.info(
                    f"Sensitive operation completed - Status: {response.status_code}, Path: {request.path}, IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}")

        return response

    def process_exception(self, request, exception):
        # Log exceptions
        client_ip = self.get_client_ip(request)
        logger.error(
            f"Exception occurred - Exception: {str(exception)}, Path: {request.path}, IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}")
        security_logger.error(
            f"Security exception - Exception: {str(exception)}, Path: {request.path}, IP: {client_ip}, User: {getattr(request.user, 'username', 'Anonymous')}")

        return None

    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Signal handlers for authentication events
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

    security_logger.info(f"User login successful - User: {user.username}, IP: {client_ip}, User-Agent: {user_agent}")
    logger.info(f"User logged in - User: {user.username}, IP: {client_ip}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))

    if user:
        security_logger.info(f"User logout - User: {user.username}, IP: {client_ip}")
        logger.info(f"User logged out - User: {user.username}, IP: {client_ip}")
    else:
        security_logger.info(f"Anonymous logout - IP: {client_ip}")
        logger.info(f"Anonymous logout - IP: {client_ip}")


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    username = credentials.get('username', 'Unknown')

    security_logger.warning(f"User login failed - Username: {username}, IP: {client_ip}, User-Agent: {user_agent}")
    logger.warning(f"Login failed - Username: {username}, IP: {client_ip}")


# Additional utility functions for logging
def log_password_strength(password_length, has_special_chars, has_numbers, has_uppercase, service_name, username):
    """Log password strength analysis"""
    logger.info(
        f"Password strength analysis - Service: {service_name}, Username: {username}, Length: {password_length}, Special chars: {has_special_chars}, Numbers: {has_numbers}, Uppercase: {has_uppercase}")


def log_suspicious_activity(activity_type, details, user, client_ip):
    """Log suspicious activities"""
    security_logger.warning(
        f"Suspicious activity detected - Type: {activity_type}, Details: {details}, User: {user}, IP: {client_ip}")


def log_data_export(user, export_type, record_count, client_ip):
    """Log data export activities"""
    security_logger.info(f"Data export - User: {user}, Type: {export_type}, Records: {record_count}, IP: {client_ip}")


def log_bulk_operations(user, operation_type, affected_records, client_ip):
    """Log bulk operations"""
    security_logger.info(
        f"Bulk operation - User: {user}, Operation: {operation_type}, Affected records: {affected_records}, IP: {client_ip}")


def log_permission_denied(user, requested_resource, client_ip):
    """Log permission denied events"""
    security_logger.warning(f"Permission denied - User: {user}, Resource: {requested_resource}, IP: {client_ip}")


def log_rate_limiting(user, action, client_ip):
    """Log rate limiting events"""
    security_logger.warning(f"Rate limit exceeded - User: {user}, Action: {action}, IP: {client_ip}")


def log_password_policy_violation(user, policy_violated, client_ip):
    """Log password policy violations"""
    security_logger.warning(f"Password policy violation - User: {user}, Policy: {policy_violated}, IP: {client_ip}")


def log_session_activity(user, activity_type, session_key, client_ip):
    """Log session-related activities"""
    security_logger.info(
        f"Session activity - User: {user}, Activity: {activity_type}, Session: {session_key[:10]}..., IP: {client_ip}")


def log_backup_restore_activity(user, activity_type, details, client_ip):
    """Log backup and restore activities"""
    security_logger.info(
        f"Backup/Restore activity - User: {user}, Activity: {activity_type}, Details: {details}, IP: {client_ip}")


def log_configuration_change(user, setting_changed, old_value, new_value, client_ip):
    """Log configuration changes"""
    security_logger.info(
        f"Configuration change - User: {user}, Setting: {setting_changed}, Old: {old_value}, New: {new_value}, IP: {client_ip}")


def log_api_access(user, endpoint, method, response_code, client_ip):
    """Log API access"""
    security_logger.info(
        f"API access - User: {user}, Endpoint: {endpoint}, Method: {method}, Response: {response_code}, IP: {client_ip}")


def log_file_access(user, file_path, action, client_ip):
    """Log file access activities"""
    security_logger.info(f"File access - User: {user}, File: {file_path}, Action: {action}, IP: {client_ip}")


def log_database_query(user, query_type, table_name, client_ip):
    """Log database query activities"""
    security_logger.debug(f"Database query - User: {user}, Type: {query_type}, Table: {table_name}, IP: {client_ip}")


def log_encryption_activity(user, activity_type, service_name, client_ip):
    """Log encryption/decryption activities"""
    security_logger.info(
        f"Encryption activity - User: {user}, Activity: {activity_type}, Service: {service_name}, IP: {client_ip}")


def log_audit_trail(user, action, resource, old_values, new_values, client_ip):
    """Log audit trail for critical changes"""
    security_logger.info(
        f"Audit trail - User: {user}, Action: {action}, Resource: {resource}, Old: {old_values}, New: {new_values}, IP: {client_ip}")


def log_system_event(event_type, details, severity='INFO'):
    """Log system-level events"""
    if severity == 'ERROR':
        security_logger.error(f"System event - Type: {event_type}, Details: {details}")
    elif severity == 'WARNING':
        security_logger.warning(f"System event - Type: {event_type}, Details: {details}")
    else:
        security_logger.info(f"System event - Type: {event_type}, Details: {details}")


def log_performance_metrics(user, action, duration, client_ip):
    """Log performance metrics"""
    logger.info(f"Performance metrics - User: {user}, Action: {action}, Duration: {duration}ms, IP: {client_ip}")


def log_security_scan(scan_type, results, client_ip):
    """Log security scan results"""
    security_logger.info(f"Security scan - Type: {scan_type}, Results: {results}, IP: {client_ip}")


def log_compliance_event(user, event_type, regulation, details, client_ip):
    """Log compliance-related events"""
    security_logger.info(
        f"Compliance event - User: {user}, Type: {event_type}, Regulation: {regulation}, Details: {details}, IP: {client_ip}")