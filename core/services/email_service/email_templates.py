import logging
from pathlib import Path
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def load_email_template_fallback(template_path, context_data):
    """Fallback template loader for custom template files"""
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
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


def render_email_templates(template_base_name, context):
    """Render HTML and text email templates with fallback"""
    html_template = f"emails/{template_base_name}.html"
    text_template = f"emails/{template_base_name}.txt"

    html_content = None
    text_content = None

    try:
        # Try Django templates first
        html_content = render_to_string(html_template, context)
        text_content = render_to_string(text_template, context)
        logger.info(f"Using Django templates for {template_base_name}")
    except Exception as template_error:
        logger.warning(f"Django template loading failed for {template_base_name}: {template_error}")

        # Try custom template loading
        html_content = load_email_template_fallback(f"{template_base_name}.html", context)

    return html_content, text_content


def generate_fallback_activation_content(context):
    """Generate fallback content for activation emails"""
    mobile = context.get('mobile', 'User')
    activation_url = context.get('activation_url')
    site_name = context.get('site_name', 'Our Site')

    text_content = f"""Hi {mobile},

We're happy to have you join our site!

To activate your account, please click the link below:
{activation_url}

This link is valid for 15 minutes.

Thank you,
Support Team"""

    html_content = f"""
    <html>
    <body>
        <h2>Account Activation</h2>
        <p>Hi {mobile},</p>
        <p>We're happy to have you join {site_name}!</p>
        <p>To activate your account, please click the link below:</p>
        <p><a href="{activation_url}">Activate Account</a></p>
        <p>This link is valid for 15 minutes.</p>
        <p>Thank you,<br>Support Team</p>
    </body>
    </html>
    """

    return html_content, text_content


def generate_fallback_password_reset_content(context):
    """Generate fallback content for password reset emails"""
    mobile = context.get('mobile', 'User')
    reset_url = context.get('reset_url')

    text_content = f"""Hi {mobile},

We received a request to reset your account password.

To set a new password, click the link below:
{reset_url}

This link is valid for 15 minutes.

If you did not request a password reset, please ignore this message.

Thank you,
Support Team"""

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

    return html_content, text_content


def generate_fallback_comment_notification_content(comment, context):
    """Generate fallback content for comment notifications"""
    user_ip = context.get('user_ip', 'Unknown')

    html_content = f"""
    <html>
    <body>
        <h2>New Comment</h2>
        <p><strong>User:</strong> {comment.user.username}</p>
        <p><strong>Subject:</strong> {getattr(comment, 'subject', 'New Comment')}</p>
        <p><strong>Content:</strong></p>
        <p>{comment.content}</p>
        <p><strong>Date:</strong> {comment.created_at}</p>
        {f'<p><strong>IP:</strong> {user_ip}</p>' if user_ip != 'Unknown' else ''}
    </body>
    </html>
    """

    ip_info = f"IP: {user_ip}" if user_ip != 'Unknown' else ""
    text_content = f"""
New Comment

User: {comment.user.username}
Subject: {getattr(comment, 'subject', 'New Comment')}
Content: {comment.content}
Date: {comment.created_at}
{ip_info}
    """

    return html_content, text_content
