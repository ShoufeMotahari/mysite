import logging
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

logger = logging.getLogger(__name__)


class Comment(models.Model):
    """یک مدل چندمنظوره برای مدیریت انواع نظرها"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="کاربر",
    )

    subject = models.CharField(
        max_length=200,
        verbose_name="موضوع",
        blank=True,
        null=True
    )

    content = models.TextField(
        max_length=1000,
        verbose_name="متن نظر"
    )

    is_approved = models.BooleanField(
        default=False,
        verbose_name="تایید شده"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    # Admin response field - THIS IS THE KEY ADDITION
    admin_response = models.TextField(
        max_length=1000,
        verbose_name="پاسخ مدیر",
        blank=True,
        null=True,
        help_text="پاسخ مدیر به این نظر"
    )

    # responded_by = models.ForeignKey(
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.SET_NULL,
    #     related_name="comment_responses",
    #     verbose_name="پاسخ داده شده توسط",
    #     blank=True,
    #     null=True
    # )
    #
    # responded_at = models.DateTimeField(
    #     verbose_name="تاریخ پاسخ",
    #     blank=True,
    #     null=True,
    #     default=None
    # )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    # Generic relation (اختیاری)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="نوع محتوا"
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="شناسه شی"
    )

    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["user", "is_approved"]),
            models.Index(fields=["is_approved", "is_active"]),
        ]

    def __str__(self):
        subject_part = f" - {self.subject[:50]}" if self.subject else ""
        return f"{self.user.username}{subject_part} - {self.content[:50]}..."

    def get_absolute_url(self):
        return f"/comments/{self.id}/"

    @property
    def status_display(self):
        """Return a user-friendly status"""
        if not self.is_active:
            return "غیرفعال"
        elif self.is_approved:
            return "تایید شده"
        else:
            return "در انتظار تایید"

    @property
    def has_admin_response(self):
        """Check if admin has responded"""
        return bool(self.admin_response)
