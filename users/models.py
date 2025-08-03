# users/models.py - Enhanced with User Types
from django.db import models
from django_jalali.db.models import jDateTimeField
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import random
from django.utils import timezone
from django.conf import settings
import uuid
import logging
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

from django.db import models
from django.conf import settings
from django.utils import timezone
import django_jalali.db.models as jmodels


class UserType(models.Model):
    """Model for different user types/roles"""

    # Predefined user type choices
    ADMIN = 'admin'
    MANAGER = 'manager'
    EDITOR = 'editor'
    AUTHOR = 'author'
    SUBSCRIBER = 'subscriber'
    CUSTOMER = 'customer'
    GUEST = 'guest'

    TYPE_CHOICES = [
        (ADMIN, 'مدیر سیستم'),
        (MANAGER, 'مدیر'),
        (EDITOR, 'ویرایشگر'),
        (AUTHOR, 'نویسنده'),
        (SUBSCRIBER, 'مشترک'),
        (CUSTOMER, 'مشتری'),
        (GUEST, 'مهمان'),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name='نام نوع کاربری')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='اسلاگ')
    description = models.TextField(blank=True, null=True, verbose_name='توضیحات')

    # Permissions for this user type
    can_create_content = models.BooleanField(default=False, verbose_name='امکان ایجاد محتوا')
    can_edit_content = models.BooleanField(default=False, verbose_name='امکان ویرایش محتوا')
    can_delete_content = models.BooleanField(default=False, verbose_name='امکان حذف محتوا')
    can_manage_users = models.BooleanField(default=False, verbose_name='امکان مدیریت کاربران')
    can_view_analytics = models.BooleanField(default=False, verbose_name='امکان مشاهده آمار')
    can_access_admin = models.BooleanField(default=False, verbose_name='دسترسی به پنل ادمین')

    # Content limits
    max_posts_per_day = models.PositiveIntegerField(null=True, blank=True, verbose_name='حداکثر پست روزانه')
    max_comments_per_day = models.PositiveIntegerField(null=True, blank=True, verbose_name='حداکثر نظر روزانه')
    max_file_upload_size_mb = models.PositiveIntegerField(default=10, verbose_name='حداکثر اندازه فایل (مگابایت)')

    # Status and metadata
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_default = models.BooleanField(default=False, verbose_name='پیش‌فرض')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'نوع کاربری'
        verbose_name_plural = 'انواع کاربری'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        # Ensure only one default user type
        if self.is_default:
            UserType.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

    @classmethod
    def get_default_type(cls):
        """Get the default user type"""
        try:
            return cls.objects.get(is_default=True)
        except cls.DoesNotExist:
            # If no default is set, return the first active type or create one
            default_type = cls.objects.filter(is_active=True).first()
            if not default_type:
                # Create a basic subscriber type as default
                default_type = cls.objects.create(
                    name='مشترک',
                    slug='subscriber',
                    description='کاربر عادی سیستم',
                    is_default=True,
                    can_create_content=False,
                    can_edit_content=False,
                    can_delete_content=False,
                    max_comments_per_day=10
                )
            return default_type

    def get_permissions_display(self):
        """Get a readable display of permissions"""
        permissions = []
        if self.can_create_content:
            permissions.append('ایجاد محتوا')
        if self.can_edit_content:
            permissions.append('ویرایش محتوا')
        if self.can_delete_content:
            permissions.append('حذف محتوا')
        if self.can_manage_users:
            permissions.append('مدیریت کاربران')
        if self.can_view_analytics:
            permissions.append('مشاهده آمار')
        if self.can_access_admin:
            permissions.append('دسترسی ادمین')

        return ', '.join(permissions) if permissions else 'بدون مجوز خاص'


