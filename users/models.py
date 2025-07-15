# users/models.py
from django.db import models
import django_jalali.db.models as jmodels
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import random
from django.utils import timezone
from django.conf import settings
import uuid


class User(AbstractUser):
    mobile = models.CharField(max_length=11, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    created_at = jmodels.jDateTimeField(auto_now_add=True)
    second_password = models.CharField(max_length=6, null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_phone_verified = models.BooleanField(default=False, verbose_name='تلفن تایید شده')
    is_email_verified = models.BooleanField(default=False, verbose_name='ایمیل تایید شده')

    def _generate_unique_slug(self, base_slug):
        """Generate a unique slug by appending numbers if needed"""
        slug = base_slug
        counter = 1

        while User.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            # Try to create slug from username first, then email, then mobile
            if self.username:
                base_slug = slugify(self.username)
            elif self.email:
                # Use part before @ for email
                base_slug = slugify(self.email.split('@')[0])
            elif self.mobile:
                base_slug = f"user-{self.mobile}"
            else:
                # Fallback to UUID
                base_slug = str(uuid.uuid4())[:8]

            # Ensure we have a valid slug
            if not base_slug:
                base_slug = str(uuid.uuid4())[:8]

            self.slug = self._generate_unique_slug(base_slug)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.mobile or self.email

    def get_absolute_url(self):
        """Get the URL for this user's profile"""
        from django.urls import reverse
        return reverse('user_profile', kwargs={'slug': self.slug})


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_jalali = jmodels.jDateTimeField(auto_now_add=True)
    updated_jalali = jmodels.jDateTimeField(auto_now=True)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user}"


# Keep your existing RegisterToken for backward compatibility
class RegisterToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() - self.created < timezone.timedelta(minutes=5)

    def __str__(self):
        return f"{self.user} - {self.code}"


# New comprehensive verification token model
class VerificationToken(models.Model):
    TOKEN_TYPES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
        ('email_activation', 'Email Activation'),
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

    def mark_as_used(self):
        self.is_used = True
        self.save()

    @classmethod
    def generate_sms_token(cls):
        return str(random.randint(100000, 999999))

    def __str__(self):
        return f"{self.user} - {self.token_type} - {self.token}"

    class Meta:
        verbose_name = 'کد تایید'
        verbose_name_plural = 'کدهای تایید'


class Comment(models.Model):
    """Model for user comments"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_set',
        verbose_name='کاربر'
    )
    content = models.TextField(verbose_name='متن نظر')
    is_approved = models.BooleanField(default=False, verbose_name='تایید شده')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    # Optional: Add reference to what the comment is about
    # For example, if comments are about products, articles, etc.
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.content[:50]}...'

    def get_absolute_url(self):
        """Get URL for this comment"""
        return f'/comments/{self.id}/'