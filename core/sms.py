from sms_ir import SmsIr
#
# sms_ir = SmsIr('un7i93fQdsGxOqFHpF5Z3bccQfA8MWFFJKb24lpUWeJfpufG', 30007732904200, )
#
# sms_ir.send_verify_code(+989931755521, 808559, [
#     {"name": "CODE", "value": '45455'}
# ], )
import logging
from sms_ir import SmsIr
from django.conf import settings

logger = logging.getLogger('accounts')

# تنظیمات اولیه API از settings یا .env
API_KEY = getattr(settings, "SMS_API_KEY", "your-api-key")
LINE_NUMBER = getattr(settings, "SMS_LINE_NUMBER", "30007732904200")
TEMPLATE_ID = getattr(settings, "SMS_TEMPLATE_ID", 808559)

# شی اصلی SMS.IR
sms_ir = SmsIr(API_KEY, LINE_NUMBER)


#
def send_verification_sms(mobile, code):
    logger.info(f"در حال ارسال پیامک به {mobile} با کد {code}")

    try:
        logger.info(f"در حال ارسال پیامک به {mobile} با کد {code}" )
        sms_ir.send_verify_code(
            mobile,
            TEMPLATE_ID,
            [{"name": "CODE", "value": code}]
        )
        logger.info(f"ارسال پیامک موفق برای شماره{mobile}")
    except Exception as e:
        logger.error("خطا در ارسال پیامک به %s: %s", mobile, str(e))
