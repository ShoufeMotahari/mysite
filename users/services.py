# users/services.py
import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail
from smsir import SmsIr

from filemanager.forms import User
from users.models.token.verificationToken import VerificationToken

logger = logging.getLogger("users")


# Abstract Factory
class NotificationService(ABC):
    @abstractmethod
    def send_verification_code(self, user, token):
        pass

    @abstractmethod
    def send_password_reset(self, user, token):
        pass


# SMS Service Implementation
class SMSService(NotificationService):
    def __init__(self):
        self.sms_ir = SmsIr(
            api_key=settings.SMS_API_KEY, line_number=settings.SMS_LINE_NUMBER
        )

    def send_verification_code(self, user, token):
        """Send SMS verification code"""
        try:
            message = f"کد تایید شما: {token.token}"
            result = self.sms_ir.send_sms(
                message=message,
                mobile=user.mobile,
                template_id=settings.SMS_TEMPLATE_ID,
            )
            logger.info(f"SMS sent to {user.mobile}: {result}")
            return True
        except Exception as e:
            logger.error(f"SMS sending failed for {user.mobile}: {e}")
            return False

    def send_password_reset(self, user, token):
        """Send SMS password reset code"""
        try:
            message = f"کد بازیابی رمز عبور: {token.token}"
            result = self.sms_ir.send_sms(
                message=message,
                mobile=user.mobile,
                template_id=settings.SMS_TEMPLATE_ID,
            )
            logger.info(f"Password reset SMS sent to {user.mobile}")
            return True
        except Exception as e:
            logger.error(f"Password reset SMS failed for {user.mobile}: {e}")
            return False


# Email Service Implementation
class EmailService(NotificationService):
    def send_verification_code(self, user, token):
        """Send email activation link"""
        try:
            activation_url = f"{settings.SITE_URL}/users/activate/{token.email_token}/"

            subject = "فعال‌سازی حساب کاربری"
            html_message = f"""
            <div style="direction: rtl; text-align: right; font-family: Tahoma;">
                <h2>سلام {user.username or 'کاربر عزیز'}</h2>
                <p>برای فعال‌سازی حساب کاربری خود روی لینک زیر کلیک کنید:</p>
                <a href="{activation_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    فعال‌سازی حساب
                </a>
                <p>این لینک تا 5 دقیقه معتبر است.</p>
            </div>
            """

            send_mail(
                subject,
                f"برای فعال‌سازی حساب کاربری خود به آدرس {activation_url} مراجعه کنید",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Activation email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Activation email failed for {user.email}: {e}")
            return False

    def send_password_reset(self, user, token):
        """Send password reset email"""
        try:
            reset_url = f"{settings.SITE_URL}/users/reset-password/{token.email_token}/"

            subject = "بازیابی رمز عبور"
            html_message = f"""
            <div style="direction: rtl; text-align: right; font-family: Tahoma;">
                <h2>سلام {user.username or 'کاربر عزیز'}</h2>
                <p>برای بازیابی رمز عبور خود روی لینک زیر کلیک کنید:</p>
                <a href="{reset_url}" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    بازیابی رمز عبور
                </a>
                <p>این لینک تا 5 دقیقه معتبر است.</p>
            </div>
            """

            send_mail(
                subject,
                f"برای بازیابی رمز عبور خود به آدرس {reset_url} مراجعه کنید",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Password reset email failed for {user.email}: {e}")
            return False


# Factory class
class NotificationServiceFactory:
    @staticmethod
    def create_service(service_type):
        if service_type == "sms":
            return SMSService()
        elif service_type == "email":
            return EmailService()
        else:
            raise ValueError(f"Unknown service type: {service_type}")


# Main Authentication Service
class AuthenticationService:
    def __init__(self):
        self.sms_service = NotificationServiceFactory.create_service("sms")
        self.email_service = NotificationServiceFactory.create_service("email")

    def register_user(self, mobile=None, email=None, password=None):
        """Register user with SMS or Email verification"""

        try:
            # Create user
            user = User.objects.create_user(
                mobile=mobile, email=email, password=password, is_active=False
            )

            # Generate verification token
            token = VerificationToken.objects.create(
                user=user,
                token=VerificationToken.generate_sms_token(),
                token_type="registration",
            )

            # Send verification based on registration method
            if mobile:
                success = self.sms_service.send_verification_code(user, token)
                return user, token, "sms" if success else None
            elif email:
                success = self.email_service.send_verification_code(user, token)
                return user, token, "email" if success else None

            return user, token, None

        except Exception as e:
            logger.error(f"User registration failed: {e}")
            return None, None, None

    def verify_user(self, token_value, token_type="sms"):
        """Verify user with SMS code or Email link"""

        try:
            if token_type == "sms":
                token = VerificationToken.objects.get(
                    token=token_value, token_type="registration", is_used=False
                )
            else:  # email
                token = VerificationToken.objects.get(
                    email_token=token_value, token_type="registration", is_used=False
                )

            if token.is_valid():
                user = token.user
                user.is_active = True
                if token_type == "sms":
                    user.is_phone_verified = True
                else:
                    user.is_email_verified = True
                user.save()

                token.mark_as_used()
                logger.info(f"User {user} verified successfully via {token_type}")
                return user

            return None

        except VerificationToken.DoesNotExist:
            logger.error(f"Invalid verification token: {token_value}")
            return None

    def initiate_password_reset(self, mobile=None, email=None):
        """Initiate password reset process"""

        try:
            if mobile:
                user = User.objects.get(mobile=mobile)
                service = self.sms_service
            elif email:
                user = User.objects.get(email=email)
                service = self.email_service
            else:
                return None, None

            # Create reset token
            token = VerificationToken.objects.create(
                user=user,
                token=VerificationToken.generate_sms_token(),
                token_type="password_reset",
            )

            # Send reset notification
            success = service.send_password_reset(user, token)
            return user, token if success else None

        except User.DoesNotExist:
            logger.error(f"User not found for password reset: {mobile or email}")
            return None, None

    def reset_password(self, token_value, new_password, token_type="sms"):
        """Reset user password"""

        try:
            if token_type == "sms":
                token = VerificationToken.objects.get(
                    token=token_value, token_type="password_reset", is_used=False
                )
            else:  # email
                token = VerificationToken.objects.get(
                    email_token=token_value, token_type="password_reset", is_used=False
                )

            if token.is_valid():
                user = token.user
                user.set_password(new_password)
                user.save()

                token.mark_as_used()
                logger.info(f"Password reset successful for user {user}")
                return user

            return None

        except VerificationToken.DoesNotExist:
            logger.error(f"Invalid password reset token: {token_value}")
            return None
