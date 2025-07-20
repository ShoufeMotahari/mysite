# users/admin.py - Enhanced User Admin Panel
from django.contrib import admin
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import path
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q, Exists, OuterRef
import logging

# Import models
from users.models import User, Profile, PasswordEntry, Comment
from emails.models import EmailTemplate

# Import forms and services
from users.forms.forms import EmailForm
from users.managers.email_manager import EmailManager, SendEmailCommand
from users.services.email_service import EmailValidator

# Import django-jalali admin components
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter

# Setup logging
logger = logging.getLogger('core')
password_logger = logging.getLogger(__name__)


class HasCommentsFilter(admin.SimpleListFilter):
    """Custom filter to show users with or without comments"""
    title = 'وضعیت نظرات'
    parameter_name = 'has_comments'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'دارای نظر'),
            ('no', 'بدون نظر'),
            ('approved', 'دارای نظر تایید شده'),
            ('pending', 'دارای نظر در انتظار تایید'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(comments__isnull=False).distinct()
        elif self.value() == 'no':
            return queryset.filter(comments__isnull=True).distinct()
        elif self.value() == 'approved':
            return queryset.filter(comments__is_approved=True).distinct()
        elif self.value() == 'pending':
            return queryset.filter(comments__is_approved=False).distinct()
        return queryset


class EmailStatusFilter(admin.SimpleListFilter):
    """Filter users by email validation status"""
    title = 'وضعیت ایمیل'
    parameter_name = 'email_status'

    def lookups(self, request, model_admin):
        return (
            ('valid', 'ایمیل معتبر'),
            ('invalid', 'ایمیل نامعتبر'),
            ('no_email', 'بدون ایمیل'),
            ('verified', 'ایمیل تایید شده'),
            ('unverified', 'ایمیل تایید نشده'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'valid':
            return queryset.exclude(email__isnull=True).exclude(email='')
        elif self.value() == 'invalid':
            return queryset.filter(Q(email__isnull=True) | Q(email=''))
        elif self.value() == 'no_email':
            return queryset.filter(Q(email__isnull=True) | Q(email=''))
        elif self.value() == 'verified':
            return queryset.filter(is_email_verified=True)
        elif self.value() == 'unverified':
            return queryset.filter(is_email_verified=False)
        return queryset


class CommentInline(admin.TabularInline):
    """Inline for user comments"""
    model = Comment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['content', 'is_approved', 'is_active', 'created_at', 'updated_at']

    def get_queryset(self, request):
        """Only show comments related to this user"""
        return super().get_queryset(request).select_related('user')


class ProfileInline(admin.StackedInline):
    """Inline for user profile"""
    model = Profile
    extra = 0
    readonly_fields = ['created_jalali', 'updated_jalali']
    fields = ['image', 'created_jalali', 'updated_jalali']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # List display with editable fields
    list_display = [
        'username', 'email', 'mobile', 'full_name_display',
        'is_active', 'is_staff', 'email_status', 'phone_status',
        'comments_count', 'last_login', 'created_at'
    ]

    # Enable editing in the list view
    list_editable = ['is_active', 'is_staff']

    # Comprehensive filters
    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser',
        'is_phone_verified',
        'is_email_verified',
        HasCommentsFilter,
        EmailStatusFilter,
        ('created_at', JDateFieldListFilter),
        ('last_login', JDateFieldListFilter),
    ]

    # Comprehensive search fields
    search_fields = [
        'username', 'email', 'mobile', 'first_name', 'last_name',
        'slug', 'comments__content'
    ]

    # Actions
    actions = ['send_email_action', 'activate_users', 'deactivate_users', 'verify_emails', 'verify_phones']

    # Pagination
    list_per_page = 50
    list_max_show_all = 200

    # Ordering
    ordering = ['-created_at']

    # Add inlines
    inlines = [ProfileInline, CommentInline]

    # Fieldsets for better organization in detail view
    fieldsets = (
        ('اطلاعات کاربری', {
            'fields': ('username', 'email', 'mobile', 'slug')
        }),
        ('اطلاعات شخصی', {
            'fields': ('first_name', 'last_name')
        }),
        ('رمز عبور', {
            'fields': ('password', 'second_password'),
            'classes': ('collapse',)
        }),
        ('مجوزها و وضعیت', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('وضعیت تایید', {
            'fields': ('is_phone_verified', 'is_email_verified')
        }),
        ('تاریخ‌ها', {
            'fields': ('last_login', 'date_joined', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'date_joined', 'last_login']

    # Optimize queries
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Annotate with comment count for efficiency
        queryset = queryset.annotate(
            comments_count_num=Count('comments'),
            approved_comments_count=Count('comments', filter=Q(comments__is_approved=True))
        )
        # Select related for efficiency
        queryset = queryset.select_related('profile')
        return queryset

    # Custom display methods
    def full_name_display(self, obj):
        """Display full name or fallback"""
        full_name = obj.get_full_name().strip()
        if full_name:
            return full_name
        return format_html('<em style="color: #888;">بدون نام</em>')

    full_name_display.short_description = 'نام کامل'

    def email_status(self, obj):
        """Display email validation status with colors"""
        if not obj.email:
            return format_html('<span style="color: #888; font-style: italic;">بدون ایمیل</span>')

        status_parts = []

        # Email verification status
        if obj.is_email_verified:
            status_parts.append('<span style="color: green;">✓ تایید شده</span>')
        else:
            status_parts.append('<span style="color: orange;">⚠ تایید نشده</span>')

        # Email validity
        try:
            EmailValidator.validate_email(obj.email)
            status_parts.append('<span style="color: green;">معتبر</span>')
        except ValidationError:
            status_parts.append('<span style="color: red;">نامعتبر</span>')

        return format_html(' | '.join(status_parts))

    email_status.short_description = 'وضعیت ایمیل'

    def phone_status(self, obj):
        """Display phone verification status"""
        if not obj.mobile:
            return format_html('<span style="color: #888; font-style: italic;">بدون شماره</span>')

        if obj.is_phone_verified:
            return format_html('<span style="color: green;">✓ تایید شده</span>')
        else:
            return format_html('<span style="color: orange;">⚠ تایید نشده</span>')

    phone_status.short_description = 'وضعیت تلفن'

    def comments_count(self, obj):
        """Display comment count with breakdown"""
        total = getattr(obj, 'comments_count_num', obj.comments.count())
        approved = getattr(obj, 'approved_comments_count', obj.comments.filter(is_approved=True).count())

        if total == 0:
            return format_html('<span style="color: #888;">بدون نظر</span>')

        pending = total - approved
        parts = [f'<strong>{total}</strong> کل']

        if approved > 0:
            parts.append(f'<span style="color: green;">{approved} تایید</span>')

        if pending > 0:
            parts.append(f'<span style="color: orange;">{pending} انتظار</span>')

        return format_html(' | '.join(parts))

    comments_count.short_description = 'نظرات'

    # Enhanced actions
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
        self.message_user(request, f'{updated} کاربر فعال شد.', level=messages.SUCCESS)

    activate_users.short_description = 'فعال کردن کاربران انتخاب شده'

    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        logger.info(f"👨‍💼 Admin {request.user.username} deactivated {updated} users")
        self.message_user(request, f'{updated} کاربر غیرفعال شد.', level=messages.SUCCESS)

    deactivate_users.short_description = 'غیرفعال کردن کاربران انتخاب شده'

    def verify_emails(self, request, queryset):
        """Verify emails for selected users"""
        updated = queryset.filter(email__isnull=False).exclude(email='').update(is_email_verified=True)
        logger.info(f"👨‍💼 Admin {request.user.username} verified emails for {updated} users")
        self.message_user(request, f'ایمیل {updated} کاربر تایید شد.', level=messages.SUCCESS)

    verify_emails.short_description = 'تایید ایمیل کاربران انتخاب شده'

    def verify_phones(self, request, queryset):
        """Verify phones for selected users"""
        updated = queryset.filter(mobile__isnull=False).exclude(mobile='').update(is_phone_verified=True)
        logger.info(f"👨‍💼 Admin {request.user.username} verified phones for {updated} users")
        self.message_user(request, f'شماره تلفن {updated} کاربر تایید شد.', level=messages.SUCCESS)

    verify_phones.short_description = 'تایید شماره تلفن کاربران انتخاب شده'

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


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Enhanced Comment admin"""
    list_display = ['user', 'content_preview', 'is_approved', 'is_active', 'created_at']
    list_editable = ['is_approved', 'is_active']
    list_filter = ['is_approved', 'is_active', ('created_at', JDateFieldListFilter)]
    search_fields = ['user__username', 'user__email', 'content']
    ordering = ['-created_at']
    list_per_page = 50

    actions = ['approve_comments', 'reject_comments', 'activate_comments', 'deactivate_comments']

    def content_preview(self, obj):
        """Show preview of comment content"""
        content = obj.content[:100]
        if len(obj.content) > 100:
            content += "..."
        return format_html('<span title="{}">{}</span>', obj.content, content)

    content_preview.short_description = 'متن نظر'

    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} نظر تایید شد.', level=messages.SUCCESS)

    approve_comments.short_description = 'تایید نظرات انتخاب شده'

    def reject_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} نظر رد شد.', level=messages.WARNING)

    reject_comments.short_description = 'رد نظرات انتخاب شده'

    def activate_comments(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} نظر فعال شد.', level=messages.SUCCESS)

    activate_comments.short_description = 'فعال کردن نظرات انتخاب شده'

    def deactivate_comments(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} نظر غیرفعال شد.', level=messages.WARNING)

    deactivate_comments.short_description = 'غیرفعال کردن نظرات انتخاب شده'


# Keep existing admin registrations for other models
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    def profile_image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="40" height="40" style="border-radius: 5px;" />', obj.image.url)
        return "بدون تصویر"

    profile_image_thumb.short_description = 'تصویر'

    list_display = ['user', 'profile_image_thumb', 'created_jalali', 'updated_jalali']
    list_filter = (('created_jalali', JDateFieldListFilter),)
    search_fields = ['user__username', 'user__email', 'user__mobile', 'user__slug']
    readonly_fields = ['created_jalali', 'updated_jalali']
    fieldsets = (
        (None, {'fields': ('user', 'image')}),
        ('تاریخ‌ها', {'fields': ('created_jalali', 'updated_jalali')}),
    )


@admin.register(PasswordEntry)
class PasswordEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'service_name', 'username', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'service_name', 'username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly_fields.append('password')  # Make password readonly when editing
        return readonly_fields

    def has_change_permission(self, request, obj=None):
        has_permission = request.user.is_superuser
        if obj:
            password_logger.info(
                f"Admin change permission check - User: {request.user.username}, Object: {obj.service_name}, Permission: {has_permission}")
        return has_permission

    def has_delete_permission(self, request, obj=None):
        has_permission = request.user.is_superuser
        if obj:
            password_logger.info(
                f"Admin delete permission check - User: {request.user.username}, Object: {obj.service_name}, Permission: {has_permission}")
        return has_permission

    def has_view_permission(self, request, obj=None):
        has_permission = request.user.is_superuser
        if obj:
            password_logger.info(
                f"Admin view permission check - User: {request.user.username}, Object: {obj.service_name}, Permission: {has_permission}")
        return has_permission

    def save_model(self, request, obj, form, change):
        if change:
            password_logger.info(
                f"Admin updating password entry - Admin: {request.user.username}, Entry: {obj.service_name}, User: {obj.user.username}")
        else:
            password_logger.info(
                f"Admin creating password entry - Admin: {request.user.username}, Entry: {obj.service_name}, User: {obj.user.username}")

        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        password_logger.info(
            f"Admin deleting password entry - Admin: {request.user.username}, Entry: {obj.service_name}, User: {obj.user.username}")
        super().delete_model(request, obj)

    def changelist_view(self, request, extra_context=None):
        password_logger.info(f"Admin changelist accessed - Admin: {request.user.username}")
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if object_id:
            password_logger.info(f"Admin change form accessed - Admin: {request.user.username}, Object ID: {object_id}")
        else:
            password_logger.info(f"Admin add form accessed - Admin: {request.user.username}")
        return super().changeform_view(request, object_id, form_url, extra_context)


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


# Customize admin site
admin.site.site_header = 'پنل مدیریت'
admin.site.site_title = 'پنل مدیریت'
admin.site.index_title = 'خوش آمدید به پنل مدیریت'