class User(AbstractUser):
    """Enhanced User model with user types"""

    mobile = models.CharField(max_length=11, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=254, unique=False, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True, max_length=255)

    # User type relationship
    user_type = models.ForeignKey(
        UserType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='نوع کاربری',
        help_text='نوع کاربری تعیین کننده سطح دسترسی کاربر است'
    )

    # Additional user information
    bio = models.TextField(blank=True, null=True, verbose_name='بیوگرافی')
    birth_date = models.DateField(blank=True, null=True, verbose_name='تاریخ تولد')

    # Status fields
    created_at = jmodels.jDateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_phone_verified = models.BooleanField(default=False, verbose_name='تلفن تایید شده')
    is_email_verified = models.BooleanField(default=False, verbose_name='ایمیل تایید شده')
    is_staff = models.BooleanField(default=False, verbose_name='دسترسی ادمین')

    # Activity tracking
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name='آخرین فعالیت')
    posts_count = models.PositiveIntegerField(default=0, verbose_name='تعداد پست‌ها')
    comments_count = models.PositiveIntegerField(default=0, verbose_name='تعداد نظرات')

    def _generate_unique_slug(self, base_slug):
        """Generate a unique slug by appending numbers if needed"""
        slug = base_slug
        counter = 1
        while User.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        """Override save to generate slug automatically and set default user type"""

        # Set default user type if not set
        if not self.user_type_id:
            self.user_type = UserType.get_default_type()

        # Generate slug if not set
        if not self.slug:
            if self.username:
                base_slug = slugify(self.username)
            elif self.email:
                base_slug = slugify(self.email.split('@')[0])
            elif self.mobile:
                base_slug = f"user-{self.mobile}"
            else:
                base_slug = str(uuid.uuid4())[:8]  # fallback

            self.slug = self._generate_unique_slug(base_slug)

        # Auto-set staff status based on user type
        if self.user_type and self.user_type.can_access_admin:
            self.is_staff = True

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.mobile or self.email or f"User {self.id}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('user_profile', kwargs={'slug': self.slug})

    def get_display_name(self):
        """Get the best available display name for the user"""
        if self.get_full_name().strip():
            return self.get_full_name()
        elif self.username:
            return self.username
        elif self.email:
            return self.email
        elif self.mobile:
            return self.mobile
        else:
            return f"کاربر {self.id}"

    def has_permission(self, permission):
        """Check if user has specific permission based on user type"""
        if not self.user_type:
            return False

        permission_map = {
            'create_content': self.user_type.can_create_content,
            'edit_content': self.user_type.can_edit_content,
            'delete_content': self.user_type.can_delete_content,
            'manage_users': self.user_type.can_manage_users,
            'view_analytics': self.user_type.can_view_analytics,
            'access_admin': self.user_type.can_access_admin,
        }

        return permission_map.get(permission, False)

    def get_daily_limit(self, limit_type):
        """Get daily limit for specific content type"""
        if not self.user_type:
            return 0

        if limit_type == 'posts':
            return self.user_type.max_posts_per_day
        elif limit_type == 'comments':
            return self.user_type.max_comments_per_day

        return 0

    def can_upload_file(self, file_size_mb):
        """Check if user can upload file based on size limit"""
        if not self.user_type:
            return False

        return file_size_mb <= self.user_type.max_file_upload_size_mb

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    def get_user_type_display(self):
        """Get user type display name"""
        return self.user_type.name if self.user_type else 'نامشخص'


# Keep existing models with minor updates
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_jalali = jmodels.jDateTimeField(auto_now_add=True)
    updated_jalali = jmodels.jDateTimeField(auto_now=True)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user}"

    class Meta:
        verbose_name = 'پروفایل'
        verbose_name_plural = 'پروفایل‌ها'


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
        verbose_name = 'کد ثبت نام قدیمی'
        verbose_name_plural = 'کدهای ثبت نام قدیمی'


