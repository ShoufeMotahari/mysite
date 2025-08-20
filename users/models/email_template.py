import logging

import django_jalali.db.models as jmodels
from ckeditor.fields import RichTextField
from django.db import models

logger = logging.getLogger(__name__)


class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام قالب")
    subject = models.CharField(max_length=200, verbose_name="موضوع")
    content = RichTextField(verbose_name="محتوا")  # CKEditor content
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "قالب ایمیل"
        verbose_name_plural = "قالب‌های ایمیل"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name
