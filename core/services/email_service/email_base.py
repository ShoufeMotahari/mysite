import re
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse

from .email_strategies import EmailStrategy, DjangoEmailStrategy
from .email_validators import EmailValidator
from .email_utils import get_site_url_from_request, strip_html_tags
from .email_templates import (
    render_email_templates,
    generate_fallback_activation_content,
    generate_fallback_password_reset_content
)

logger = logging.getLogger(__name__)


class EmailService:
    """Main email service for sending emails"""

    def __init__(self, strategy: EmailStrategy = None):
        self._strategy = strategy or DjangoEmailStrategy()
        self.logger = logging.getLogger("email_service")

    def set_strategy(self, strategy: EmailStrategy):
        """Change email sending strategy"""
        self._strategy = strategy
        self.logger.info(f"Email strategy changed to: {strategy.__class__.__name__}")

    def send_email(self, recipients, subject, content, sender_info="System"):
        """Send email using the current strategy"""
        self.logger.info(f"Email service initiated for: '{subject}'")
        self.logger.info(f"Processing {len(recipients)} recipients")

        # Validate inputs
        if not recipients:
            error_msg = "No recipients provided"
            self.logger.error(f"{error_msg}")
            return False, error_msg, {}

        if not subject:
            error_msg = "No subject provided"
            self.logger.error(f"{error_msg}")
            return False, error_msg, {}

        if not content:
            error_msg = "No content provided"
            self.logger.error(f"{error_msg}")
            return False, error_msg, {}

        return self._strategy.send_email(recipients, subject, content, sender_info)

    def send_single_email(self, recipient_email: str, subject: str,
                          html_content: str = None, text_content: str = None):
        """Send email to a single recipient with HTML and text content"""
        try:
            # Validate email
            if not EmailValidator.is_valid_email(recipient_email):
                error_msg = f"Invalid email address: {recipient_email}"
                self.logger.error(error_msg)
                return False, error_msg

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

            # Use text_content as body, fallback to html_content without tags
            body = text_content
            if not body and html_content:
                # Simple HTML tag removal for fallback
                body = strip_html_tags(html_content)

            msg = EmailMultiAlternatives(
                subject=subject,
                body=body or "Please view the HTML version of this email.",
                from_email=from_email,
                to=[recipient_email],
            )

            # Add HTML alternative if provided
            if html_content:
                msg.attach_alternative(html_content, "text/html")

            result = msg.send()

            if result:
                self.logger.info(f"Single email sent successfully to {recipient_email}")
                return True, "Email sent successfully"
            else:
                error_msg = f"Failed to send email to {recipient_email}"
                self.logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Exception sending email to {recipient_email}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def send_activation_email(self, user, token, request=None):
        """Send account activation email with dynamic URL detection"""
        try:
            subject = "Account Activation"
            site_url = get_site_url_from_request(request)
            activation_url = f"{site_url}{reverse('users:activate')}?token={token}"
            mobile = str(user.mobile)

            # Prepare context for templates
            context = {
                "user": user,
                "mobile": mobile,
                "activation_url": activation_url,
                "site_name": getattr(settings, "SITE_NAME", "Our Site"),
                "site_url": site_url,
                "support_email": getattr(settings, "SUPPORT_EMAIL", settings.DEFAULT_FROM_EMAIL),
            }

            # Try to render templates
            html_content, text_content = render_email_templates("activation_email", context)

            # Use fallback if templates not found
            if not html_content:
                html_content, text_content = generate_fallback_activation_content(context)

            success, message = self.send_single_email(
                recipient_email=user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )

            if success:
                self.logger.info(f"Activation email sent to {user.email} with URL: {activation_url}")
            else:
                self.logger.error(f"Failed to send activation email to {user.email}: {message}")

            return success

        except Exception as e:
            self.logger.error(f"Error sending activation email to {user.email}: {str(e)}")
            return False

    def send_password_reset_email(self, user, token, request=None):
        """Send password reset email with dynamic URL detection"""
        try:
            subject = "Password Reset"
            site_url = get_site_url_from_request(request)
            reset_url = f"{site_url}{reverse('reset-password-email')}?token={token}"
            mobile = str(user.mobile)

            # Prepare context for templates
            context = {
                "user": user,
                "mobile": mobile,
                "reset_url": reset_url,
                "site_name": getattr(settings, "SITE_NAME", "Our Site"),
                "site_url": site_url,
                "support_email": getattr(settings, "SUPPORT_EMAIL", settings.DEFAULT_FROM_EMAIL),
            }

            # Try to render templates
            html_content, text_content = render_email_templates("password_reset_email", context)

            # Use fallback if templates not found
            if not html_content:
                html_content, text_content = generate_fallback_password_reset_content(context)

            success, message = self.send_single_email(
                recipient_email=user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )

            if success:
                self.logger.info(f"Password reset email sent to {user.email} with URL: {reset_url}")
            else:
                self.logger.error(f"Failed to send password reset email to {user.email}: {message}")

            return success

        except Exception as e:
            self.logger.error(f"Error sending password reset email to {user.email}: {str(e)}")
            return False