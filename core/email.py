# -*- coding: utf-8 -*-

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger('emails')


def send_activation_email(user, token):
    try:
        # Use explicit Unicode strings
        subject = 'فعال‌سازی حساب کاربری'

        activation_url = f"{settings.SITE_URL}{reverse('users:activate')}?token={token}"
        mobile = str(user.mobile)

        text_content = f"""سلام {mobile},

برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:
{activation_url}

این لینک تا 15 دقیقه معتبر است.

با تشکر"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body dir="rtl" style="font-family: 'Tahoma', 'Arial', sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #333;">فعال‌سازی حساب کاربری</h2>
        <p>سلام {mobile},</p>
        <p>برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:</p>
        <div style="text-align: center; margin: 20px 0;">
            <a href="{activation_url}" style="background-color: #007bff; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">فعال‌سازی حساب</a>
        </div>
        <p>این لینک تا 15 دقیقه معتبر است.</p>
        <p>با تشکر</p>
    </div>
</body>
</html>"""

        # Create message with explicit encoding
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

        # Set encoding and content type explicitly
        msg.content_subtype = "plain"
        msg.encoding = 'utf-8'
        msg.attach_alternative(html_content, "text/html")

        # Send the email
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
    """Send password reset email with proper Unicode handling"""
    try:
        subject = 'بازیابی رمز عبور'
        reset_url = f"{settings.SITE_URL}{reverse('reset-password-email')}?token={token}"

        text_content = f"""سلام {user.mobile},

برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:
{reset_url}

این لینک تا 15 دقیقه معتبر است.

اگر شما درخواست بازیابی رمز عبور نداده‌اید، این پیام را نادیده بگیرید.

با تشکر"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body dir="rtl" style="font-family: 'Tahoma', 'Arial', sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #333;">بازیابی رمز عبور</h2>
        <p>سلام {user.mobile},</p>
        <p>برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:</p>
        <div style="text-align: center; margin: 20px 0;">
            <a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block;">بازیابی رمز عبور</a>
        </div>
        <p>این لینک تا 15 دقیقه معتبر است.</p>
        <p>اگر شما درخواست بازیابی رمز عبور نداده‌اید، این پیام را نادیده بگیرید.</p>
        <p>با تشکر</p>
    </div>
</body>
</html>"""

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