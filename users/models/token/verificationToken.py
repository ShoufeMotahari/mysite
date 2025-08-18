import logging
import random
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class VerificationToken(models.Model):
    TOKEN_TYPES = [
        ("registration", "Registration"),
        ("login", "Login"),
        ("password_reset", "Password Reset"),
        ("email_activation", "Email Activation"),
        ("phone_verification", "Phone Verification"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)  # For SMS codes
    email_token = models.UUIDField(default=uuid.uuid4, unique=True)  # For email links
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return (
                timezone.now() - self.created_at < timezone.timedelta(minutes=5)
                and not self.is_used
        )

    def is_expired(self):
        """Check if token has expired (15 minutes)"""
        import datetime

        from django.utils import timezone

        expiry_time = self.created_at + datetime.timedelta(minutes=15)
        return timezone.now() > expiry_time

    def mark_as_used(self):
        self.is_used = True
        self.save()
        logger.info(
            f"Verification token marked as used - User: {self.user}, Type: {self.token_type}"
        )

    @classmethod
    def generate_sms_token(cls):
        """Generate a 6-digit SMS verification code"""
        return str(random.randint(100000, 999999))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            logger.info(
                f"Creating verification token - User: {self.user}, Type: {self.token_type}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.token_type} - {self.token}"

    class Meta:
        verbose_name = "کد تایید"
        verbose_name_plural = "کدهای تایید"
        ordering = ["-created_at"]

try:
    from django_jalali.admin.filters import JDateFieldListFilter
except ImportError:
    from django.contrib.admin import DateFieldListFilter as JDateFieldListFilter