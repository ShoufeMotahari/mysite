# core/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_jalali.db import models as jmodels


class BaseModel(models.Model):
    created_jalali = jmodels.jDateTimeField(
        auto_now_add=True, verbose_name=_("تاریخ ایجاد (شمسی)")
    )
    updated_jalali = jmodels.jDateTimeField(
        auto_now=True, verbose_name=_("تاریخ بروزرسانی (شمسی)")
    )

    class Meta:
        abstract = True
        ordering = ["-created_jalali"]


class EmailTemplate(BaseModel):
    """Email template model for the email manager"""
    name = models.CharField(
        max_length=200,
        verbose_name=_("نام قالب"),
        help_text=_("نام شناسایی برای قالب ایمیل")
    )
    subject = models.CharField(
        max_length=255,
        verbose_name=_("موضوع ایمیل"),
        help_text=_("موضوع پیش‌فرض برای ایمیل")
    )
    content = models.TextField(
        verbose_name=_("متن ایمیل"),
        help_text=_("محتوای ایمیل - می‌تواند شامل HTML باشد")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("فعال"),
        help_text=_("آیا این قالب فعال است؟")
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("توضیحات"),
        help_text=_("توضیحات اضافی درباره این قالب")
    )

    # Email type categorization
    EMAIL_TYPE_CHOICES = [
        ('notification', _('اعلان')),
        ('marketing', _('بازاریابی')),
        ('system', _('سیستمی')),
        ('welcome', _('خوش‌آمدگویی')),
        ('reminder', _('یادآوری')),
        ('other', _('سایر')),
    ]

    email_type = models.CharField(
        max_length=20,
        choices=EMAIL_TYPE_CHOICES,
        default='notification',
        verbose_name=_("نوع ایمیل"),
        help_text=_("دسته‌بندی نوع ایمیل")
    )

    class Meta:
        verbose_name = _("قالب ایمیل")
        verbose_name_plural = _("قالب‌های ایمیل")
        ordering = ['-created_jalali']

    def __str__(self):
        return f"{self.name} ({self.get_email_type_display()})"

    def clean(self):
        """Validate the email template"""
        from django.core.exceptions import ValidationError

        if not self.name.strip():
            raise ValidationError({'name': _('نام قالب نمی‌تواند خالی باشد')})

        if not self.subject.strip():
            raise ValidationError({'subject': _('موضوع ایمیل نمی‌تواند خالی باشد')})

        if not self.content.strip():
            raise ValidationError({'content': _('محتوای ایمیل نمی‌تواند خالی باشد')})

    def save(self, *args, **kwargs):
        """Override save to run clean validation"""
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_html_content(self):
        """Check if content contains HTML"""
        import re
        html_pattern = re.compile(r"<[^>]+>")
        return bool(html_pattern.search(self.content))

    def get_preview(self, max_length=100):
        """Get a preview of the content"""
        import re
        # Strip HTML tags for preview
        clean_content = re.sub(r'<[^>]+>', '', self.content)
        if len(clean_content) > max_length:
            return clean_content[:max_length] + "..."
        return clean_content