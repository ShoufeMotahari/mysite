# -*- coding: utf-8 -*-

from email.header import Header

from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger('emails')


from django.core.mail import EmailMultiAlternatives

def send_activation_email(user, token):
    try:
        subject = str(Header('فعال‌سازی حساب کاربری', 'utf-8'))  # encode explicitly
        from_email = str(Header(settings.DEFAULT_FROM_EMAIL, 'utf-8'))

        activation_url = f"{settings.SITE_URL}{reverse('users:activate')}?token={token}"
        mobile = str(user.mobile)

        text_content = f"""
سلام {mobile},

برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:
{activation_url}

این لینک تا 15 دقیقه معتبر است.

با تشکر
        """

        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body dir="rtl">
            <h2>فعال‌سازی حساب کاربری</h2>
            <p>سلام {mobile},</p>
            <p>برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:</p>
            <a href="{activation_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">فعال‌سازی حساب</a>
            <p>این لینک تا 15 دقیقه معتبر است.</p>
            <p>با تشکر</p>
        </body>
        </html>
        """

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[user.email],
        )
        msg.encoding = 'utf-8'  # ✅ critical!
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Activation email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send activation email to {user.email}: {str(e)}")
        return False

def send_password_reset_email(user, token):
    """Send password reset email"""
    try:
        subject = 'بازیابی رمز عبور'
        reset_url = f"{settings.SITE_URL}{reverse('reset-password-email')}?token={token}"

        text_content = f"""
سلام {user.mobile},

برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:
{reset_url}

این لینک تا 15 دقیقه معتبر است.

اگر شما درخواست بازیابی رمز عبور نداده‌اید، این پیام را نادیده بگیرید.

با تشکر
        """

        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body dir="rtl">
            <h2>بازیابی رمز عبور</h2>
            <p>سلام {user.mobile},</p>
            <p>برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:</p>
            <a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">بازیابی رمز عبور</a>
            <p>این لینک تا 15 دقیقه معتبر است.</p>
            <p>اگر شما درخواست بازیابی رمز عبور نداده‌اید، این پیام را نادیده بگیرید.</p>
            <p>با تشکر</p>
        </body>
        </html>
        """

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Password reset email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False