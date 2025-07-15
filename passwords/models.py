from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class PasswordEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service_name} - {self.username}"

    class Meta:
        unique_together = ['user', 'service_name', 'username']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            logger.info(
                f"Creating new password entry - User: {self.user.username}, Service: {self.service_name}, Username: {self.username}")
        else:
            logger.info(
                f"Updating password entry - User: {self.user.username}, Service: {self.service_name}, Username: {self.username}")

        try:
            super().save(*args, **kwargs)
            action = "created" if is_new else "updated"
            logger.info(
                f"Password entry {action} successfully - ID: {self.pk}, User: {self.user.username}, Service: {self.service_name}")
        except Exception as e:
            logger.error(
                f"Failed to save password entry - User: {self.user.username}, Service: {self.service_name}, Error: {str(e)}")
            raise

    def delete(self, *args, **kwargs):
        logger.info(
            f"Deleting password entry - ID: {self.pk}, User: {self.user.username}, Service: {self.service_name}, Username: {self.username}")
        try:
            super().delete(*args, **kwargs)
            logger.info(
                f"Password entry deleted successfully - User: {self.user.username}, Service: {self.service_name}")
        except Exception as e:
            logger.error(
                f"Failed to delete password entry - ID: {self.pk}, User: {self.user.username}, Error: {str(e)}")
            raise

    def encrypt_password(self, password):
        """Encrypt password before storing"""
        logger.debug(f"Starting password encryption - User: {self.user.username}, Service: {self.service_name}")
        try:
            f = Fernet(settings.ENCRYPTION_KEY)
            encrypted_password = f.encrypt(password.encode())
            self.password = encrypted_password.decode()
            logger.info(f"Password encrypted successfully - User: {self.user.username}, Service: {self.service_name}")
        except Exception as e:
            logger.error(
                f"Password encryption failed - User: {self.user.username}, Service: {self.service_name}, Error: {str(e)}")
            raise ValidationError("Error encrypting password")

    def decrypt_password(self):
        """Decrypt password for display"""
        logger.debug(f"Starting password decryption - User: {self.user.username}, Service: {self.service_name}")
        try:
            f = Fernet(settings.ENCRYPTION_KEY)
            decrypted_password = f.decrypt(self.password.encode())
            logger.info(f"Password decrypted successfully - User: {self.user.username}, Service: {self.service_name}")
            return decrypted_password.decode()
        except Exception as e:
            logger.error(
                f"Password decryption failed - User: {self.user.username}, Service: {self.service_name}, Error: {str(e)}")
            raise ValidationError("Error decrypting password")
