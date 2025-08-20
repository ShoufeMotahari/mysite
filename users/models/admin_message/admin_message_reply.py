import logging
import django_jalali.db.models as jmodels
from django.conf import settings
from django.db import models

from users.models.admin_message.admin_message import AdminMessage

logger = logging.getLogger(__name__)

class AdminMessageReply(models.Model):
    """Model for replies to admin messages"""

    original_message = models.ForeignKey(
        AdminMessage,
        on_delete=models.CASCADE,
        related_name="replies",
        verbose_name="پیام اصلی",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_message_replies",
        verbose_name="فرستنده پاسخ",
    )

    reply_text = models.TextField(verbose_name="متن پاسخ")

    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "پاسخ پیام ادمین"
        verbose_name_plural = "پاسخ‌های پیام ادمین"
        ordering = ["created_at"]

    def __str__(self):
        return f"پاسخ به: {self.original_message.subject}"