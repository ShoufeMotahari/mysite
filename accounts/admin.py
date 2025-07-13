# admin.py (Enhanced version with "Send to All Users" functionality)
from django.contrib import admin
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import path
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ValidationError

from accounts.forms.forms import EmailForm
from accounts.managers.email_manager import EmailManager, SendEmailCommand
from accounts.services.email_service import EmailValidator
from core.models import EmailTemplate
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter
import logging

from users.models import User

logger = logging.getLogger('core')


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', ('created_at', JDateFieldListFilter)]
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'updated_at']

    # Add fieldsets for better organization
    fieldsets = (
        (None, {
            'fields': ('name', 'subject', 'content', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if change:
            logger.info(f"📝 Email template updated: '{obj.name}' by {request.user.username}")
        else:
            logger.info(f"➕ New email template created: '{obj.name}' by {request.user.username}")
        super().save_model(request, obj, form, change)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'mobile', 'is_active', 'email_status', 'created_at']
    list_filter = ['is_active', ('created_at', JDateFieldListFilter)]
    search_fields = ['username', 'email', 'mobile']
    actions = ['send_email_action', 'activate_users', 'deactivate_users']
    list_per_page = 50

    # Add fieldsets for better user editing
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'mobile')
        }),
        ('Status', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', ]

    def email_status(self, obj):
        """Display email validation status"""
        if not obj.email:
            return format_html('<span style="color: red;">No Email</span>')

        if not obj.is_active:
            return format_html('<span style="color: orange;">Inactive User</span>')

        try:
            EmailValidator.validate_email(obj.email)
            return format_html('<span style="color: green;">Valid</span>')
        except ValidationError:
            return format_html('<span style="color: red;">Invalid Email</span>')

    email_status.short_description = 'Email Status'

    def send_email_action(self, request, queryset):
        selected = queryset.values_list('id', flat=True)
        selected_count = len(selected)

        logger.info(f"👨‍💼 Admin {request.user.username} initiated email action for {selected_count} users")
        logger.debug(f"Selected user IDs: {list(selected)}")

        request.session['selected_users'] = list(selected)
        return HttpResponseRedirect(reverse('admin:send_email'))

    send_email_action.short_description = 'ارسال ایمیل به کاربران انتخاب شده'

    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        logger.info(f"👨‍💼 Admin {request.user.username} activated {updated} users")
        self.message_user(request, f'{updated} کاربر فعال شد.')

    activate_users.short_description = 'فعال کردن کاربران انتخاب شده'

    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        logger.info(f"👨‍💼 Admin {request.user.username} deactivated {updated} users")
        self.message_user(request, f'{updated} کاربر غیرفعال شد.')

    deactivate_users.short_description = 'غیرفعال کردن کاربران انتخاب شده'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-email/', self.send_email_view, name='send_email'),
            path('send-email-all/', self.send_email_all_view, name='send_email_all'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add 'Send Email to All Users' button"""
        extra_context = extra_context or {}
        extra_context['show_send_all_email_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def send_email_all_view(self, request):
        """Send email to all users view"""
        logger.info(f"👨‍💼 Admin {request.user.username} accessing send email to all users")

        # Get all user IDs
        all_user_ids = list(User.objects.values_list('id', flat=True))
        request.session['selected_users'] = all_user_ids
        request.session['email_all_users'] = True

        logger.info(f"📊 Preparing to send email to all {len(all_user_ids)} users")

        return HttpResponseRedirect(reverse('admin:send_email'))

    def send_email_view(self, request):
        """Enhanced send email view with better error handling"""
        if request.method == 'POST':
            return self._handle_email_post(request)
        else:
            return self._handle_email_get(request)

    def _handle_email_post(self, request):
        """Handle POST request for email sending"""
        form = EmailForm(request.POST)
        if not form.is_valid():
            logger.warning(f"⚠️ Invalid form submission by {request.user.username}")
            logger.debug(f"Form errors: {form.errors}")
            return self._render_email_form(request, form)

        try:
            # Get selected users
            selected_users = request.session.get('selected_users', [])
            is_email_all = request.session.get('email_all_users', False)

            if not selected_users:
                logger.warning(f"⚠️ No users selected for email sending by {request.user.username}")
                messages.error(request, 'هیچ کاربری انتخاب نشده است.')
                return redirect('admin:users_user_changelist')

            logger.info(f"🎯 Processing email form submission by {request.user.username}")
            logger.info(f"Selected users count: {len(selected_users)}")
            logger.info(f"Email all users: {is_email_all}")
            logger.info(f"Template: {form.cleaned_data['template'].name}")
            logger.info(f"Custom subject: {form.cleaned_data.get('subject', 'None')}")

            # Create and execute command
            command = SendEmailCommand(
                template_id=form.cleaned_data['template'].id,
                user_ids=selected_users,
                sender=request.user,
                custom_subject=form.cleaned_data.get('subject'),
                custom_content=form.cleaned_data.get('content')
            )

            manager = EmailManager()
            manager.add_command(command)
            results = manager.execute_commands()

            # Process results
            self._process_email_results(request, results, is_email_all)

            # Clear session
            if 'selected_users' in request.session:
                del request.session['selected_users']
            if 'email_all_users' in request.session:
                del request.session['email_all_users']

            return redirect('admin:users_user_changelist')

        except Exception as e:
            error_msg = f'خطا در ارسال ایمیل: {str(e)}'
            messages.error(request, error_msg)
            logger.error(f"❌ Exception in admin email sending by {request.user.username}: {str(e)}")
            logger.exception("Full exception details:")
            return self._render_email_form(request, form)

    def _handle_email_get(self, request):
        """Handle GET request for email form display"""
        form = EmailForm()
        logger.info(f"📋 Email form displayed to admin {request.user.username}")
        return self._render_email_form(request, form)

    def _render_email_form(self, request, form):
        """Render the email form with validation info"""
        selected_users = request.session.get('selected_users', [])
        is_email_all = request.session.get('email_all_users', False)
        users = User.objects.filter(id__in=selected_users)

        # Add validation info to context
        valid_users, invalid_users = EmailValidator.validate_users(users)

        logger.debug(f"Form display: {len(valid_users)} valid, {len(invalid_users)} invalid users")

        context = {
            'form': form,
            'users': users,
            'valid_users': valid_users,
            'invalid_users': invalid_users,
            'is_email_all': is_email_all,
            'total_users': len(users),
            'title': 'ارسال ایمیل به همه کاربران' if is_email_all else 'ارسال ایمیل'
        }

        return render(request, 'admin/send_email.html', context)

    def _process_email_results(self, request, results, is_email_all=False):
        """Process email sending results and display appropriate messages"""
        if results and results[0][0]:  # Check if successful
            success, message, details = results[0]

            # Create detailed success message
            total_users = details.get('total_users', 0)
            valid_users = details.get('valid_users', 0)
            invalid_users = details.get('invalid_users', 0)

            if is_email_all:
                if invalid_users > 0:
                    success_msg = f'ایمیل با موفقیت به {valid_users} کاربر از {total_users} کاربر موجود ارسال شد. ({invalid_users} کاربر نامعتبر نادیده گرفته شد)'
                    messages.success(request, success_msg)
                    self._add_invalid_user_warnings(request, details)
                else:
                    success_msg = f'ایمیل با موفقیت به تمام {valid_users} کاربر سیستم ارسال شد.'
                    messages.success(request, success_msg)
            else:
                if invalid_users > 0:
                    success_msg = f'ایمیل با موفقیت به {valid_users} کاربر از {total_users} کاربر انتخاب شده ارسال شد. ({invalid_users} کاربر نامعتبر نادیده گرفته شد)'
                    messages.success(request, success_msg)
                    self._add_invalid_user_warnings(request, details)
                else:
                    success_msg = f'ایمیل با موفقیت به تمام {valid_users} کاربر انتخاب شده ارسال شد.'
                    messages.success(request, success_msg)

            logger.info(f"✅ Email successfully processed by admin {request.user.username}")
            logger.info(f"  📊 Results: {valid_users}/{total_users} users, {invalid_users} invalid")

        else:
            error_msg = results[0][1] if results else 'خطای نامشخص'
            messages.error(request, f'خطا در ارسال ایمیل: {error_msg}')
            logger.error(f"❌ Email sending failed by admin {request.user.username}: {error_msg}")

    def _add_invalid_user_warnings(self, request, details):
        """Add warning messages for invalid users"""
        invalid_details = details.get('invalid_details', [])
        if invalid_details:
            warning_msg = "کاربران نامعتبر: "
            invalid_reasons = []
            for invalid_user in invalid_details:
                user = invalid_user['user']
                issues = invalid_user['issues']
                reason = []
                if 'inactive_user' in issues:
                    reason.append('غیرفعال')
                if 'invalid_email' in issues:
                    reason.append('ایمیل نامعتبر')
                invalid_reasons.append(f"{user.username} ({', '.join(reason)})")

            warning_msg += ", ".join(invalid_reasons)
            messages.warning(request, warning_msg)


# Customize admin site
admin.site.site_header = 'پنل مدیریت'
admin.site.site_title = 'پنل مدیریت'
admin.site.index_title = 'خوش آمدید به پنل مدیریت'