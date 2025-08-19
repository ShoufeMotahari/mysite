import re
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def is_html_content(content):
    """Check if content contains HTML tags"""
    html_pattern = re.compile(r"<[^>]+>")
    return bool(html_pattern.search(content))


def get_site_url_from_request(request):
    """Get the site URL from request with proper protocol detection"""
    if request:
        protocol = "https" if request.is_secure() else "http"
        domain = request.get_host()
        return f"{protocol}://{domain}"
    else:
        return getattr(settings, 'SITE_URL', 'http://localhost:8000')


def strip_html_tags(html_content):
    """Simple HTML tag removal for fallback text content"""
    return re.sub(r'<[^>]+>', '', html_content)


def get_admin_emails():
    """Get admin email addresses from settings"""
    from .email_validators import EmailValidator

    try:
        # Try to get from ADMINS setting
        admins = getattr(settings, 'ADMINS', [])
        admin_emails = [admin[1] for admin in admins if len(admin) > 1]

        # Fallback to a specific setting
        if not admin_emails:
            notification_emails = getattr(settings, 'COMMENT_NOTIFICATION_EMAILS', [])
            if isinstance(notification_emails, (list, tuple)):
                admin_emails = list(notification_emails)
            elif isinstance(notification_emails, str):
                admin_emails = [notification_emails]

        # Final fallback to DEFAULT_FROM_EMAIL if configured
        if not admin_emails:
            default_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            if default_email and EmailValidator.is_valid_email(default_email):
                admin_emails = [default_email]

        # Validate all emails
        valid_emails = []
        for email in admin_emails:
            if EmailValidator.is_valid_email(email):
                valid_emails.append(email)
            else:
                logger.warning(f"Invalid admin email found: {email}")

        return valid_emails

    except Exception as e:
        logger.error(f"Error getting admin emails: {str(e)}")
        return []
