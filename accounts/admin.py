# admin.py (updated - remove EmailLog admin)
from profile import Profile

from django.contrib import admin
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import path
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse

from accounts.forms.email_forms import EmailForm
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

    def save_model(self, request, obj, form, change):
        if change:
            logger.info(f"📝 Email template updated: '{obj.name}' by {request.user.username}")
        else:
            logger.info(f"➕ New email template created: '{obj.name}' by {request.user.username}")
        super().save_model(request, obj, form, change)


class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'mobile', 'is_active', 'created_at']
    list_filter = ['is_active', ('created_at', JDateFieldListFilter)]
    search_fields = ['username', 'email', 'mobile']
    actions = ['send_email_action']

    def send_email_action(self, request, queryset):
        selected = queryset.values_list('id', flat=True)
        selected_count = len(selected)

        logger.info(f"👨‍💼 Admin {request.user.username} initiated email action for {selected_count} users")
        logger.debug(f"Selected user IDs: {list(selected)}")

        request.session['selected_users'] = list(selected)
        return HttpResponseRedirect(reverse('admin:send_email'))

    send_email_action.short_description = 'ارسال ایمیل به کاربران انتخاب شده'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-email/', self.send_email_view, name='send_email'),
        ]
        return custom_urls + urls

    # admin.py (updated send_email_view method)
    def send_email_view(self, request):
        if request.method == 'POST':
            form = EmailForm(request.POST)
            if form.is_valid():
                try:
                    # Get selected users
                    selected_users = request.session.get('selected_users', [])
                    if not selected_users:
                        logger.warning(f"⚠️ No users selected for email sending by {request.user.username}")
                        messages.error(request, 'هیچ کاربری انتخاب نشده است.')
                        return redirect('admin:users_user_changelist')

                    logger.info(f"🎯 Processing email form submission by {request.user.username}")
                    logger.info(f"Selected users count: {len(selected_users)}")
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

                    if results and results[0][0]:  # Check if successful
                        success, message, details = results[0]

                        # Create detailed success message
                        total_users = details.get('total_users', 0)
                        valid_users = details.get('valid_users', 0)
                        invalid_users = details.get('invalid_users', 0)

                        if invalid_users > 0:
                            success_msg = f'ایمیل با موفقیت به {valid_users} کاربر از {total_users} کاربر انتخاب شده ارسال شد. ({invalid_users} کاربر نامعتبر نادیده گرفته شد)'
                            messages.success(request, success_msg)

                            # Add warning message with details
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
                        else:
                            success_msg = f'ایمیل با موفقیت به تمام {valid_users} کاربر انتخاب شده ارسال شد.'
                            messages.success(request, success_msg)

                        logger.info(f"✅ Email successfully processed by admin {request.user.username}")
                        logger.info(f"  📊 Results: {valid_users}/{total_users} users, {invalid_users} invalid")

                    else:
                        error_msg = results[0][1] if results else 'خطای نامشخص'
                        messages.error(request, f'خطا در ارسال ایمیل: {error_msg}')
                        logger.error(f"❌ Email sending failed by admin {request.user.username}: {error_msg}")

                    # Clear session
                    if 'selected_users' in request.session:
                        del request.session['selected_users']

                    return redirect('admin:users_user_changelist')

                except Exception as e:
                    error_msg = f'خطا در ارسال ایمیل: {str(e)}'
                    messages.error(request, error_msg)
                    logger.error(f"❌ Exception in admin email sending by {request.user.username}: {str(e)}")
                    logger.exception("Full exception details:")
            else:
                logger.warning(f"⚠️ Invalid form submission by {request.user.username}")
                logger.debug(f"Form errors: {form.errors}")
        else:
            form = EmailForm()
            logger.info(f"📋 Email form displayed to admin {request.user.username}")

        selected_users = request.session.get('selected_users', [])
        users = User.objects.filter(id__in=selected_users)

        # Add validation info to context
        valid_users, invalid_users = EmailValidator.validate_users(users)

        logger.debug(f"Form display: {len(valid_users)} valid, {len(invalid_users)} invalid users")

        return render(request, 'admin/send_email.html', {
            'form': form,
            'users': users,
            'valid_users': valid_users,
            'invalid_users': invalid_users,
            'title': 'ارسال ایمیل'
        })

# Register admins
admin.site.register(User, UserAdmin)

