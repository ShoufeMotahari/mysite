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
    slug = models.SlugField(unique=True, blank=True)
    created_at = jmodels.jDateTimeField(auto_now_add=True)
    second_password = models.CharField(max_length=6, null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='فعال')  # Changed to True
    is_phone_verified = models.BooleanField(default=False, verbose_name='تلفن تایید شده')
    is_email_verified = models.BooleanField(default=False, verbose_name='ایمیل تایید شده')

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.username or self.email or self.mobile)
            self.slug = base_slug or str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.mobile or self.email


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