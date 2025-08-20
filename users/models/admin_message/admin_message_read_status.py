import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class AdminMessageReadStatus(models.Model):
    """Track which superuser admins have read which messages"""

    message = models.ForeignKey(
        "users.AdminMessage",   # 👈 string reference
        on_delete=models.CASCADE,
        verbose_name="پیام",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="کاربر"
    )

    read_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ خواندن")

    class Meta:
        unique_together = ["message", "user"]
        verbose_name = "وضعیت خواندن پیام"
        verbose_name_plural = "وضعیت‌های خواندن پیام"

    def __str__(self):
        return f"{self.user.get_display_name()} - {self.message.subject}"
