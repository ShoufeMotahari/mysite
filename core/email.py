# emails.py - Updated with template loading
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.template import Context, Template
import logging

logger = logging.getLogger('emails')

# Get the base directory for templates
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / 'templates' / 'emails'


def load_email_template(template_name, context_data):
    """
    Load and render HTML email template with context data

    Args:
        template_name (str): Name of the template file
        context_data (dict): Data to replace in template

    Returns:
        str: Rendered HTML content
    """
    global template_content
    try:
        template_path = TEMPLATES_DIR / template_name

        if not template_path.exists():
            logger.error(f"Template not found: {template_path}")
            return None

        # Read the template file
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()

        # Replace placeholders with actual data
        for key, value in context_data.items():
            placeholder = f"{{{{{key}}}}}"
            template_content = template_content.replace(placeholder, str(value))

        return template_content

    except Exception as e:
        logger.error(f"Error loading template {template_name}: {str(e)}")
        return None


def load_email_template_django(template_name, context_data):
    """
    Alternative method using Django's template system (if preferred)

    Args:
        template_name (str): Name of the template file (e.g., 'emails/activation_email.html')
        context_data (dict): Data to pass to template

    Returns:
        str: Rendered HTML content
    """
    try:
        return render_to_string(template_name, context_data)
    except Exception as e:
        logger.error(f"Error rendering Django template {template_name}: {str(e)}")
        return None


def send_activation_email(user, token):
    """
    Send activation email using HTML template
    """
    try:
        subject = 'فعال‌سازی حساب کاربری'

        activation_url = f"{settings.SITE_URL}{reverse('users:activate')}?token={token}"
        mobile = str(user.mobile)

        # Plain text version
        text_content = f"""سلام {mobile},

از ثبت نام شما در سایت ما خوشحالیم!

برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:
{activation_url}

این لینک تا 15 دقیقه معتبر است.

با تشکر
تیم پشتیبانی"""

        # Prepare context data for template
        context_data = {
            'mobile': mobile,
            'activation_url': activation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'سایت ما'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL)
        }

        # Load HTML template
        html_content = load_email_template('activation_email.html', context_data)

        if not html_content:
            logger.error("Failed to load activation email template")
            return False

        # Create and send email
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

        # Set encoding and attach HTML version
        msg.content_subtype = "plain"
        msg.encoding = 'utf-8'
        msg.attach_alternative(html_content, "text/html")

        result = msg.send()

        if result:
            logger.info(f"Activation email sent successfully to {user.email}")
            return True
        else:
            logger.error(f"Failed to send activation email to {user.email}: No result returned")
            return False

    except Exception as e:
        logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
        return False


def send_password_reset_email(user, token):
    """
    Send password reset email using HTML template
    """
    try:
        subject = 'بازیابی رمز عبور'
        reset_url = f"{settings.SITE_URL}{reverse('reset-password-email')}?token={token}"
        mobile = str(user.mobile)

        # Plain text version
        text_content = f"""سلام {mobile},

درخواست بازیابی رمز عبور برای حساب کاربری شما دریافت شد.

برای تنظیم رمز عبور جدید روی لینک زیر کلیک کنید:
{reset_url}

این لینک تا 15 دقیقه معتبر است.

اگر شما درخواست بازیابی رمز عبور نداده‌اید، این پیام را نادیده بگیرید.

با تشکر
تیم پشتیبانی"""

        # Prepare context data for template
        context_data = {
            'mobile': mobile,
            'reset_url': reset_url,
            'site_name': getattr(settings, 'SITE_NAME', 'سایت ما'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL)
        }

        # Load HTML template
        html_content = load_email_template('password_reset_email.html', context_data)

        if not html_content:
            logger.error("Failed to load password reset email template")
            return False

        # Create and send email
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )

        msg.content_subtype = "plain"
        msg.encoding = 'utf-8'
        msg.attach_alternative(html_content, "text/html")

        result = msg.send()

        if result:
            logger.info(f"Password reset email sent successfully to {user.email}")
            return True
        else:
            logger.error(f"Failed to send password reset email to {user.email}: No result returned")
            return False

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False


# Alternative functions using Django's template system
def send_activation_email_django_template(user, token):
    """
    Send activation email using Django's template system
    """
    try:
        subject = 'فعال‌سازی حساب کاربری'

        activation_url = f"{settings.SITE_URL}{reverse('users:activate')}?token={token}"

        context = {
            'user': user,
            'mobile': str(user.mobile),
            'activation_url': activation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'سایت ما'),
        }

        # Render templates using Django's template system
        text_content = render_to_string('emails/activation_email.txt', context)
        html_content = render_to_string('emails/activation_email.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

        msg.attach_alternative(html_content, "text/html")
        result = msg.send()

        if result:
            logger.info(f"Activation email sent successfully to {user.email}")
            return True
        else:
            logger.error(f"Failed to send activation email to {user.email}")
            return False

    except Exception as e:
        logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
        return False
