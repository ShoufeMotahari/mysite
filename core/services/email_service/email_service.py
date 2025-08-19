import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


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


def _get_site_url_from_request(request):
    """Get the site URL from request with proper protocol detection"""
    if request:
        protocol = "https" if request.is_secure() else "http"
        domain = request.get_host()
        return f"{protocol}://{domain}"
    else:
        return getattr(settings, 'SITE_URL', 'http://localhost:8000')


def _load_email_template_fallback(template_path, context_data):
    """Fallback template loader for custom template files"""
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent
        TEMPLATES_DIR = BASE_DIR / "templates" / "emails"
        full_template_path = TEMPLATES_DIR / template_path

        if not full_template_path.exists():
            logger.warning(f"Custom template not found: {full_template_path}")
            return None

        with open(full_template_path, "r", encoding="utf-8") as file:
            template_content = file.read()

        # Simple placeholder replacement
        for key, value in context_data.items():
            placeholder = f"{{{{{key}}}}}"
            template_content = template_content.replace(placeholder, str(value))

        return template_content

    except Exception as e:
        logger.error(f"Error loading custom template {template_path}: {str(e)}")
        return None


class DjangoEmailStrategy(EmailStrategy):
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
            if _is_html_content(content):
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


class EmailService:
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
                body = re.sub(r'<[^>]+>', '', html_content)

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
            site_url = _get_site_url_from_request(request)
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

            # Try Django templates first
            try:
                html_content = render_to_string("emails/activation_email.html", context)
                text_content = render_to_string("emails/activation_email.txt", context)
                self.logger.info("Using Django templates for activation email")
            except Exception as template_error:
                self.logger.warning(f"Django template loading failed: {template_error}")

                # Try custom template loading
                html_content = _load_email_template_fallback("activation_email.html", context)

                # Fallback text content
                text_content = f"""Hi {mobile},

We're happy to have you join our site!

To activate your account, please click the link below:
{activation_url}

This link is valid for 15 minutes.

Thank you,
Support Team"""

                if not html_content:
                    # Final fallback HTML
                    html_content = f"""
                    <html>
                    <body>
                        <h2>Account Activation</h2>
                        <p>Hi {mobile},</p>
                        <p>We're happy to have you join {context['site_name']}!</p>
                        <p>To activate your account, please click the link below:</p>
                        <p><a href="{activation_url}">Activate Account</a></p>
                        <p>This link is valid for 15 minutes.</p>
                        <p>Thank you,<br>Support Team</p>
                    </body>
                    </html>
                    """

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
            site_url = _get_site_url_from_request(request)
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

            # Try Django templates first
            try:
                html_content = render_to_string("emails/password_reset_email.html", context)
                text_content = render_to_string("emails/password_reset_email.txt", context)
                self.logger.info("Using Django templates for password reset email")
            except Exception as template_error:
                self.logger.warning(f"Django template loading failed: {template_error}")

                # Try custom template loading
                html_content = _load_email_template_fallback("password_reset_email.html", context)

                # Fallback text content
                text_content = f"""Hi {mobile},

We received a request to reset your account password.

To set a new password, click the link below:
{reset_url}

This link is valid for 15 minutes.

If you did not request a password reset, please ignore this message.

Thank you,
Support Team"""

                if not html_content:
                    # Final fallback HTML
                    html_content = f"""
                    <html>
                    <body>
                        <h2>Password Reset</h2>
                        <p>Hi {mobile},</p>
                        <p>We received a request to reset your account password.</p>
                        <p>To set a new password, click the link below:</p>
                        <p><a href="{reset_url}">Reset Password</a></p>
                        <p>This link is valid for 15 minutes.</p>
                        <p>If you did not request a password reset, please ignore this message.</p>
                        <p>Thank you,<br>Support Team</p>
                    </body>
                    </html>
                    """

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


