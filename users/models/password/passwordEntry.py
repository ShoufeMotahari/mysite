import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class PasswordEntry(models.Model):
    """Password storage model"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_name = models.CharField(max_length=100, verbose_name="نام سرویس")
    username = models.CharField(max_length=100, verbose_name="نام کاربری")
    password = models.TextField(verbose_name="رمز عبور")  # Encrypted password
    notes = models.TextField(blank=True, null=True, verbose_name="یادداشت")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service_name} - {self.username}"
