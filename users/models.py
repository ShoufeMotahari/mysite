from django.db import models
import django_jalali.db.models as jmodels
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import random
from django.utils import timezone
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_jalali = jmodels.jDateTimeField(auto_now_add=True)
    updated_jalali = jmodels.jDateTimeField(auto_now=True)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)

class User(AbstractUser):
    mobile = models.CharField(max_length=11, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=254, unique=True)  # Changed to EmailField with proper length
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)  # Increased length
    slug = models.SlugField(unique=True, blank=True)
    created_at = jmodels.jDateTimeField(auto_now_add=True)
    second_password = models.CharField(max_length=6, null=True, blank=True)
    is_active = models.BooleanField(default=False, verbose_name='فعال')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.username or self.email or self.mobile)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.mobile


class RegisterToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() - self.created < timezone.timedelta(minutes=5)

    def __str__(self):
        return f"{self.user} - {self.code}"


