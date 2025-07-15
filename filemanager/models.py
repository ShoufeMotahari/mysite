from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
import os
from django.utils import timezone

User = get_user_model()


def get_photo_upload_path(instance, filename):
    """Generate upload path for photos"""
    return f'photos/{filename}'


def get_file_upload_path(instance, filename):
    """Generate upload path for files"""
    return f'files/{filename}'


class Photo(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    image = models.ImageField(upload_to=get_photo_upload_path, verbose_name="تصویر")
    alt_text = models.CharField(max_length=255, blank=True, verbose_name="متن جایگزین")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="آپلود شده توسط")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان آپلود")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان بروزرسانی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name="اندازه فایل")

    class Meta:
        verbose_name = "تصویر"
        verbose_name_plural = "تصاویر"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('filemanager:photo_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if self.image:
            self.file_size = self.image.size
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


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('doc', 'Word Document'),
        ('docx', 'Word Document'),
        ('txt', 'Text File'),
        ('xls', 'Excel'),
        ('xlsx', 'Excel'),
        ('zip', 'ZIP Archive'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200, verbose_name="نام فایل")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    file = models.FileField(upload_to=get_file_upload_path, verbose_name="فایل")
    file_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES, verbose_name="نوع فایل")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="آپلود شده توسط")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان آپلود")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان بروزرسانی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name="اندازه فایل")
    download_count = models.PositiveIntegerField(default=0, verbose_name="تعداد دانلود")

    class Meta:
        verbose_name = "سند"
        verbose_name_plural = "اسناد"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('filemanager:document_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            # Auto-detect file type from extension
            if not self.file_type:
                ext = os.path.splitext(self.file.name)[1].lower().lstrip('.')
                if ext in [choice[0] for choice in self.DOCUMENT_TYPES]:
                    self.file_type = ext
                else:
                    self.file_type = 'other'
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
        self.save(update_fields=['download_count'])


from django.db import models

# Create your models here.
