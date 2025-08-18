import logging
from django.db import models
from django.utils.text import slugify

logger = logging.getLogger(__name__)


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
