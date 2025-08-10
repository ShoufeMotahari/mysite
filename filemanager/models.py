import logging
import os
from io import BytesIO

import django_jalali.db.models as jmodels
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from PIL import Image as PILImage

logger = logging.getLogger("filemanager")

User = get_user_model()


def get_photo_upload_path(instance, filename):
    """Generate upload path for photos"""
    return f"photos/{filename}"


def get_file_upload_path(instance, filename):
    """Generate upload path for files"""
    return f"files/{filename}"


class ImageUpload(models.Model):
    """مدل آپلود تصویر سازگار با Arvan Cloud"""

    MINIFICATION_CHOICES = [
        ("none", "بدون فشرده‌سازی"),
        ("low", "فشرده‌سازی کم (90% کیفیت)"),
        ("medium", "فشرده‌سازی متوسط (75% کیفیت)"),
        ("high", "فشرده‌سازی بالا (60% کیفیت)"),
        ("maximum", "فشرده‌سازی حداکثر (45% کیفیت)"),
    ]

    SIZE_CHOICES = [
        ("original", "اندازه اصلی"),
        ("large", "بزرگ (1920x1080)"),
        ("medium", "متوسط (1280x720)"),
        ("small", "کوچک (800x600)"),
        ("thumbnail", "بندانگشتی (300x200)"),
    ]

    title = models.CharField(
        max_length=200, verbose_name="عنوان تصویر", help_text="عنوان توضیحی برای تصویر"
    )

    description = models.TextField(
        blank=True, null=True, verbose_name="توضیحات", help_text="توضیحات تکمیلی تصویر"
    )

    # تصویر اصلی - در Arvan Cloud ذخیره می‌شود
    original_image = models.ImageField(
        upload_to="images/original/%Y/%m/",
        verbose_name="تصویر اصلی",
        help_text="تصویر اصلی آپلود شده",
    )

    # تصویر پردازش شده - در Arvan Cloud ذخیره می‌شود
    processed_image = models.ImageField(
        upload_to="images/processed/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="تصویر پردازش شده",
        help_text="تصویر پس از اعمال تنظیمات",
    )

    minification_level = models.CharField(
        max_length=10,
        choices=MINIFICATION_CHOICES,
        default="none",
        verbose_name="سطح فشرده‌سازی",
        help_text="انتخاب سطح فشرده‌سازی تصویر",
    )

    resize_option = models.CharField(
        max_length=10,
        choices=SIZE_CHOICES,
        default="original",
        verbose_name="تغییر اندازه",
        help_text="تغییر اندازه تصویر",
    )

    maintain_aspect_ratio = models.BooleanField(
        default=True,
        verbose_name="حفظ نسبت ابعاد",
        help_text="حفظ نسبت طول و عرض هنگام تغییر اندازه",
    )

    convert_to_webp = models.BooleanField(
        default=False,
        verbose_name="تبدیل به WebP",
        help_text="تبدیل تصویر به فرمت WebP برای کاهش حجم",
    )

    # اطلاعات فایل
    original_size = models.PositiveIntegerField(
        default=0, verbose_name="حجم اصلی (بایت)", help_text="حجم فایل اصلی به بایت"
    )

    processed_size = models.PositiveIntegerField(
        default=0,
        verbose_name="حجم پردازش شده (بایت)",
        help_text="حجم فایل پس از پردازش",
    )

    compression_ratio = models.FloatField(
        default=0.0, verbose_name="نسبت فشرده‌سازی", help_text="درصد کاهش حجم"
    )

    # URL های Arvan Cloud
    original_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="لینک تصویر اصلی",
        help_text="لینک مستقیم تصویر اصلی در Arvan Cloud",
    )

    processed_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="لینک تصویر پردازش شده",
        help_text="لینک مستقیم تصویر پردازش شده در Arvan Cloud",
    )

    # Metadata
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="آپلود شده توسط",
        related_name="uploaded_images",
    )

    is_active = models.BooleanField(
        default=True, verbose_name="فعال", help_text="آیا این تصویر فعال است؟"
    )

    processing_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "در انتظار پردازش"),
            ("processing", "در حال پردازش"),
            ("completed", "تکمیل شده"),
            ("failed", "خطا در پردازش"),
        ],
        default="pending",
        verbose_name="وضعیت پردازش",
    )

    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    processed_at = jmodels.jDateTimeField(
        null=True, blank=True, verbose_name="تاریخ پردازش"
    )

    class Meta:
        verbose_name = "آپلود تصویر"
        verbose_name_plural = "آپلود تصاویر"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["uploaded_by"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["processing_status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save برای پردازش تصویر"""
        # تنظیم حجم فایل اصلی
        if self.original_image and hasattr(self.original_image, "size"):
            self.original_size = self.original_image.size

        # تنظیم URL های Arvan Cloud
        if self.original_image:
            self.original_url = self.original_image.url

        # ذخیره اولیه
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # پردازش تصویر برای رکوردهای جدید یا تغییر تنظیمات
        if is_new or self.processing_status == "pending":
            self.process_image_async()

    def process_image_async(self):
        """پردازش غیرهمزمان تصویر"""
        try:
            self.processing_status = "processing"
            self.save(update_fields=["processing_status"])

            # Check if any processing is needed
            needs_processing = (
                self.minification_level != "none"
                or self.resize_option != "original"
                or self.convert_to_webp
            )

            if needs_processing:
                success = self.process_image()

                if success:
                    self.processing_status = "completed"
                    self.processed_at = timezone.now()
                    logger.info(f"تصویر {self.title} با موفقیت پردازش شد")
                else:
                    self.processing_status = "failed"
                    logger.error(f"خطا در پردازش تصویر {self.title}")
            else:
                # Even if no processing is needed, mark as completed
                self.processing_status = "completed"
                self.processed_at = timezone.now()
                # Copy original to processed for consistency
                if not self.processed_image:
                    self.processed_image = self.original_image
                    self.processed_size = self.original_size
                    self.processed_url = self.original_url

            self.save(
                update_fields=[
                    "processing_status",
                    "processed_at",
                    "processed_image",
                    "processed_size",
                    "processed_url",
                ]
            )

        except Exception as e:
            self.processing_status = "failed"
            self.save(update_fields=["processing_status"])
            logger.error(f"خطا در پردازش تصویر {self.title}: {str(e)}", exc_info=True)

    def reprocess_image(self):
        """Force reprocess the image"""
        self.processing_status = "pending"
        self.save(update_fields=["processing_status"])
        self.process_image_async()
        return self.processing_status == "completed"

    def process_image(self):
        """پردازش تصویر با تنظیمات انتخاب شده"""
        if not self.original_image:
            return False

        try:
            # دانلود تصویر از Arvan Cloud
            from django.core.files.storage import default_storage

            # باز کردن تصویر از storage
            with default_storage.open(self.original_image.name) as image_file:
                with PILImage.open(image_file) as img:
                    # تبدیل به RGB در صورت نیاز
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")

                    # تغییر اندازه
                    img = self._resize_image(img)

                    # تعیین فرمت خروجی
                    output_format = (
                        "WEBP" if self.convert_to_webp else img.format or "JPEG"
                    )

                    # تنظیم کیفیت
                    quality = self._get_quality_setting()

                    # ذخیره تصویر پردازش شده
                    output = BytesIO()

                    if output_format == "WEBP":
                        img.save(output, format="WEBP", quality=quality, optimize=True)
                        file_extension = ".webp"
                    elif output_format in ["JPEG", "JPG"]:
                        img.save(output, format="JPEG", quality=quality, optimize=True)
                        file_extension = ".jpg"
                    else:
                        img.save(
                            output, format=output_format, quality=quality, optimize=True
                        )
                        file_extension = ".png"

                    output.seek(0)

                    # تولید نام فایل پردازش شده
                    original_name = os.path.splitext(
                        os.path.basename(self.original_image.name)
                    )[0]
                    processed_filename = f"{original_name}_processed{file_extension}"

                    # ذخیره در Arvan Cloud
                    self.processed_image.save(
                        processed_filename, ContentFile(output.getvalue()), save=False
                    )

                    # تنظیم URL و اندازه
                    self.processed_url = self.processed_image.url
                    self.processed_size = len(output.getvalue())

                    # محاسبه نسبت فشرده‌سازی
                    if self.original_size > 0:
                        self.compression_ratio = (
                            (self.original_size - self.processed_size)
                            / self.original_size
                        ) * 100

                    # ذخیره بدون فراخوانی مجدد save
                    super().save(
                        update_fields=[
                            "processed_image",
                            "processed_url",
                            "processed_size",
                            "compression_ratio",
                        ]
                    )

                    logger.info(
                        f"تصویر {self.title} پردازش شد - کاهش حجم: {self.compression_ratio:.1f}%"
                    )
                    return True

        except Exception as e:
            logger.error(f"خطا در پردازش تصویر {self.id}: {str(e)}")
            return False

    def _resize_image(self, img):
        """تغییر اندازه تصویر بر اساس تنظیمات"""
        if self.resize_option == "original":
            return img

        size_mappings = getattr(settings, "IMAGE_UPLOAD_SETTINGS", {}).get(
            "RESIZE_DIMENSIONS",
            {
                "large": (1920, 1080),
                "medium": (1280, 720),
                "small": (800, 600),
                "thumbnail": (300, 200),
            },
        )

        target_size = size_mappings.get(self.resize_option)
        if not target_size:
            return img

        if self.maintain_aspect_ratio:
            img.thumbnail(target_size, PILImage.Resampling.LANCZOS)
        else:
            img = img.resize(target_size, PILImage.Resampling.LANCZOS)

        return img

    def _get_quality_setting(self):
        """تنظیم کیفیت بر اساس سطح فشرده‌سازی"""
        quality_mappings = getattr(settings, "IMAGE_UPLOAD_SETTINGS", {}).get(
            "MINIFICATION_LEVELS",
            {
                "none": 95,
                "low": 90,
                "medium": 75,
                "high": 60,
                "maximum": 45,
            },
        )
        return quality_mappings.get(self.minification_level, 95)

    def get_file_size_display(self, size_bytes=None):
        """تبدیل بایت به فرمت قابل خواندن"""
        if size_bytes is None:
            size_bytes = self.original_size

        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def get_original_size_display(self):
        """نمایش حجم فایل اصلی"""
        return self.get_file_size_display(self.original_size)

    def get_processed_size_display(self):
        """نمایش حجم فایل پردازش شده"""
        return self.get_file_size_display(self.processed_size)

    def get_compression_display(self):
        """نمایش نسبت فشرده‌سازی"""
        if self.compression_ratio > 0:
            return f"{self.compression_ratio:.1f}% کاهش"
        return "بدون فشرده‌سازی"

    def get_active_image(self):
        """دریافت تصویر فعال (پردازش شده یا اصلی)"""
        if self.processed_image:
            return self.processed_image
        return self.original_image

    def get_active_url(self):
        """دریافت URL فعال"""
        if self.processed_url:
            return self.processed_url
        return self.original_url or (
            self.original_image.url if self.original_image else None
        )

    @classmethod
    def get_total_storage_used(cls):
        """محاسبه کل فضای استفاده شده"""
        from django.db.models import Sum

        result = cls.objects.aggregate(
            total_original=Sum("original_size"), total_processed=Sum("processed_size")
        )
        return {
            "original": result["total_original"] or 0,
            "processed": result["total_processed"] or 0,
            "total": (result["total_original"] or 0) + (result["total_processed"] or 0),
        }

    @classmethod
    def get_compression_stats(cls):
        """آمار فشرده‌سازی"""
        from django.db.models import Avg, Sum

        return cls.objects.filter(compression_ratio__gt=0).aggregate(
            avg_compression=Avg("compression_ratio"),
            total_saved=Sum("original_size") - Sum("processed_size"),
        )


class ImageGallery(models.Model):
    """گالری تصاویر"""

    name = models.CharField(
        max_length=200, verbose_name="نام گالری", help_text="نام گالری تصاویر"
    )

    description = models.TextField(blank=True, null=True, verbose_name="توضیحات گالری")

    images = models.ManyToManyField(
        ImageUpload, verbose_name="تصاویر", blank=True, help_text="تصاویر این گالری"
    )

    cover_image = models.ForeignKey(
        ImageUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gallery_covers",
        verbose_name="تصویر کاور",
        help_text="تصویر کاور گالری",
    )

    is_public = models.BooleanField(
        default=True, verbose_name="عمومی", help_text="آیا این گالری عمومی است؟"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="ایجاد شده توسط",
    )

    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "گالری تصاویر"
        verbose_name_plural = "گالری‌های تصاویر"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_images_count(self):
        """تعداد تصاویر گالری"""
        return self.images.count()

    def get_total_size(self):
        """حجم کل تصاویر گالری"""
        total_size = 0
        for image in self.images.all():
            total_size += image.processed_size or image.original_size
        return total_size

    def get_total_size_display(self):
        """نمایش حجم کل"""
        return ImageUpload().get_file_size_display(self.get_total_size())


class Document(models.Model):
    DOCUMENT_TYPES = [
        ("pdf", "PDF"),
        ("doc", "Word Document"),
        ("docx", "Word Document"),
        ("txt", "Text File"),
        ("xls", "Excel"),
        ("xlsx", "Excel"),
        ("zip", "ZIP Archive"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=200, verbose_name="نام فایل")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    file = models.FileField(upload_to=get_file_upload_path, verbose_name="فایل")
    file_type = models.CharField(
        max_length=10, choices=DOCUMENT_TYPES, verbose_name="نوع فایل"
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="آپلود شده توسط"
    )
    uploaded_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="زمان آپلود")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="زمان بروزرسانی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    file_size = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="اندازه فایل"
    )
    download_count = models.PositiveIntegerField(default=0, verbose_name="تعداد دانلود")

    class Meta:
        verbose_name = "سند"
        verbose_name_plural = "اسناد"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("filemanager:document_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            # Auto-detect file type from extension
            if not self.file_type:
                ext = os.path.splitext(self.file.name)[1].lower().lstrip(".")
                if ext in [choice[0] for choice in self.DOCUMENT_TYPES]:
                    self.file_type = ext
                else:
                    self.file_type = "other"
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Return human-readable file size"""
        if self.file_size:
            if self.file_size < 1024:
                return f"{self.file_size} B"
            elif self.file_size < 1024 * 1024:
                return f"{self.file_size / 1024:.1f} KB"
            else:
                return f"{self.file_size / (1024 * 1024):.1f} MB"
        return "نامشخص"

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1
        self.save(update_fields=["download_count"])


@receiver(post_delete, sender="filemanager.ImageUpload")
def delete_image_files(sender, instance, **kwargs):
    """Delete files when ImageUpload instance is deleted"""
    try:
        if instance.original_image:
            instance.original_image.delete(save=False)
    except Exception as e:
        logger.error(f"Error deleting original image for {instance.title}: {str(e)}")

    try:
        if instance.processed_image:
            instance.processed_image.delete(save=False)
    except Exception as e:
        logger.error(f"Error deleting processed image for {instance.title}: {str(e)}")


@receiver(post_delete, sender="filemanager.Document")
def delete_document_file(sender, instance, **kwargs):
    """Delete file when Document instance is deleted"""
    try:
        if instance.file:
            instance.file.delete(save=False)
    except Exception as e:
        logger.error(f"Error deleting file for {instance.name}: {str(e)}")