class VerificationToken(models.Model):
    TOKEN_TYPES = [
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
        ('email_activation', 'Email Activation'),
        ('phone_verification', 'Phone Verification'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)  # For SMS codes
    email_token = models.UUIDField(default=uuid.uuid4, unique=True)  # For email links
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return (
                timezone.now() - self.created_at < timezone.timedelta(minutes=5)
                and not self.is_used
        )
    def is_expired(self):
        """Check if token has expired (15 minutes)"""
        from django.utils import timezone
        import datetime
        expiry_time = self.created_at + datetime.timedelta(minutes=15)
        return timezone.now() > expiry_time

    def mark_as_used(self):
        self.is_used = True
        self.save()
        logger.info(f"Verification token marked as used - User: {self.user}, Type: {self.token_type}")

    @classmethod
    def generate_sms_token(cls):
        """Generate a 6-digit SMS verification code"""
        return str(random.randint(100000, 999999))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            logger.info(f"Creating verification token - User: {self.user}, Type: {self.token_type}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.token_type} - {self.token}"

    class Meta:
        verbose_name = 'کد تایید'
        verbose_name_plural = 'کدهای تایید'
        ordering = ['-created_at']


class Comment(models.Model):
    """Model for user comments"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='کاربر'
    )
    content = models.TextField(verbose_name='متن نظر')
    is_approved = models.BooleanField(default=False, verbose_name='تایید شده')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    # Generic foreign key for commenting on different models
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['user', 'is_approved']),
        ]

    def __str__(self):
        return f'{self.user} - {self.content[:50]}...'

    def get_absolute_url(self):
        """Get URL for this comment"""
        return f'/comments/{self.id}/'


class PasswordEntry(models.Model):
    """Password storage model"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_name = models.CharField(max_length=100, verbose_name='نام سرویس')
    username = models.CharField(max_length=100, verbose_name='نام کاربری')
    password = models.TextField(verbose_name='رمز عبور')  # Encrypted password
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service_name} - {self.username}"

    class Meta:
        unique_together = ['user', 'service_name', 'username']
        verbose_name = 'ورودی رمز عبور'
        verbose_name_plural = 'ورودی‌های رمز عبور'
        indexes = [
            models.Index(fields=['user', 'service_name']),
        ]

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('gAAAA'):
            self.encrypt_password(self.password)
        super().save(*args, **kwargs)

    def encrypt_password(self, password):
        """Encrypt password before storing"""
        try:
            f = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str)
                       else settings.ENCRYPTION_KEY)
            encrypted_password = f.encrypt(password.encode())
            self.password = encrypted_password.decode()
        except Exception as e:
            logger.error(f"Password encryption failed - Service: {self.service_name}, Error: {str(e)}")
            raise ValidationError("Error encrypting password")

    def decrypt_password(self):
        """Decrypt password for display"""
        try:
            f = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str)
                       else settings.ENCRYPTION_KEY)
            decrypted_password = f.decrypt(self.password.encode())
            return decrypted_password.decode()
        except Exception as e:
            logger.error(f"Password decryption failed - Service: {self.service_name}, Error: {str(e)}")
            raise ValidationError("Error decrypting password")


class AdminMessage(models.Model):
    """Model for messages sent by message admins to superuser admins"""

    STATUS_CHOICES = [
        ('unread', 'خوانده نشده'),
        ('read', 'خوانده شده'),
        ('archived', 'آرشیو شده'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'کم'),
        ('normal', 'عادی'),
        ('high', 'بالا'),
        ('urgent', 'فوری'),
    ]

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_admin_messages',
        verbose_name='فرستنده'
    )

    subject = models.CharField(
        max_length=200,
        verbose_name='موضوع',
        help_text='موضوع پیام'
    )

    message = models.TextField(
        verbose_name='متن پیام',
        help_text='متن کامل پیام'
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name='اولویت'
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='unread',
        verbose_name='وضعیت'
    )

    # Timestamps
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ خواندن')
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    # Tracking fields
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='AdminMessageReadStatus',
        related_name='read_admin_messages',
        blank=True,
        verbose_name='خوانده شده توسط'
    )

    class Meta:
        verbose_name = 'پیام ادمین'
        verbose_name_plural = 'پیام‌های ادمین'
        ordering = ['-created_at', '-priority']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f'{self.sender.get_display_name()} - {self.subject}'

    def mark_as_read(self, user):
        """Mark message as read by a specific user"""
        read_status, created = AdminMessageReadStatus.objects.get_or_create(
            message=self,
            user=user,
            defaults={'read_at': timezone.now()}
        )
        if not created and not read_status.read_at:
            read_status.read_at = timezone.now()
            read_status.save()

        # Update overall status if this is the first read
        if self.status == 'unread':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])

    def get_priority_color(self):
        """Get CSS color class for priority"""
        colors = {
            'low': 'text-muted',
            'normal': 'text-info',
            'high': 'text-warning',
            'urgent': 'text-danger'
        }
        return colors.get(self.priority, 'text-info')

    def get_priority_icon(self):
        """Get icon for priority"""
        icons = {
            'low': '⬇️',
            'normal': '➡️',
            'high': '⬆️',
            'urgent': '🚨'
        }
        return icons.get(self.priority, '➡️')

    @classmethod
    def get_unread_count(cls):
        """Get count of unread messages"""
        return cls.objects.filter(status='unread').count()

    @classmethod
    def get_recent_messages(cls, limit=5):
        """Get recent messages for notification"""
        return cls.objects.filter(status='unread').order_by('-created_at')[:limit]


