# services/email_service.py
from abc import ABC, abstractmethod
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging
import json
import re

logger = logging.getLogger('email_service')


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
                invalid_users.append({
                    'user': user,
                    'issues': user_issues
                })
            else:
                valid_users.append(user)

        return valid_users, invalid_users


class EmailStrategy(ABC):
    @abstractmethod
    def send_email(self, recipients, subject, content, sender_info):
        pass


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
                    user = invalid_user['user']
                    issues = invalid_user['issues']
                    logger.warning(f"  - {user.username} (ID: {user.id}): {', '.join(issues)}")
                    logger.warning(f"    Email: '{user.email}', Active: {user.is_active}")

            # If no valid users, return early
            if not valid_users:
                error_msg = "No valid users found to send email to"
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {
                    'total_users': len(recipients),
                    'valid_users': 0,
                    'invalid_users': len(invalid_users),
                    'invalid_details': invalid_users
                }

            # Prepare email for valid users
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_emails = [user.email for user in valid_users]

            logger.info(f"📧 Preparing email for {len(valid_users)} valid users:")
            for user in valid_users:
                logger.info(f"  ✅ {user.username} ({user.email})")

            logger.info(f"📨 Sending email: '{subject}' to {len(recipient_emails)} recipients")

            msg = EmailMultiAlternatives(
                subject=subject,
                body=content,
                from_email=from_email,
                to=recipient_emails
            )
            msg.attach_alternative(content, "text/html")

            # Send email
            result = msg.send()

            if result:
                success_msg = f"Email sent successfully to {len(recipient_emails)} valid users"
                logger.info(f"✅ {success_msg}")

                # Log summary
                logger.info(f"📈 Email sending summary:")
                logger.info(f"  📧 Subject: '{subject}'")
                logger.info(f"  👤 Sender: {sender_info}")
                logger.info(f"  📊 Total requested: {len(recipients)}")
                logger.info(f"  ✅ Successfully sent: {len(recipient_emails)}")
                logger.info(f"  ❌ Invalid/skipped: {len(invalid_users)}")

                return True, success_msg, {
                    'total_users': len(recipients),
                    'valid_users': len(valid_users),
                    'invalid_users': len(invalid_users),
                    'invalid_details': invalid_users
                }
            else:
                error_msg = "Email sending failed - Django mail returned 0"
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {
                    'total_users': len(recipients),
                    'valid_users': len(valid_users),
                    'invalid_users': len(invalid_users),
                    'invalid_details': invalid_users
                }

        except Exception as e:
            error_msg = f"Exception occurred while sending email '{subject}': {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Full exception details:")
            return False, error_msg, {
                'total_users': len(recipients) if recipients else 0,
                'valid_users': 0,
                'invalid_users': 0,
                'invalid_details': []
            }


class EmailService:
    def __init__(self, strategy: EmailStrategy):
        self._strategy = strategy
        self.logger = logging.getLogger('email_service')

    def set_strategy(self, strategy: EmailStrategy):
        self._strategy = strategy
        self.logger.info(f"🔄 Email strategy changed to: {strategy.__class__.__name__}")

    def send_email(self, recipients, subject, content, sender_info):
        self.logger.info(f"🚀 Email service initiated for: '{subject}'")
        self.logger.info(f"📋 Processing {len(recipients)} recipients")
        return self._strategy.send_email(recipients, subject, content, sender_info)


# Factory Pattern for Email Service
class EmailServiceFactory:
    @staticmethod
    def create_email_service(service_type='django'):
        logger.info(f"🏭 Creating email service of type: {service_type}")
        if service_type == 'django':
            return EmailService(DjangoEmailStrategy())
        else:
            logger.error(f"❌ Unknown email service type requested: {service_type}")
            raise ValueError(f"Unknown email service type: {service_type}")