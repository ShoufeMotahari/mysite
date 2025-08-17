# services/email_service.py
import logging
import re
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.validators import validate_email

logger = logging.getLogger("email_service")


class EmailValidator:
    @staticmethod
    def is_valid_email(email):
        """Validate email format"""
        if not email:
            return False
        try:
            validate_email(email)
            return True
        except ValidationError:
            return False

    @staticmethod
    def is_active_user(user):
        """Check if user is active"""
        return user.is_active

    @staticmethod
    def validate_users(users):
        """Validate users and return valid/invalid lists"""
        valid_users = []
        invalid_users = []

        for user in users:
            user_issues = []

            # Check if user is active
            if not EmailValidator.is_active_user(user):
                user_issues.append("inactive_user")

            # Check if user has valid email
            if not EmailValidator.is_valid_email(user.email):
                user_issues.append("invalid_email")

            if user_issues:
                invalid_users.append({"user": user, "issues": user_issues})
            else:
                valid_users.append(user)

        return valid_users, invalid_users

    @classmethod
    def validate_email(cls, email):
        """Validate single email address"""
        if not email:
            raise ValidationError("Email is required")

        try:
            validate_email(email)
            return True
        except ValidationError as e:
            raise ValidationError(f"Invalid email format: {email}")


class EmailStrategy(ABC):
    @abstractmethod
    def send_email(self, recipients, subject, content, sender_info):
        pass


def _is_html_content(content):
    """Check if content contains HTML tags"""
    html_pattern = re.compile(r"<[^>]+>")
    return bool(html_pattern.search(content))


class DjangoEmailStrategy(EmailStrategy):
    def send_email(self, recipients, subject, content, sender_info):
        try:
            # Validate recipients first
            valid_users, invalid_users = EmailValidator.validate_users(recipients)

            # Log validation results
            logger.info(f"📊 User validation results:")
            logger.info(f"  ✅ Valid users: {len(valid_users)}")
            logger.info(f"  ❌ Invalid users: {len(invalid_users)}")

            # Log invalid users details
            if invalid_users:
                logger.warning(f"⚠️ Invalid users found ({len(invalid_users)}):")
                for invalid_user in invalid_users:
                    user = invalid_user["user"]
                    issues = invalid_user["issues"]
                    logger.warning(
                        f"  - {user.username} (ID: {user.id}): {', '.join(issues)}"
                    )
                    logger.warning(
                        f"    Email: '{user.email}', Active: {user.is_active}"
                    )

            # If no valid users, return early
            if not valid_users:
                error_msg = "No valid users found to send email to"
                logger.error(f"❌ {error_msg}")
                return (
                    False,
                    error_msg,
                    {
                        "total_users": len(recipients),
                        "valid_users": 0,
                        "invalid_users": len(invalid_users),
                        "invalid_details": invalid_users,
                    },
                )

            # Prepare email for valid users
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_emails = [user.email for user in valid_users]

            logger.info(f"📧 Preparing email for {len(valid_users)} valid users:")
            for user in valid_users:
                logger.info(f"  ✅ {user.username} ({user.email})")

            logger.info(
                f"📨 Sending email: '{subject}' to {len(recipient_emails)} recipients"
            )

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=content,
                from_email=from_email,
                to=recipient_emails,
            )

            # Add HTML alternative if content contains HTML
            if _is_html_content(content):
                msg.attach_alternative(content, "text/html")

            # Send email
            result = msg.send()

            if result:
                success_msg = (
                    f"Email sent successfully to {len(recipient_emails)} valid users"
                )
                logger.info(f"✅ {success_msg}")

                # Log summary
                logger.info(f"📈 Email sending summary:")
                logger.info(f"  📧 Subject: '{subject}'")
                logger.info(f"  👤 Sender: {sender_info}")
                logger.info(f"  📊 Total requested: {len(recipients)}")
                logger.info(f"  ✅ Successfully sent: {len(recipient_emails)}")
                logger.info(f"  ❌ Invalid/skipped: {len(invalid_users)}")

                return (
                    True,
                    success_msg,
                    {
                        "total_users": len(recipients),
                        "valid_users": len(valid_users),
                        "invalid_users": len(invalid_users),
                        "invalid_details": invalid_users,
                    },
                )
            else:
                error_msg = "Email sending failed - Django mail returned 0"
                logger.error(f"❌ {error_msg}")
                return (
                    False,
                    error_msg,
                    {
                        "total_users": len(recipients),
                        "valid_users": len(valid_users),
                        "invalid_users": len(invalid_users),
                        "invalid_details": invalid_users,
                    },
                )

        except Exception as e:
            error_msg = f"Exception occurred while sending email '{subject}': {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Full exception details:")
            return (
                False,
                error_msg,
                {
                    "total_users": len(recipients) if recipients else 0,
                    "valid_users": 0,
                    "invalid_users": 0,
                    "invalid_details": [],
                },
            )


