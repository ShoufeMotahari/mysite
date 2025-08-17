# users/models.py - Enhanced with User Types
import logging
import random
import uuid

from ckeditor.fields import RichTextField
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)

import django_jalali.db.models as jmodels
from django.conf import settings
from django.db import models
from django.utils import timezone


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


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    content = RichTextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"

    def __str__(self):
        return f"{self.recipient.email} - {self.get_status_display()} - {self.subject}"


class UserType(models.Model):
    """Model for different user types/roles"""

    # Predefined user type choices
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    AUTHOR = "author"
    SUBSCRIBER = "subscriber"
    CUSTOMER = "customer"
    GUEST = "guest"

    TYPE_CHOICES = [
        (ADMIN, "مدیر سیستم"),
        (MANAGER, "مدیر"),
        (EDITOR, "ویرایشگر"),
        (AUTHOR, "نویسنده"),
        (SUBSCRIBER, "مشترک"),
        (CUSTOMER, "مشتری"),
        (GUEST, "مهمان"),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name="نام نوع کاربری")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    # Permissions for this user type
    can_create_content = models.BooleanField(
        default=False, verbose_name="امکان ایجاد محتوا"
    )
    can_edit_content = models.BooleanField(
        default=False, verbose_name="امکان ویرایش محتوا"
    )
    can_delete_content = models.BooleanField(
        default=False, verbose_name="امکان حذف محتوا"
    )
    can_manage_users = models.BooleanField(
        default=False, verbose_name="امکان مدیریت کاربران"
    )
    can_view_analytics = models.BooleanField(
        default=False, verbose_name="امکان مشاهده آمار"
    )
    can_access_admin = models.BooleanField(
        default=False, verbose_name="دسترسی به پنل ادمین"
    )

    # Content limits
    max_posts_per_day = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="حداکثر پست روزانه"
    )
    max_comments_per_day = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="حداکثر نظر روزانه"
    )
    max_file_upload_size_mb = models.PositiveIntegerField(
        default=10, verbose_name="حداکثر اندازه فایل (مگابایت)"
    )

    # Status and metadata
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "نوع کاربری"
        verbose_name_plural = "انواع کاربری"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        # Ensure only one default user type
        if self.is_default:
            UserType.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )

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
                    name="مشترک",
                    slug="subscriber",
                    description="کاربر عادی سیستم",
                    is_default=True,
                    can_create_content=False,
                    can_edit_content=False,
                    can_delete_content=False,
                    max_comments_per_day=10,
                )
            return default_type

    def get_permissions_display(self):
        """Get a readable display of permissions"""
        permissions = []
        if self.can_create_content:
            permissions.append("ایجاد محتوا")
        if self.can_edit_content:
            permissions.append("ویرایش محتوا")
        if self.can_delete_content:
            permissions.append("حذف محتوا")
        if self.can_manage_users:
            permissions.append("مدیریت کاربران")
        if self.can_view_analytics:
            permissions.append("مشاهده آمار")
        if self.can_access_admin:
            permissions.append("دسترسی ادمین")

        return ", ".join(permissions) if permissions else "بدون مجوز خاص"


class User(AbstractUser):
    """Enhanced User model with user types"""

    mobile = models.CharField(max_length=11, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=254, unique=False, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    image = models.ImageField(upload_to="avatars/", null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True, max_length=255)

    # User type relationship
    user_type = models.ForeignKey(
        UserType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="نوع کاربری",
        help_text="نوع کاربری تعیین کننده سطح دسترسی کاربر است",
    )

    # Additional user information
    bio = models.TextField(blank=True, null=True, verbose_name="بیوگرافی")
    birth_date = models.DateField(blank=True, null=True, verbose_name="تاریخ تولد")

    # Status fields
    created_at = jmodels.jDateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_phone_verified = models.BooleanField(
        default=False, verbose_name="تلفن تایید شده"
    )
    is_email_verified = models.BooleanField(
        default=False, verbose_name="ایمیل تایید شده"
    )
    is_staff = models.BooleanField(default=False, verbose_name="دسترسی ادمین")

    # Activity tracking
    last_activity = models.DateTimeField(
        null=True, blank=True, verbose_name="آخرین فعالیت"
    )
    posts_count = models.PositiveIntegerField(default=0, verbose_name="تعداد پست‌ها")
    comments_count = models.PositiveIntegerField(default=0, verbose_name="تعداد نظرات")

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
                base_slug = slugify(self.email.split("@")[0])
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

        return reverse("user_profile", kwargs={"slug": self.slug})

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
            "create_content": self.user_type.can_create_content,
            "edit_content": self.user_type.can_edit_content,
            "delete_content": self.user_type.can_delete_content,
            "manage_users": self.user_type.can_manage_users,
            "view_analytics": self.user_type.can_view_analytics,
            "access_admin": self.user_type.can_access_admin,
        }

        return permission_map.get(permission, False)

    def get_daily_limit(self, limit_type):
        """Get daily limit for specific content type"""
        if not self.user_type:
            return 0

        if limit_type == "posts":
            return self.user_type.max_posts_per_day
        elif limit_type == "comments":
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
        self.save(update_fields=["last_activity"])

    def get_user_type_display(self):
        """Get user type display name"""
        return self.user_type.name if self.user_type else "نامشخص"


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
        verbose_name = "کد ثبت نام قدیمی"
        verbose_name_plural = "کدهای ثبت نام قدیمی"


