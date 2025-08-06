from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django import forms
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth import get_user_model
from .models import EmailBroadcast
import logging
from .tasks import send_broadcast_email

User = get_user_model()
logger = logging.getLogger('emails')


class EmailBroadcastForm(forms.ModelForm):
    content = forms.CharField(
        widget=CKEditorWidget(config_name='default'),
        help_text="Use the rich text editor to create your HTML email content."
    )

    class Meta:
        model = EmailBroadcast
        fields = ['subject', 'content']
        widgets = {
            'subject': forms.TextInput(attrs={'size': 60}),
        }


class EmailLogInline(admin.TabularInline):
    extra = 0
    readonly_fields = ['recipient', 'status', 'error_message', 'sent_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EmailBroadcast)
class EmailBroadcastAdmin(admin.ModelAdmin):
    form = EmailBroadcastForm
    list_display = [
        'subject',
        'status_badge',
        'created_by',
        'total_recipients',
        'successful_sends',
        'failed_sends',
        'created_at',
        'actions_column'
    ]
    list_filter = ['status', 'created_at', 'created_by']
    search_fields = ['subject', 'content']
    readonly_fields = [
        'status',
        'created_by',
        'total_recipients',
        'successful_sends',
        'failed_sends',
        'sent_at',
        'preview_content'
    ]
    inlines = [EmailLogInline]

    fieldsets = (
        ('Email Content', {
            'fields': ('subject', 'content', 'preview_content')
        }),
        ('Status Information', {
            'fields': (
                'status',
                'created_by',
                'total_recipients',
                'successful_sends',
                'failed_sends',
                'sent_at'
            ),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'sending': 'blue',
            'sent': 'green',
            'failed': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def actions_column(self, obj):
        if obj.status == 'draft':
            return format_html(
                '<a class="button" href="{}">Send Email</a>',
                reverse('admin:emails_emailbroadcast_send', args=[obj.pk])
            )
        elif obj.status == 'sent':
            return format_html(
                '<a class="button" href="{}">View Details</a>',
                reverse('admin:emails_emailbroadcast_change', args=[obj.pk])
            )
        return '-'

    actions_column.short_description = 'Actions'

    def preview_content(self, obj):
        if obj.content:
            return format_html(
                '<div style="border: 1px solid #ddd; padding: 10px; max-height: 200px; overflow-y: auto;">{}</div>',
                obj.content
            )
        return '-'

    preview_content.short_description = 'Content Preview'

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
            logger.info(f"New email broadcast created by {request.user.username}: '{obj.subject}'")
        else:
            logger.info(f"Email broadcast updated by {request.user.username}: '{obj.subject}'")
        super().save_model(request, obj, form, change)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/send/',
                self.admin_site.admin_view(self.send_email_view),
                name='emails_emailbroadcast_send',
            ),
        ]
        return custom_urls + urls

    def send_email_view(self, request, object_id):
        broadcast = self.get_object(request, object_id)

        if request.method == 'POST':
            logger.info(f"Email broadcast send initiated by {request.user.username} for broadcast ID: {broadcast.id}")

            # Count active users with email addresses
            active_users = User.objects.filter(
                is_active=True,
                email__isnull=False
            ).exclude(email='')

            broadcast.total_recipients = active_users.count()
            broadcast.status = 'sending'
            broadcast.save()

            logger.info(
                f"Email broadcast {broadcast.id} status changed to 'sending'. Total recipients: {broadcast.total_recipients}")

            # Send emails (this could be done asynchronously)
            try:
                send_broadcast_email(broadcast.id)
                logger.info(f"Email broadcast {broadcast.id} sending process completed successfully")
                messages.success(
                    request,
                    f'Email broadcast "{broadcast.subject}" has been sent to {broadcast.total_recipients} recipients.'
                )
            except Exception as e:
                broadcast.status = 'failed'
                broadcast.save()
                logger.error(f"Email broadcast {broadcast.id} failed during sending process: {str(e)}")
                messages.error(request, f'Failed to send email: {str(e)}')

            return HttpResponseRedirect(reverse('admin:emails_emailbroadcast_changelist'))

        # Show confirmation page
        logger.info(
            f"Email broadcast confirmation page accessed by {request.user.username} for broadcast ID: {broadcast.id}")

        context = {
            'broadcast': broadcast,
            'recipient_count': User.objects.filter(
                is_active=True,
                email__isnull=False
            ).exclude(email='').count(),
            'title': f'Send Email: {broadcast.subject}',
            'opts': self.model._meta,
        }

        return render(request, 'admin/emails/send_confirmation.html', context)

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of draft emails
        if obj and obj.status != 'draft':
            logger.warning(f"User {request.user.username} attempted to delete non-draft email broadcast: {obj.id}")
            return False
        if obj:
            logger.info(f"User {request.user.username} deleted email broadcast: {obj.id} - '{obj.subject}'")
        return super().has_delete_permission(request, obj)