class CommentEmailService:
    """Service for sending comment-related email notifications"""

    def __init__(self, email_service: EmailService = None):
        self.email_service = email_service or EmailService()

    @staticmethod
    def _get_admin_emails() -> List[str]:
        """Get admin email addresses from settings"""
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

    @staticmethod
    def _prepare_email_context(comment, user_ip: str = None) -> Dict:
        """Prepare context for email templates"""
        return {
            'comment': comment,
            'user': comment.user,
            'user_ip': user_ip,
            'site_name': getattr(settings, 'SITE_NAME', 'Website'),
            'domain': getattr(settings, 'SITE_DOMAIN', 'example.com'),
        }

    def send_comment_notification(self, comment, user_ip: str = None) -> bool:
        """Send email notification to admins when a new comment is posted"""
        try:
            # Check if notifications are enabled
            if not getattr(settings, 'COMMENT_NOTIFICATION_ENABLED', True):
                logger.info(f"Comment notifications disabled - skipping for comment {comment.id}")
                return False

            # Get admin emails
            admin_emails = self._get_admin_emails()
            if not admin_emails:
                logger.warning("No admin emails configured for comment notifications")
                return False

            # Prepare email context
            context = self._prepare_email_context(comment, user_ip)

            # Generate subject
            subject = self._get_email_subject(comment)

            # Try to render templates, fallback to simple content
            try:
                html_content = render_to_string('emails/comment_notification.html', context)
                text_content = render_to_string('emails/comment_notification.txt', context)
            except Exception as template_error:
                logger.warning(f"Template rendering failed, using fallback: {template_error}")
                html_content = self._get_fallback_html_content(comment, context)
                text_content = self._get_fallback_text_content(comment, context)

            # Send email to each admin
            success_count = 0
            for admin_email in admin_emails:
                success, message = self.email_service.send_single_email(
                    recipient_email=admin_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                if success:
                    success_count += 1

            if success_count > 0:
                logger.info(
                    f"Comment notification sent to {success_count}/{len(admin_emails)} admins - Comment ID: {comment.id}")
                return True
            else:
                logger.error(f"Failed to send comment notification to any admin - Comment ID: {comment.id}")
                return False

        except Exception as e:
            logger.error(f"Error sending comment notification - Comment ID: {comment.id}, Error: {str(e)}")
            return False

    @staticmethod
    def _get_email_subject(comment) -> str:
        """Generate email subject with safe handling"""
        prefix = getattr(settings, 'COMMENT_NOTIFICATION_SUBJECT_PREFIX', '[Site] ')
        user = comment.user

        # Safe handling of optional subject field
        if hasattr(comment, 'subject') and comment.subject and comment.subject.strip():
            subject_text = comment.subject.strip()[:50]
            if len(comment.subject) > 50:
                subject_text += "..."
        else:
            # Use first part of content if no subject
            subject_text = comment.content[:50] + "..." if len(comment.content) > 50 else comment.content

        subject = f"{prefix}New comment from {user.username} - {subject_text}"
        return subject

    @staticmethod
    def _get_fallback_html_content(comment, context):
        """Generate fallback HTML content if template doesn't exist"""
        return f"""
        <html>
        <body>
            <h2>New Comment</h2>
            <p><strong>User:</strong> {comment.user.username}</p>
            <p><strong>Subject:</strong> {getattr(comment, 'subject', 'New Comment')}</p>
            <p><strong>Content:</strong></p>
            <p>{comment.content}</p>
            <p><strong>Date:</strong> {comment.created_at}</p>
            {f'<p><strong>IP:</strong> {context.get("user_ip", "Unknown")}</p>' if context.get("user_ip") else ''}
        </body>
        </html>
        """

    @staticmethod
    def _get_fallback_text_content(comment, context):
        """Generate fallback text content if template doesn't exist"""
        ip_info = f"IP: {context.get('user_ip', 'Unknown')}" if context.get('user_ip') else ""

        return f"""
New Comment

User: {comment.user.username}
Subject: {getattr(comment, 'subject', 'New Comment')}
Content: {comment.content}
Date: {comment.created_at}
{ip_info}
        """


class EmailTestService:
    """Service for testing email configuration"""

    def __init__(self, email_service: EmailService = None):
        self.email_service = email_service or EmailService()

    def test_email_configuration(self) -> Dict[str, any]:
        """Test email configuration and send a test email"""
        try:
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

            # Send test email using the email service
            success_count = 0
            for admin_email in admin_emails:
                success, message = self.email_service.send_single_email(
                    recipient_email=admin_email,
                    subject='Test Email - Comment Notification System',
                    text_content='This is a test email to verify the comment notification system is working correctly.',
                    html_content="""
                    <html>
                    <body>
                        <h2>Test Email</h2>
                        <p>This is a test email to verify the comment notification system is working correctly.</p>
                        <p>If you received this email, your email configuration is working properly.</p>
                    </body>
                    </html>
                    """
                )
                if success:
                    success_count += 1

            if success_count > 0:
                test_result['success'] = True
                test_result[
                    'message'] = f'Test email sent successfully to {success_count}/{len(admin_emails)} recipients'
            else:
                test_result['message'] = 'Failed to send test email to any recipient'

            return test_result

        except Exception as e:
            return {
                'success': False,
                'message': f'Email test failed: {str(e)}',
                'details': {'error': str(e)}
            }


# Convenience functions for backward compatibility
def get_email_service():
    """Get a default email service instance"""
    return EmailService()


def send_activation_email(user, token, request=None):
    """Backward compatibility function for activation emails"""
    email_service = EmailService()
    return email_service.send_activation_email(user, token, request)


def send_password_reset_email(user, token, request=None):
    """Backward compatibility function for password reset emails"""
    email_service = EmailService()
    return email_service.send_password_reset_email(user, token, request)