from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField
import django_jalali.db.models as jmodels

User = get_user_model()


class EmailBroadcast(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    subject = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    total_recipients = models.IntegerField(default=0)
    successful_sends = models.IntegerField(default=0)
    failed_sends = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Broadcast'
        verbose_name_plural = 'Email Broadcasts'

    def __str__(self):
        return f"{self.subject} - {self.status}"


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    broadcast = models.ForeignKey(EmailBroadcast, on_delete=models.CASCADE, related_name='logs')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"{self.broadcast.subject} to {self.recipient.email} - {self.status}"

class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    subject = models.CharField(max_length=200, verbose_name='موضوع')
    content = RichTextField(verbose_name='محتوا')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'قالب ایمیل'
        verbose_name_plural = 'قالب‌های ایمیل'

    def __str__(self):
        return self.name
