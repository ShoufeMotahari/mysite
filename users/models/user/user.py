import logging
import uuid
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import django_jalali.db.models as jmodels
from django.db import models
from django.utils import timezone

from users.models.user.user_type import UserType

logger = logging.getLogger(__name__)

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