class AdminMessageReadStatus(models.Model):
    """Track which superuser admins have read which messages"""

    message = models.ForeignKey(
        AdminMessage,
        on_delete=models.CASCADE,
        verbose_name='پیام'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='کاربر'
    )

    read_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ خواندن'
    )

    class Meta:
        unique_together = ['message', 'user']
        verbose_name = 'وضعیت خواندن پیام'
        verbose_name_plural = 'وضعیت‌های خواندن پیام'

    def __str__(self):
        return f'{self.user.get_display_name()} - {self.message.subject}'


class AdminMessageReply(models.Model):
    """Model for replies to admin messages"""

    original_message = models.ForeignKey(
        AdminMessage,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='پیام اصلی'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_message_replies',
        verbose_name='فرستنده پاسخ'
    )

    reply_text = models.TextField(
        verbose_name='متن پاسخ'
    )

    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    class Meta:
        verbose_name = 'پاسخ پیام ادمین'
        verbose_name_plural = 'پاسخ‌های پیام ادمین'
        ordering = ['created_at']

    def __str__(self):
        return f'پاسخ به: {self.original_message.subject}'


# users/models.py - اضافه کردن این مدل‌ها به فایل موجود

from PIL import Image as PILImage
import os
from django.core.files.base import ContentFile
from io import BytesIO
from django.conf import settings
import logging
# Add these imports at the top of your models.py
from django.db import models
from django.utils import timezone
from django.conf import settings


