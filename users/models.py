# users/models.py
from django.db import models
import django_jalali.db.models as jmodels
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import random
from django.utils import timezone
from django.conf import settings
import uuid
import logging

logger = logging.getLogger(__name__)


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
        return self.username or self.mobile or self.email or f"User {self.id}"

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

    def mark_as_used(self):
        self.is_used = True
        self.save()
        logger.info(f"Verification token marked as used - User: {self.user}, Type: {self.token_type}")

    @classmethod
    def generate_sms_token(cls):
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


# Move PasswordEntry to a separate passwords app or keep it here if truly needed
class PasswordEntry(models.Model):
    """Password storage model - consider moving to passwords app"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_name = models.CharField(max_length=100, verbose_name='نام سرویس')
    username = models.CharField(max_length=100, verbose_name='نام کاربری')
    password = models.TextField(verbose_name='رمز عبور')  # Encrypted, so might be long
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
        is_new = self.pk is None
        action = "Creating" if is_new else "Updating"
        logger.info(f"{action} password entry - User: {self.user.username}, Service: {self.service_name}")

        try:
            super().save(*args, **kwargs)
            action = "created" if is_new else "updated"
            logger.info(f"Password entry {action} successfully - ID: {self.pk}")
        except Exception as e:
            logger.error(f"Failed to save password entry - User: {self.user.username}, Error: {str(e)}")
            raise

    def delete(self, *args, **kwargs):
        logger.info(
            f"Deleting password entry - ID: {self.pk}, User: {self.user.username}, Service: {self.service_name}")
        try:
            super().delete(*args, **kwargs)
            logger.info(f"Password entry deleted successfully")
        except Exception as e:
            logger.error(f"Failed to delete password entry - ID: {self.pk}, Error: {str(e)}")
            raise

    def encrypt_password(self, password):
        """Encrypt password before storing"""
        try:
            from cryptography.fernet import Fernet
            from django.core.exceptions import ValidationError

            logger.debug(f"Encrypting password for service: {self.service_name}")
            f = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY,
                                                                      str) else settings.ENCRYPTION_KEY)
            encrypted_password = f.encrypt(password.encode())
            self.password = encrypted_password.decode()
            logger.info(f"Password encrypted successfully for service: {self.service_name}")
        except Exception as e:
            logger.error(f"Password encryption failed - Service: {self.service_name}, Error: {str(e)}")
            raise ValidationError("Error encrypting password")

    def decrypt_password(self):
        """Decrypt password for display"""
        try:
            from cryptography.fernet import Fernet
            from django.core.exceptions import ValidationError

            logger.debug(f"Decrypting password for service: {self.service_name}")
            f = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY,
                                                                      str) else settings.ENCRYPTION_KEY)
            decrypted_password = f.decrypt(self.password.encode())
            logger.info(f"Password decrypted successfully for service: {self.service_name}")
            return decrypted_password.decode()
        except Exception as e:
            logger.error(f"Password decryption failed - Service: {self.service_name}, Error: {str(e)}")
            raise ValidationError("Error decrypting password")