class SMTPEmailStrategy(EmailStrategy):
    """Alternative SMTP email strategy for future use"""

    def __init__(self, smtp_config=None):
        self.smtp_config = smtp_config or {}

    def send_email(self, recipients, subject, content, sender_info):
        # Implementation for SMTP strategy
        # This can be implemented later if needed
        logger.info("SMTP email strategy not implemented yet")
        return False, "SMTP strategy not implemented", {}


class EmailService:
    def __init__(self, strategy: EmailStrategy):
        self._strategy = strategy
        self.logger = logging.getLogger("email_service")

    def set_strategy(self, strategy: EmailStrategy):
        """Change email sending strategy"""
        self._strategy = strategy
        self.logger.info(f"🔄 Email strategy changed to: {strategy.__class__.__name__}")

    def send_email(self, recipients, subject, content, sender_info):
        """Send email using the current strategy"""
        self.logger.info(f"🚀 Email service initiated for: '{subject}'")
        self.logger.info(f"📋 Processing {len(recipients)} recipients")

        # Validate inputs
        if not recipients:
            error_msg = "No recipients provided"
            self.logger.error(f"❌ {error_msg}")
            return False, error_msg, {}

        if not subject:
            error_msg = "No subject provided"
            self.logger.error(f"❌ {error_msg}")
            return False, error_msg, {}

        if not content:
            error_msg = "No content provided"
            self.logger.error(f"❌ {error_msg}")
            return False, error_msg, {}

        return self._strategy.send_email(recipients, subject, content, sender_info)

    def get_current_strategy(self):
        """Get the current email strategy"""
        return self._strategy.__class__.__name__


# Factory Pattern for Email Service
class EmailServiceFactory:
    _services = {
        "django": DjangoEmailStrategy,
        "smtp": SMTPEmailStrategy,
    }

    @staticmethod
    def create_email_service(service_type="django", **kwargs):
        """Create email service with specified strategy"""
        logger.info(f"🏭 Creating email service of type: {service_type}")

        if service_type not in EmailServiceFactory._services:
            available_types = ", ".join(EmailServiceFactory._services.keys())
            error_msg = f"Unknown email service type: {service_type}. Available types: {available_types}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        strategy_class = EmailServiceFactory._services[service_type]
        strategy = strategy_class(**kwargs)

        return EmailService(strategy)

    @staticmethod
    def get_available_services():
        """Get list of available email service types"""
        return list(EmailServiceFactory._services.keys())


# Utility functions for email processing
class EmailUtils:
    @staticmethod
    def sanitize_subject(subject):
        """Sanitize email subject line"""
        if not subject:
            return "No Subject"

        # Remove potentially harmful characters
        sanitized = re.sub(r'[^\w\s\-_.,!?()[\]{}:;@#$%^&*+=|\\/<>"`~]', "", subject)

        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:197] + "..."

        return sanitized.strip()

    @staticmethod
    def sanitize_content(content):
        """Basic content sanitization"""
        if not content:
            return ""

        # Remove null bytes and other control characters
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", content)

        return sanitized.strip()

    @staticmethod
    def extract_plain_text(html_content):
        """Extract plain text from HTML content"""
        if not html_content:
            return ""

        # Simple HTML tag removal
        plain_text = re.sub(r"<[^>]+>", "", html_content)

        # Decode HTML entities
        plain_text = plain_text.replace("&nbsp;", " ")
        plain_text = plain_text.replace("&amp;", "&")
        plain_text = plain_text.replace("&lt;", "<")
        plain_text = plain_text.replace("&gt;", ">")
        plain_text = plain_text.replace("&quot;", '"')
        plain_text = plain_text.replace("&#39;", "'")

        return plain_text.strip()


