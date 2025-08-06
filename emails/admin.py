from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django import forms
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth import get_user_model
from .models import EmailBroadcast, EmailTemplate
from .tasks import send_broadcast_email
import logging

User = get_user_model()
logger = logging.getLogger('emails')


class EmailBroadcastForm(forms.ModelForm):
    # Rich text editor for content
    content = forms.CharField(
        widget=CKEditorWidget(config_name='default'),
        help_text="Use the rich text editor to create your HTML email content."
    )

    # User selection field
    RECIPIENT_CHOICES = [
        ('all', 'All Active Users'),
        ('staff', 'Staff Members Only'),
        ('superusers', 'Superusers Only'),
        ('custom', 'Select Specific Users'),
    ]

    recipient_type = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        initial='all',
        widget=forms.RadioSelect,
        help_text="Choose who should receive this email"
    )

    # Custom user selection (shown when 'custom' is selected)
    custom_recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True, email__isnull=False).exclude(email=''),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select specific users to receive this email (only shown when 'Select Specific Users' is chosen)"
    )

    # Email template selection (optional)
    email_template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.filter(is_active=True),
        required=False,
        empty_label="Choose a template (optional)",
        help_text="Select a pre-made template to load content and subject"
    )

    class Meta:
        model = EmailBroadcast
        fields = ['email_template', 'subject', 'content', 'recipient_type', 'custom_recipients']
        widgets = {
            'subject': forms.TextInput(attrs={'size': 80, 'placeholder': 'Enter email subject...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add JavaScript for template loading and recipient type handling
        self.fields['email_template'].widget.attrs.update({
            'onchange': 'loadTemplate(this.value)'
        })

        self.fields['recipient_type'].widget.attrs.update({
            'onchange': 'toggleRecipientSelection(this.value)'
        })

    class Media:
        js = ('admin/js/email_broadcast.js',)  # We'll create this
        css = {
            'all': ('admin/css/email_broadcast.css',)  # We'll create this
        }


@admin.register(EmailBroadcast)
class EmailBroadcastAdmin(admin.ModelAdmin):
    form = EmailBroadcastForm
    list_display = [
        'subject',
        'status_badge',
        'recipient_info',
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
        'preview_content',
        'recipient_list_preview'
    ]
    inlines = [EmailLogInline]

    fieldsets = (
        ('Email Template', {
            'fields': ('email_template',),
            'description': 'Optional: Select a pre-made template to auto-fill content'
        }),
        ('Email Content', {
            'fields': ('subject', 'content', 'preview_content')
        }),
        ('Recipients', {
            'fields': ('recipient_type', 'custom_recipients', 'recipient_list_preview'),
            'description': 'Choose who will receive this email'
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

    def recipient_info(self, obj):
        """Show recipient type information"""
        if hasattr(obj, 'recipient_type'):
            return obj.recipient_type
        return f"{obj.total_recipients} users"

    recipient_info.short_description = 'Recipients'

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
                '<div style="border: 1px solid #ddd; padding: 10px; max-height: 200px; overflow-y: auto; background: #f9f9f9;">{}</div>',
                obj.content
            )
        return '-'

    preview_content.short_description = 'Content Preview'

    def recipient_list_preview(self, obj):
        """Show preview of who will receive the email"""
        if obj.pk:  # Only for existing objects
            # This would show based on the stored recipient_type
            return "Recipients will be calculated when sending"
        return "Save first to see recipient preview"

    recipient_list_preview.short_description = 'Recipient Preview'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            logger.info(f"New email broadcast created by {request.user.username}: '{obj.subject}'")
        else:
            logger.info(f"Email broadcast updated by {request.user.username}: '{obj.subject}'")

        # Store recipient selection info (we'll add these fields to model)
        if hasattr(form, 'cleaned_data'):
            # Store recipient type for later use
            obj.recipient_type = form.cleaned_data.get('recipient_type', 'all')
            if form.cleaned_data.get('custom_recipients'):
                # Store custom recipient IDs as comma-separated string
                recipient_ids = [str(u.id) for u in form.cleaned_data['custom_recipients']]
                obj.custom_recipient_ids = ','.join(recipient_ids)

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
            path(
                'load-template/<int:template_id>/',
                self.admin_site.admin_view(self.load_template_view),
                name='emails_emailbroadcast_load_template',
            ),
            path(
                'preview-recipients/',
                self.admin_site.admin_view(self.preview_recipients_view),
                name='emails_emailbroadcast_preview_recipients',
            ),
        ]
        return custom_urls + urls

    def send_email_view(self, request, object_id):
        broadcast = self.get_object(request, object_id)

        if request.method == 'POST':
            logger.info(f"Email broadcast send initiated by {request.user.username} for broadcast ID: {broadcast.id}")

            # Get recipients based on stored selection
            recipients = self.get_recipients_for_broadcast(broadcast)

            broadcast.total_recipients = recipients.count()
            broadcast.status = 'sending'
            broadcast.save()

            logger.info(
                f"Email broadcast {broadcast.id} status changed to 'sending'. Total recipients: {broadcast.total_recipients}")

            # Send emails asynchronously
            try:
                send_broadcast_email.delay(broadcast.id)
                logger.info(f"Email broadcast {broadcast.id} queued for sending")
                messages.success(
                    request,
                    f'Email broadcast "{broadcast.subject}" has been queued for sending to {broadcast.total_recipients} recipients.'
                )
            except Exception as e:
                broadcast.status = 'failed'
                broadcast.save()
                logger.error(f"Email broadcast {broadcast.id} failed to queue: {str(e)}")
                messages.error(request, f'Failed to queue email: {str(e)}')

            return HttpResponseRedirect(reverse('admin:emails_emailbroadcast_changelist'))

        # Show confirmation page with recipient preview
        recipients = self.get_recipients_for_broadcast(broadcast)

        context = {
            'broadcast': broadcast,
            'recipients': recipients[:10],  # Show first 10 for preview
            'recipient_count': recipients.count(),
            'title': f'Send Email: {broadcast.subject}',
            'opts': self.model._meta,
        }

        return render(request, 'admin/emails/send_confirmation.html', context)

    def load_template_view(self, request, template_id):
        """AJAX view to load template content"""
        try:
            template = EmailTemplate.objects.get(id=template_id, is_active=True)
            return JsonResponse({
                'success': True,
                'subject': template.subject,
                'content': template.content
            })
        except EmailTemplate.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Template not found'
            })

    def get_recipients_for_broadcast(self, broadcast):
        """Get recipients based on broadcast recipient type"""
        recipient_type = getattr(broadcast, 'recipient_type', 'all')

        if recipient_type == 'all':
            return User.objects.filter(is_active=True, email__isnull=False).exclude(email='')
        elif recipient_type == 'staff':
            return User.objects.filter(is_active=True, is_staff=True, email__isnull=False).exclude(email='')
        elif recipient_type == 'superusers':
            return User.objects.filter(is_active=True, is_superuser=True, email__isnull=False).exclude(email='')
        elif recipient_type == 'custom':
            if hasattr(broadcast, 'custom_recipient_ids') and broadcast.custom_recipient_ids:
                recipient_ids = broadcast.custom_recipient_ids.split(',')
                return User.objects.filter(id__in=recipient_ids, is_active=True)

        # Fallback to all users
        return User.objects.filter(is_active=True, email__isnull=False).exclude(email='')

    def preview_recipients_view(self, request):
        """AJAX view to preview recipients"""
        if request.method == 'POST':
            recipient_type = request.POST.get('recipient_type', 'all')
            custom_recipient_ids = request.POST.get('custom_recipient_ids', '')

            try:
                if recipient_type == 'all':
                    recipients = User.objects.filter(is_active=True, email__isnull=False).exclude(email='')
                elif recipient_type == 'staff':
                    recipients = User.objects.filter(is_active=True, is_staff=True, email__isnull=False).exclude(
                        email='')
                elif recipient_type == 'superusers':
                    recipients = User.objects.filter(is_active=True, is_superuser=True, email__isnull=False).exclude(
                        email='')
                elif recipient_type == 'custom' and custom_recipient_ids:
                    recipient_ids = [int(id.strip()) for id in custom_recipient_ids.split(',') if id.strip().isdigit()]
                    recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
                else:
                    recipients = User.objects.none()

                recipient_list = []
                for recipient in recipients[:50]:  # Limit to first 50 for preview
                    recipient_list.append({
                        'id': recipient.id,
                        'email': recipient.email,
                        'first_name': recipient.first_name or '',
                        'last_name': recipient.last_name or '',
                        'is_staff': recipient.is_staff,
                        'is_superuser': recipient.is_superuser,
                    })

                return JsonResponse({
                    'success': True,
                    'count': recipients.count(),
                    'recipients': recipient_list,
                    'recipient_type': recipient_type
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status != 'draft':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'subject', 'content']

    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'subject', 'is_active')
        }),
        ('Content', {
            'fields': ('content',)
        }),
    )

    def save_model(self, request, obj, form, change):
        logger.info(f"Email template {'updated' if change else 'created'} by {request.user.username}: '{obj.name}'")
        super().save_model(request, obj, form, change)