class ImageUpload(models.Model):
    """مدل آپلود تصویر سازگار با Arvan Cloud"""

    MINIFICATION_CHOICES = [
        ('none', 'بدون فشرده‌سازی'),
        ('low', 'فشرده‌سازی کم (90% کیفیت)'),
        ('medium', 'فشرده‌سازی متوسط (75% کیفیت)'),
        ('high', 'فشرده‌سازی بالا (60% کیفیت)'),
        ('maximum', 'فشرده‌سازی حداکثر (45% کیفیت)'),
    ]

    SIZE_CHOICES = [
        ('original', 'اندازه اصلی'),
        ('large', 'بزرگ (1920x1080)'),
        ('medium', 'متوسط (1280x720)'),
        ('small', 'کوچک (800x600)'),
        ('thumbnail', 'بندانگشتی (300x200)'),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name='عنوان تصویر',
        help_text='عنوان توضیحی برای تصویر'
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='توضیحات',
        help_text='توضیحات تکمیلی تصویر'
    )

    # تصویر اصلی - در Arvan Cloud ذخیره می‌شود
    original_image = models.ImageField(
        upload_to='images/original/%Y/%m/',
        verbose_name='تصویر اصلی',
        help_text='تصویر اصلی آپلود شده'
    )

    # تصویر پردازش شده - در Arvan Cloud ذخیره می‌شود
    processed_image = models.ImageField(
        upload_to='images/processed/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='تصویر پردازش شده',
        help_text='تصویر پس از اعمال تنظیمات'
    )

    minification_level = models.CharField(
        max_length=10,
        choices=MINIFICATION_CHOICES,
        default='none',
        verbose_name='سطح فشرده‌سازی',
        help_text='انتخاب سطح فشرده‌سازی تصویر'
    )

    resize_option = models.CharField(
        max_length=10,
        choices=SIZE_CHOICES,
        default='original',
        verbose_name='تغییر اندازه',
        help_text='تغییر اندازه تصویر'
    )

    maintain_aspect_ratio = models.BooleanField(
        default=True,
        verbose_name='حفظ نسبت ابعاد',
        help_text='حفظ نسبت طول و عرض هنگام تغییر اندازه'
    )

    convert_to_webp = models.BooleanField(
        default=False,
        verbose_name='تبدیل به WebP',
        help_text='تبدیل تصویر به فرمت WebP برای کاهش حجم'
    )

    # اطلاعات فایل
    original_size = models.PositiveIntegerField(
        default=0,
        verbose_name='حجم اصلی (بایت)',
        help_text='حجم فایل اصلی به بایت'
    )

    processed_size = models.PositiveIntegerField(
        default=0,
        verbose_name='حجم پردازش شده (بایت)',
        help_text='حجم فایل پس از پردازش'
    )

    compression_ratio = models.FloatField(
        default=0.0,
        verbose_name='نسبت فشرده‌سازی',
        help_text='درصد کاهش حجم'
    )

    # URL های Arvan Cloud
    original_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='لینک تصویر اصلی',
        help_text='لینک مستقیم تصویر اصلی در Arvan Cloud'
    )

    processed_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='لینک تصویر پردازش شده',
        help_text='لینک مستقیم تصویر پردازش شده در Arvan Cloud'
    )

    # Metadata
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='آپلود شده توسط',
        related_name='uploaded_images'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال',
        help_text='آیا این تصویر فعال است؟'
    )

    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'در انتظار پردازش'),
            ('processing', 'در حال پردازش'),
            ('completed', 'تکمیل شده'),
            ('failed', 'خطا در پردازش'),
        ],
        default='pending',
        verbose_name='وضعیت پردازش'
    )

    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='تاریخ آپلود')
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    processed_at = jmodels.jDateTimeField(null=True, blank=True, verbose_name='تاریخ پردازش')

    class Meta:
        verbose_name = 'آپلود تصویر'
        verbose_name_plural = 'آپلود تصاویر'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['is_active']),
            models.Index(fields=['processing_status']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save برای پردازش تصویر"""

        # تنظیم حجم فایل اصلی
        if self.original_image and hasattr(self.original_image, 'size'):
            self.original_size = self.original_image.size

        # تنظیم URL های Arvan Cloud
        if self.original_image:
            self.original_url = self.original_image.url

        # ذخیره اولیه
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # پردازش تصویر برای رکوردهای جدید یا تغییر تنظیمات
        if is_new or self.processing_status == 'pending':
            self.process_image_async()

    # Fix for the process_image_async method in your model

    def process_image_async(self):
        """پردازش غیرهمزمان تصویر"""
        try:
            self.processing_status = 'processing'
            self.save(update_fields=['processing_status'])

            # Check if any processing is needed
            needs_processing = (
                    self.minification_level != 'none' or
                    self.resize_option != 'original' or
                    self.convert_to_webp
            )

            if needs_processing:
                success = self.process_image()

                if success:
                    self.processing_status = 'completed'
                    self.processed_at = timezone.now()
                    logger.info(f"تصویر {self.title} با موفقیت پردازش شد")
                else:
                    self.processing_status = 'failed'
                    logger.error(f"خطا در پردازش تصویر {self.title}")
            else:
                # Even if no processing is needed, mark as completed
                self.processing_status = 'completed'
                self.processed_at = timezone.now()
                # Copy original to processed for consistency
                if not self.processed_image:
                    self.processed_image = self.original_image
                    self.processed_size = self.original_size
                    self.processed_url = self.original_url

            self.save(update_fields=['processing_status', 'processed_at', 'processed_image', 'processed_size',
                                     'processed_url'])

        except Exception as e:
            self.processing_status = 'failed'
            self.save(update_fields=['processing_status'])
            logger.error(f"خطا در پردازش تصویر {self.title}: {str(e)}", exc_info=True)

    # Also add this method to manually trigger processing
    def reprocess_image(self):
        """Force reprocess the image"""
        self.processing_status = 'pending'
        self.save(update_fields=['processing_status'])
        self.process_image_async()
        return self.processing_status == 'completed'

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
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')

                    # تغییر اندازه
                    img = self._resize_image(img)

                    # تعیین فرمت خروجی
                    output_format = 'WEBP' if self.convert_to_webp else img.format or 'JPEG'

                    # تنظیم کیفیت
                    quality = self._get_quality_setting()

                    # ذخیره تصویر پردازش شده
                    output = BytesIO()

                    if output_format == 'WEBP':
                        img.save(output, format='WEBP', quality=quality, optimize=True)
                        file_extension = '.webp'
                    elif output_format in ['JPEG', 'JPG']:
                        img.save(output, format='JPEG', quality=quality, optimize=True)
                        file_extension = '.jpg'
                    else:
                        img.save(output, format=output_format, quality=quality, optimize=True)
                        file_extension = '.png'

                    output.seek(0)

                    # تولید نام فایل پردازش شده
                    original_name = os.path.splitext(os.path.basename(self.original_image.name))[0]
                    processed_filename = f"{original_name}_processed{file_extension}"

                    # ذخیره در Arvan Cloud
                    self.processed_image.save(
                        processed_filename,
                        ContentFile(output.getvalue()),
                        save=False
                    )

                    # تنظیم URL و اندازه
                    self.processed_url = self.processed_image.url
                    self.processed_size = len(output.getvalue())

                    # محاسبه نسبت فشرده‌سازی
                    if self.original_size > 0:
                        self.compression_ratio = ((self.original_size - self.processed_size) / self.original_size) * 100

                    # ذخیره بدون فراخوانی مجدد save
                    super().save(update_fields=[
                        'processed_image', 'processed_url', 'processed_size', 'compression_ratio'
                    ])

                    logger.info(f"تصویر {self.title} پردازش شد - کاهش حجم: {self.compression_ratio:.1f}%")
                    return True

        except Exception as e:
            logger.error(f"خطا در پردازش تصویر {self.id}: {str(e)}")
            return False

    def _resize_image(self, img):
        """تغییر اندازه تصویر بر اساس تنظیمات"""
        if self.resize_option == 'original':
            return img

        size_mappings = getattr(settings, 'IMAGE_UPLOAD_SETTINGS', {}).get('RESIZE_DIMENSIONS', {
            'large': (1920, 1080),
            'medium': (1280, 720),
            'small': (800, 600),
            'thumbnail': (300, 200),
        })

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
        quality_mappings = getattr(settings, 'IMAGE_UPLOAD_SETTINGS', {}).get('MINIFICATION_LEVELS', {
            'none': 95,
            'low': 90,
            'medium': 75,
            'high': 60,
            'maximum': 45,
        })
        return quality_mappings.get(self.minification_level, 95)

    def get_file_size_display(self, size_bytes):
        """تبدیل بایت به فرمت قابل خواندن"""
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
        return self.original_url or (self.original_image.url if self.original_image else None)

    @classmethod
    def get_total_storage_used(cls):
        """محاسبه کل فضای استفاده شده"""
        from django.db.models import Sum
        result = cls.objects.aggregate(
            total_original=Sum('original_size'),
            total_processed=Sum('processed_size')
        )
        return {
            'original': result['total_original'] or 0,
            'processed': result['total_processed'] or 0,
            'total': (result['total_original'] or 0) + (result['total_processed'] or 0)
        }

    @classmethod
    def get_compression_stats(cls):
        """آمار فشرده‌سازی"""
        from django.db.models import Avg, Sum
        return cls.objects.filter(
            compression_ratio__gt=0
        ).aggregate(
            avg_compression=Avg('compression_ratio'),
            total_saved=Sum('original_size') - Sum('processed_size')
        )


class ImageGallery(models.Model):
    """گالری تصاویر"""

    name = models.CharField(
        max_length=200,
        verbose_name='نام گالری',
        help_text='نام گالری تصاویر'
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='توضیحات گالری'
    )

    images = models.ManyToManyField(
        ImageUpload,
        verbose_name='تصاویر',
        blank=True,
        help_text='تصاویر این گالری'
    )

    cover_image = models.ForeignKey(
        ImageUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gallery_covers',
        verbose_name='تصویر کاور',
        help_text='تصویر کاور گالری'
    )

    is_public = models.BooleanField(
        default=True,
        verbose_name='عمومی',
        help_text='آیا این گالری عمومی است؟'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='ایجاد شده توسط'
    )

    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'گالری تصاویر'
        verbose_name_plural = 'گالری‌های تصاویر'
        ordering = ['-created_at']

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