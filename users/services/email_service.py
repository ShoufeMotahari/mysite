# services/email_service.py
import logging
import re
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
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
