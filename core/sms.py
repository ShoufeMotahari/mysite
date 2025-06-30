import requests
import json
from django.conf import settings

def send_verification_sms(mobile, code):
    url = "https://api.sms.ir/v1/send/verify"

    payload = {
        "mobile": mobile,
        "templateId": "کد_تمپلیت_شما",  # باید از پنل sms.ir بگیری
        "parameters": [
            {"name": "CODE", "value": code}
        ]
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-API-KEY': settings.SMS_API_KEY
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response.json()