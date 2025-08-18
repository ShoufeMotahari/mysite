import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from .models import emailLog  # الان این مدل داخل users/models.py خواهد بود

logger = logging.getLogger("emails")


@shared_task
def send_single_email(recipient_email, subject, content, from_email=None):
    """
    ارسال یک ایمیل تکی به صورت async
    """
    User = get_user_model()
    user = User.objects.filter(email=recipient_email).first()

    try:
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL

        send_mail(
            subject=subject,
            message="",
            from_email=from_email,
            recipient_list=[recipient_email],
            html_message=content,
            fail_silently=False,
        )

        # ثبت لاگ موفق
        if user:
            EmailLog.objects.create(
                recipient=user, subject=subject, content=content, status="sent"
            )

        logger.info(f"Single email sent successfully to {recipient_email}")
        return {"status": "sent", "recipient": recipient_email}

    except Exception as e:
        logger.error(f"Failed to send single email to {recipient_email}: {str(e)}")
        # ثبت لاگ شکست
        if user:
            EmailLog.objects.create(
                recipient=user,
                subject=subject,
                content=content,
                status="failed",
                error_message=str(e),
            )
        raise


@shared_task
def cleanup_old_email_logs():
    """
    پاک کردن لاگ ایمیل‌های قدیمی (بیشتر از 30 روز)
    """
    from datetime import timedelta

    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = EmailLog.objects.filter(sent_at__lt=cutoff_date).delete()[0]

    logger.info(f"Cleaned up {deleted_count} old email logs")
    return {"deleted_count": deleted_count}
