import logging
import django_jalali.db.models as jmodels
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class AdminMessage(models.Model):
    """Model for messages sent by message admins to superuser admins"""

    STATUS_CHOICES = [
        ("unread", "خوانده نشده"),
        ("read", "خوانده شده"),
        ("archived", "آرشیو شده"),
    ]

    PRIORITY_CHOICES = [
        ("low", "کم"),
        ("normal", "عادی"),
        ("high", "بالا"),
        ("urgent", "فوری"),
    ]

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_admin_messages",
        verbose_name="فرستنده",
    )

    subject = models.CharField(max_length=200, verbose_name="موضوع", help_text="موضوع پیام")
    message = models.TextField(verbose_name="متن پیام", help_text="متن کامل پیام")

    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="normal", verbose_name="اولویت"
    )

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="unread", verbose_name="وضعیت"
    )

    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ خواندن")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="users.AdminMessageReadStatus",   # 👈 استفاده از string reference
        related_name="read_admin_messages",
        blank=True,
        verbose_name="خوانده شده توسط",
    )

    class Meta:
        verbose_name = "پیام ادمین"
        verbose_name_plural = "پیام‌های ادمین"
        ordering = ["-created_at", "-priority"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["priority", "status"]),
        ]

    def __str__(self):
        return f"{self.sender.get_display_name()} - {self.subject}"

    def mark_as_read(self, user):
        """Mark message as read by a specific user"""
        from users.models.admin_message.admin_message_read_status import AdminMessageReadStatus  # 👈 import local

        read_status, created = AdminMessageReadStatus.objects.get_or_create(
            message=self, user=user, defaults={"read_at": timezone.now()}
        )
        if not created and not read_status.read_at:
            read_status.read_at = timezone.now()
            read_status.save()

        if self.status == "unread":
            self.status = "read"
            self.read_at = timezone.now()
            self.save(update_fields=["status", "read_at"])
