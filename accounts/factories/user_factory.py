from users.models import User, RegisterToken
from core.sms import send_verification_sms
import random

def generate_code():
    return str(random.randint(100000, 999999))

class UserFactory:
    @staticmethod
    def create_user_with_token(mobile):
        user = User.objects.create(mobile=mobile, is_active=False)
        code = generate_code()
        RegisterToken.objects.create(user=user, code=code)
        send_verification_sms(mobile, code)
        return user