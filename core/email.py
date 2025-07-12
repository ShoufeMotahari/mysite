from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

import logging
logger = logging.getLogger('core')

def send_activation_email(user, token):
    subject = 'فعالسازی حساب کاربری'
    message = 'برای فعالسازی روی لینک کلیک کنید'
    logger.info(user.email)
    logger.info('user.email')
    to_email = user.email

    # قالب HTML با context
    html_message = render_to_string('emails/activation_email.html', {
        'user': user,
        'activation_link': f"{settings.SITE_URL}/accounts/activate/?token={token}"
    })
    logger.info("ایمیل فعال‌سازی برای %s ارسال شد", to_email)

    try:
        logger.info("ایمیل فعال‌سازی برای %s ارسال شد", to_email)

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            html_message=html_message,
        )
        # logger.info(subject)
        # logger.info(message)
        logger.info(to_email)
        logger.info(f"{settings.SITE_URL}/accounts/activate/?token={token}")
        logger.info(user.mobile)
        logger.info('user.mobile')
    except Exception as e:
        logger.error("خطا در ارسال ایمیل فعال‌سازی به %s: %s", to_email, str(e))