class VerificationToken(models.Model):
    TOKEN_TYPES = [
        ("registration", "Registration"),
        ("login", "Login"),
        ("password_reset", "Password Reset"),
        ("email_activation", "Email Activation"),
        ("phone_verification", "Phone Verification"),
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
        import datetime

        from django.utils import timezone

        expiry_time = self.created_at + datetime.timedelta(minutes=15)
        return timezone.now() > expiry_time

    def mark_as_used(self):
        self.is_used = True
        self.save()
        logger.info(
            f"Verification token marked as used - User: {self.user}, Type: {self.token_type}"
        )

    @classmethod
    def generate_sms_token(cls):
        """Generate a 6-digit SMS verification code"""
        return str(random.randint(100000, 999999))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            logger.info(
                f"Creating verification token - User: {self.user}, Type: {self.token_type}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.token_type} - {self.token}"

    class Meta:
        verbose_name = "کد تایید"
        verbose_name_plural = "کدهای تایید"
        ordering = ["-created_at"]


try:
    from django_jalali.admin.filters import JDateFieldListFilter
except ImportError:
    from django.contrib.admin import DateFieldListFilter as JDateFieldListFilter


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

    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="comment_responses",
        verbose_name="پاسخ داده شده توسط",
        blank=True,
        null=True
    )

    responded_at = models.DateTimeField(
        verbose_name="تاریخ پاسخ",
        blank=True,
        null=True
    )

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

    subject = models.CharField(
        max_length=200, verbose_name="موضوع", help_text="موضوع پیام"
    )

    message = models.TextField(verbose_name="متن پیام", help_text="متن کامل پیام")

    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="normal", verbose_name="اولویت"
    )

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="unread", verbose_name="وضعیت"
    )

    # Timestamps
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ خواندن")
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    # Tracking fields
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="AdminMessageReadStatus",
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
        read_status, created = AdminMessageReadStatus.objects.get_or_create(
            message=self, user=user, defaults={"read_at": timezone.now()}
        )
        if not created and not read_status.read_at:
            read_status.read_at = timezone.now()
            read_status.save()

        # Update overall status if this is the first read
        if self.status == "unread":
            self.status = "read"
            self.read_at = timezone.now()
            self.save(update_fields=["status", "read_at"])

    def get_priority_color(self):
        """Get CSS color class for priority"""
        colors = {
            "low": "text-muted",
            "normal": "text-info",
            "high": "text-warning",
            "urgent": "text-danger",
        }
        return colors.get(self.priority, "text-info")

    def get_priority_icon(self):
        """Get icon for priority"""
        icons = {"low": "⬇️", "normal": "➡️", "high": "⬆️", "urgent": "🚨"}
        return icons.get(self.priority, "➡️")

    @classmethod
    def get_unread_count(cls):
        """Get count of unread messages"""
        return cls.objects.filter(status="unread").count()

    @classmethod
    def get_recent_messages(cls, limit=5):
        """Get recent messages for notification"""
        return cls.objects.filter(status="unread").order_by("-created_at")[:limit]


class AdminMessageReadStatus(models.Model):
    """Track which superuser admins have read which messages"""

    message = models.ForeignKey(
        AdminMessage, on_delete=models.CASCADE, verbose_name="پیام"
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

