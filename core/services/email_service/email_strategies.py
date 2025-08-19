import logging
from abc import ABC, abstractmethod
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .email_validators import EmailValidator
from .email_utils import is_html_content

logger = logging.getLogger(__name__)


class EmailStrategy(ABC):
    """Abstract base class for email sending strategies"""

    @abstractmethod
    def send_email(self, recipients, subject, content, sender_info):
        """Send email to recipients"""
        pass


class DjangoEmailStrategy(EmailStrategy):
    """Django-based email sending strategy"""

    def send_email(self, recipients, subject, content, sender_info):
        try:
            # Validate recipients first
            valid_users, invalid_users = EmailValidator.validate_users(recipients)

            # Log validation results
            logger.info(f"User validation results:")
            logger.info(f"  Valid users: {len(valid_users)}")
            logger.info(f"  Invalid users: {len(invalid_users)}")

            # Log invalid users details
            if invalid_users:
                logger.warning(f"Invalid users found ({len(invalid_users)}):")
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
                logger.error(f"{error_msg}")
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
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
            recipient_emails = [user.email for user in valid_users]

            logger.info(f"Preparing email for {len(valid_users)} valid users:")
            for user in valid_users:
                logger.info(f"  {user.username} ({user.email})")

            logger.info(
                f"Sending email: '{subject}' to {len(recipient_emails)} recipients"
            )

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=content,
                from_email=from_email,
                to=recipient_emails,
            )

            # Add HTML alternative if content contains HTML
            if is_html_content(content):
                msg.attach_alternative(content, "text/html")

            # Send email
            result = msg.send()

            if result:
                success_msg = (
                    f"Email sent successfully to {len(recipient_emails)} valid users"
                )
                logger.info(f"{success_msg}")

                # Log summary
                logger.info(f"Email sending summary:")
                logger.info(f"  Subject: '{subject}'")
                logger.info(f"  Sender: {sender_info}")
                logger.info(f"  Total requested: {len(recipients)}")
                logger.info(f"  Successfully sent: {len(recipient_emails)}")
                logger.info(f"  Invalid/skipped: {len(invalid_users)}")

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
                logger.error(f"{error_msg}")
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
            logger.error(f"{error_msg}")
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
