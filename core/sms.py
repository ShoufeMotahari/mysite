#
# sms_ir = SmsIr('un7i93fQdsGxOqFHpF5Z3bccQfA8MWFFJKb24lpUWeJfpufG', 30007732904200, )
#
# sms_ir.send_verify_code(+989931755521, 808559, [
#     {"name": "CODE", "value": '45455'}
# ], )
import logging

from django.conf import settings
from sms_ir import SmsIr

logger = logging.getLogger("accounts_")

# تنظیمات اولیه API از settings یا .env
API_KEY = getattr(settings, "SMS_API_KEY", "your-api-key")
LINE_NUMBER = getattr(settings, "SMS_LINE_NUMBER", "30007732904200")
TEMPLATE_ID = getattr(settings, "SMS_TEMPLATE_ID", 808559)

# شی اصلی SMS.IR
sms_ir = SmsIr(API_KEY, LINE_NUMBER)


#
# Check core/sms.py
def send_verification_sms(mobile, code):
    try:
        # Your SMS sending logic here
        print(f"Sending SMS to {mobile}: {code}")  # Add for debugging
        # Actual SMS sending code
        return True
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        return False
