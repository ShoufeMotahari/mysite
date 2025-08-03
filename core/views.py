from django.shortcuts import render
from django.http import HttpResponse
import logging
logger = logging.getLogger('core')
def home_view(request):
    return HttpResponse("<h1>من بالاخره اجرا شدم :)✅</h1>")

# core/views.py
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

def test_email_view(request):
    try:
        logger.warning(f"📧 Trying to send email from: {settings.DEFAULT_FROM_EMAIL}")

        send_mail(
            subject='تست ایمیل از هاست',
            message='این ایمیل تستی از ویوی تستی هست.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['your_email@example.com'],  # آدرس ایمیل خودت رو بذار اینجا
            fail_silently=False,
        )

        return HttpResponse("✅ ایمیل با موفقیت ارسال شد.")
    except Exception as e:
        logger.error(f"❌ خطا در ارسال ایمیل: {e}")
        return HttpResponse(f"❌ خطا در ارسال ایمیل: {e}")

