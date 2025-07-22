from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger('emails')


def send_activation_email(user, token):
    """Send account activation email"""
    try:
        subject = 'فعال‌سازی حساب کاربری'
        activation_url = f"{settings.SITE_URL}{reverse('activate')}?token={token}"

        message = f"""
سلام {user.mobile},

برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:
{activation_url}

این لینک تا 15 دقیقه معتبر است.

با تشکر
        """

        html_message = f"""
        <html>
        <body dir="rtl">
            <h2>فعال‌سازی حساب کاربری</h2>
            <p>سلام {user.mobile},</p>
            <p>برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:</p>
            <a href="{activation_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">فعال‌سازی حساب</a>
            <p>این لینک تا 15 دقیقه معتبر است.</p>
            <p>با تشکر</p>
        </body>
        </html>
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

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

        message = f"""
سلام {user.mobile},

برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:
{reset_url}

این لینک تا 15 دقیقه معتبر است.

اگر شما درخواست بازیابی رمز عبور نداده‌اید، این پیام را نادیده بگیرید.

با تشکر
        """

        html_message = f"""
        <html>
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

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Password reset email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False