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

    RECIPIENT_TYPE_CHOICES = [
        ('all', 'All Active Users'),
        ('staff', 'Staff Members Only'),
        ('superusers', 'Superusers Only'),
        ('custom', 'Selected Users'),
    ]

    subject = models.CharField(max_length=255)
    content = RichTextField()  # Changed to RichTextField for better CKEditor support
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Recipient selection fields
    recipient_type = models.CharField(
        max_length=20,
        choices=RECIPIENT_TYPE_CHOICES,
        default='all',
        help_text='Who should receive this email'
    )
    custom_recipient_ids = models.TextField(
        blank=True,
        null=True,
        help_text='Comma-separated user IDs for custom recipient selection'
    )

    # Statistics
    total_recipients = models.IntegerField(default=0)
    successful_sends = models.IntegerField(default=0)
    failed_sends = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Broadcast'
        verbose_name_plural = 'Email Broadcasts'

    def __str__(self):
        return f"{self.subject} - {self.get_status_display()}"

    def get_recipients(self):
        """Get the actual User objects that will receive this email"""
        if self.recipient_type == 'all':
            return User.objects.filter(is_active=True, email__isnull=False).exclude(email='')
        elif self.recipient_type == 'staff':
            return User.objects.filter(is_active=True, is_staff=True, email__isnull=False).exclude(email='')
        elif self.recipient_type == 'superusers':
            return User.objects.filter(is_active=True, is_superuser=True, email__isnull=False).exclude(email='')
        elif self.recipient_type == 'custom' and self.custom_recipient_ids:
            recipient_ids = [int(id.strip()) for id in self.custom_recipient_ids.split(',') if id.strip().isdigit()]
            return User.objects.filter(id__in=recipient_ids, is_active=True)

        # Fallback to all users
        return User.objects.filter(is_active=True, email__isnull=False).exclude(email='')

    @property
    def recipient_count(self):
        """Calculate recipient count without hitting database if total_recipients is set"""
        if self.total_recipients > 0:
            return self.total_recipients
        return self.get_recipients().count()

    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        if self.total_recipients == 0:
            return 0
        return round((self.successful_sends / self.total_recipients) * 100, 2)


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
        unique_together = ['broadcast', 'recipient']  # Prevent duplicate logs

    def __str__(self):
        return f"{self.broadcast.subject} to {self.recipient.email} - {self.get_status_display()}"


class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام قالب')
    subject = models.CharField(max_length=200, verbose_name='موضوع')
    content = RichTextField(verbose_name='محتوا')  # Changed to RichTextField
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = jmodels.jDateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'قالب ایمیل'
        verbose_name_plural = 'قالب‌های ایمیل'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name