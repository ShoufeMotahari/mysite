# emails.py - Updated with English messages
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


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / 'templates' / 'emails'


def load_email_template(template_name, context_data):
    """Load and render HTML email template with context data"""
    global template_content
    try:
        template_path = TEMPLATES_DIR / template_name

        if not template_path.exists():
            logger.error(f"Template not found: {template_path}")
            return None

        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()

        for key, value in context_data.items():
            placeholder = f"{{{{{key}}}}}"
            template_content = template_content.replace(placeholder, str(value))

        return template_content

    except Exception as e:
        logger.error(f"Error loading template {template_name}: {str(e)}")
        return None


def load_email_template_django(template_name, context_data):
    """Alternative method using Django's template system"""
    try:
        return render_to_string(template_name, context_data)
    except Exception as e:
        logger.error(f"Error rendering Django template {template_name}: {str(e)}")
        return None


def send_activation_email(user, token):
    """Send account activation email using HTML template"""
    try:
        subject = 'Account Activation'
        activation_url = f"{settings.SITE_URL}{reverse('users:activate')}?token={token}"
        mobile = str(user.mobile)

        text_content = f"""Hi {mobile},

We're happy to have you join our site!

To activate your account, please click the link below:
{activation_url}

This link is valid for 15 minutes.

Thank you,
Support Team"""

        context_data = {
            'mobile': mobile,
            'activation_url': activation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Our Site'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL)
        }

        html_content = load_email_template('activation_email.html', context_data)

        if not html_content:
            logger.error("Failed to load activation email template")
            return False

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

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
    """Send password reset email using HTML template"""
    try:
        subject = 'Password Reset'
        reset_url = f"{settings.SITE_URL}{reverse('reset-password-email')}?token={token}"
        mobile = str(user.mobile)

        text_content = f"""Hi {mobile},

We received a request to reset your account password.

To set a new password, click the link below:
{reset_url}

This link is valid for 15 minutes.

If you did not request a password reset, please ignore this message.

Thank you,
Support Team"""

        context_data = {
            'mobile': mobile,
            'reset_url': reset_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Our Site'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL)
        }

        html_content = load_email_template('password_reset_email.html', context_data)

        if not html_content:
            logger.error("Failed to load password reset email template")
            return False

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


def send_activation_email_django_template(user, token):
    """Send account activation email using Django's template system"""
    try:
        subject = 'Account Activation'
        activation_url = f"{settings.SITE_URL}{reverse('users:activate')}?token={token}"

        context = {
            'user': user,
            'mobile': str(user.mobile),
            'activation_url': activation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Our Site'),
        }

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