# Email service instance factory
def get_email_service(service_type="django"):
    """Convenience function to get email service instance"""
    return EmailServiceFactory.create_email_service(service_type)


# users/services/email_service.py
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from users.models import Comment, PasswordEntry

logger = logging.getLogger('users')


class CommentEmailService:
    @staticmethod
    def send_comment_notification(comment, client_ip=None):
        """
        Send email notification to admins when a new comment is created
        Production-ready version with error handling
        """
        try:
            # Get admin email from settings
            admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
            subject_prefix = getattr(settings, 'EMAIL_SUBJECT_PREFIX', '[Site] ')

            # Create subject
            subject = f"{subject_prefix}New Comment from {comment.user.username}"

            # Create detailed message content
            message_lines = [
                "A new comment has been submitted on your website.",
                "",
                f"User: {comment.user.username}",
                f"Email: {comment.user.email}",
                f"Subject: {comment.subject}",
                f"IP Address: {client_ip or 'Unknown'}",
                f"Submitted: {comment.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "Content:",
                "-" * 40,
                comment.content,
                "-" * 40,
                "",
                f"Comment ID: {comment.id}",
                "You can manage comments in the admin panel.",
            ]

            message = "\n".join(message_lines)

            # Log attempt
            logger.info(f"Attempting to send comment notification email for comment {comment.id}")
            logger.debug(f"Email backend: {settings.EMAIL_BACKEND}")
            logger.debug(f"Sending to: {admin_email}")

            # Try using Django's mail_admins first (preferred for admin notifications)
            try:
                mail_admins(
                    subject=f"New Comment from {comment.user.username}",
                    message=message,
                    fail_silently=False
                )
                logger.info(f"Admin notification sent successfully using mail_admins for comment {comment.id}")
                return True

            except Exception as admin_mail_error:
                logger.warning(f"mail_admins failed, trying send_mail: {str(admin_mail_error)}")

                # Fallback to send_mail
                result = send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_email],
                    fail_silently=False,
                )

                if result:
                    logger.info(
                        f"Comment notification email sent successfully using send_mail for comment {comment.id}")
                    return True
                else:
                    logger.error(f"send_mail returned 0 for comment {comment.id}")
                    return False

        except Exception as e:
            # Log the full error for debugging
            logger.error(
                f"Failed to send comment notification email for comment {comment.id}: {type(e).__name__}: {str(e)}")

            # In production, you might want to try alternative notification methods
            try:
                # Alternative: Log to a special file for manual review
                error_logger = logging.getLogger('email_failures')
                error_logger.critical(
                    f"FAILED EMAIL NOTIFICATION - Comment ID: {comment.id}, User: {comment.user.username}, Subject: {comment.subject}")
            except:
                pass

            return False


class EmailTestService:
    """Service for testing email configuration"""

    @staticmethod
    def test_email_configuration() -> Dict[str, any]:
        """Test email configuration and send a test email"""
        try:
            from django.core.mail import send_mail

            # Test email settings
            test_result = {
                'success': False,
                'message': '',
                'details': {}
            }

            # Check email backend
            backend = getattr(settings, 'EMAIL_BACKEND', 'Not configured')
            test_result['details']['backend'] = backend

            # Check SMTP settings
            host = getattr(settings, 'EMAIL_HOST', 'Not configured')
            port = getattr(settings, 'EMAIL_PORT', 'Not configured')
            test_result['details']['host'] = f"{host}:{port}"

            # Check authentication
            user = getattr(settings, 'EMAIL_HOST_USER', 'Not configured')
            test_result['details']['user'] = user

            # Get admin emails
            admin_emails = CommentEmailService._get_admin_emails()
            test_result['details']['admin_emails'] = admin_emails

            if not admin_emails:
                test_result['message'] = 'No admin emails configured'
                return test_result

            # Send test email
            send_mail(
                subject='Test Email - Comment Notification System',
                message='This is a test email to verify the comment notification system is working correctly.',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'test@example.com'),
                recipient_list=admin_emails,
                fail_silently=False
            )

            test_result['success'] = True
            test_result['message'] = f'Test email sent successfully to {len(admin_emails)} recipients'

            return test_result

        except Exception as e:
            return {
                'success': False,
                'message': f'Email test failed: {str(e)}',
                'details': {'error': str(e)}
            }