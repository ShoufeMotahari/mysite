import logging
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class RegisterToken(models.Model):
    """Legacy model - kept for backward compatibility"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() - self.created < timezone.timedelta(minutes=5)

    def __str__(self):
        return f"{self.user} - {self.code}"

    class Meta:
        verbose_name = "کد ثبت نام قدیمی"
        verbose_name_plural = "کدهای ثبت نام قدیمی"
