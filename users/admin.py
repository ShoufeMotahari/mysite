from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth.models import Group

from .models import Profile, User, RegisterToken, VerificationToken
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter

# Unregister the default User admin if it exists
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    readonly_fields = ['created_jalali', 'updated_jalali']
    fieldsets = (
        (None, {
            'fields': ('image',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_jalali', 'updated_jalali'),
            'classes': ('collapse',)
        }),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]

    # Custom methods for better display
    def user_status(self, obj):
        """Show user status with colored badges"""
        statuses = []

        if obj.is_superuser:
            statuses.append(
                '<span style="background:#dc3545;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">سوپر ادمین</span>')
        elif obj.is_staff:
            statuses.append(
                '<span style="background:#007bff;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">کارمند</span>')
        else:
            statuses.append(
                '<span style="background:#6c757d;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">کاربر عادی</span>')

        if obj.is_active:
            statuses.append(
                '<span style="background:#28a745;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">فعال</span>')
        else:
            statuses.append(
                '<span style="background:#dc3545;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">غیرفعال</span>')

        return mark_safe(' '.join(statuses))

    user_status.short_description = 'وضعیت'
    user_status.admin_order_field = 'is_active'

    def verification_status(self, obj):
        """Show verification status with icons"""
        statuses = []

        if obj.is_phone_verified:
            statuses.append('<span style="color:#28a745;">📱 تلفن تایید شده</span>')
        else:
            statuses.append('<span style="color:#dc3545;">📱 تلفن تایید نشده</span>')

        if obj.is_email_verified:
            statuses.append('<span style="color:#28a745;">✉️ ایمیل تایید شده</span>')
        else:
            statuses.append('<span style="color:#dc3545;">✉️ ایمیل تایید نشده</span>')

        return mark_safe('<br>'.join(statuses))

    verification_status.short_description = 'وضعیت تایید'

    def profile_image_thumb(self, obj):
        """Show profile image thumbnail"""
        try:
            if obj.profile.image:
                return format_html(
                    '<img src="{}" width="40" height="40" style="border-radius: 50%; object-fit: cover;" />',
                    obj.profile.image.url
                )
        except:
            pass
        return format_html(
            '<div style="width:40px;height:40px;background:#f8f9fa;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;color:#6c757d;">بدون تصویر</div>')

    profile_image_thumb.short_description = 'تصویر پروفایل'

    def user_groups(self, obj):
        """Show user groups"""
        groups = obj.groups.all()
        if groups:
            group_list = [
                f'<span style="background:#17a2b8;color:white;padding:1px 4px;border-radius:2px;font-size:10px;">{group.name}</span>'
                for group in groups]
            return mark_safe(' '.join(group_list))
        return '-'

    user_groups.short_description = 'گروه‌ها'

    def last_login_display(self, obj):
        """Show last login with better formatting"""
        if obj.last_login:
            return obj.last_login.strftime('%Y/%m/%d %H:%M')
        return 'هرگز'

    last_login_display.short_description = 'آخرین ورود'
    last_login_display.admin_order_field = 'last_login'

    def registration_date(self, obj):
        """Show registration date"""
        if obj.date_joined:
            return obj.date_joined.strftime('%Y/%m/%d')
        return '-'

    registration_date.short_description = 'تاریخ ثبت‌نام'
    registration_date.admin_order_field = 'date_joined'

    # List display configuration
    list_display = [
        'profile_image_thumb',
        'username',
        'email',
        'mobile',
        'user_status',
        'verification_status',
        'user_groups',
        'last_login_display',
        'registration_date',
    ]

    # List filters
    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser',
        'is_phone_verified',
        'is_email_verified',
        'groups',
        ('date_joined', JDateFieldListFilter),
        ('last_login', JDateFieldListFilter),
    ]

    # Search fields
    search_fields = [
        'username',
        'email',
        'mobile',
        'first_name',
        'last_name',
        'slug',
    ]

    # Ordering
    ordering = ['-date_joined']

    # Fieldsets for detailed view
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('username', 'email', 'mobile', 'slug')
        }),
        ('اطلاعات شخصی', {
            'fields': ('first_name', 'last_name'),
            'classes': ('collapse',)
        }),
        ('دسترسی‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('وضعیت تایید', {
            'fields': ('is_phone_verified', 'is_email_verified'),
            'classes': ('collapse',)
        }),
        ('رمز عبور', {
            'fields': ('password', 'second_password'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('date_joined', 'last_login', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    # Add fieldsets for user creation
    add_fieldsets = (
        ('اطلاعات اصلی', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'mobile', 'password1', 'password2'),
        }),
        ('اطلاعات شخصی', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name'),
        }),
        ('دسترسی‌ها', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )

    # Read-only fields
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'slug']

    # Actions
    actions = [
        'activate_users',
        'deactivate_users',
        'mark_phone_verified',
        'mark_email_verified',
        'make_staff',
        'remove_staff',
    ]

    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} کاربر فعال شدند.')

    activate_users.short_description = 'فعال کردن کاربران انتخاب شده'

    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} کاربر غیرفعال شدند.')

    deactivate_users.short_description = 'غیرفعال کردن کاربران انتخاب شده'

    def mark_phone_verified(self, request, queryset):
        """Mark phone as verified"""
        updated = queryset.update(is_phone_verified=True)
        self.message_user(request, f'تلفن {updated} کاربر تایید شد.')

    mark_phone_verified.short_description = 'تایید شماره تلفن'

    def mark_email_verified(self, request, queryset):
        """Mark email as verified"""
        updated = queryset.update(is_email_verified=True)
        self.message_user(request, f'ایمیل {updated} کاربر تایید شد.')

    mark_email_verified.short_description = 'تایید ایمیل'

    def make_staff(self, request, queryset):
        """Make users staff"""
        updated = queryset.update(is_staff=True)
        self.message_user(request, f'{updated} کاربر به کارمند تبدیل شدند.')

    make_staff.short_description = 'تبدیل به کارمند'

    def remove_staff(self, request, queryset):
        """Remove staff status"""
        updated = queryset.update(is_staff=False)
        self.message_user(request, f'دسترسی کارمندی {updated} کاربر حذف شد.')

    remove_staff.short_description = 'حذف دسترسی کارمندی'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    def profile_image_display(self, obj):
        """Show profile image with better styling"""
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius: 10px; object-fit: cover; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        return format_html(
            '<div style="width:60px;height:60px;background:#f8f9fa;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:12px;color:#6c757d;border:2px dashed #dee2e6;">بدون تصویر</div>'
        )

    profile_image_display.short_description = 'تصویر پروفایل'

    def user_info(self, obj):
        """Show comprehensive user info"""
        user = obj.user
        info = f'<strong>{user.username or user.mobile or user.email}</strong><br>'

        if user.first_name or user.last_name:
            info += f'<span style="color:#6c757d;">{user.first_name} {user.last_name}</span><br>'

        if user.email:
            info += f'<span style="color:#007bff;">✉️ {user.email}</span><br>'

        if user.mobile:
            info += f'<span style="color:#28a745;">📱 {user.mobile}</span>'

        return mark_safe(info)

    user_info.short_description = 'اطلاعات کاربر'

    def user_status_display(self, obj):
        """Show user status"""
        user = obj.user
        statuses = []

        if user.is_superuser:
            statuses.append(
                '<span style="background:#dc3545;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">سوپر ادمین</span>')
        elif user.is_staff:
            statuses.append(
                '<span style="background:#007bff;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">کارمند</span>')
        else:
            statuses.append(
                '<span style="background:#6c757d;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">کاربر عادی</span>')

        if user.is_active:
            statuses.append(
                '<span style="background:#28a745;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">فعال</span>')
        else:
            statuses.append(
                '<span style="background:#dc3545;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">غیرفعال</span>')

        return mark_safe('<br>'.join(statuses))

    user_status_display.short_description = 'وضعیت کاربر'

    def verification_badges(self, obj):
        """Show verification badges"""
        user = obj.user
        badges = []

        if user.is_phone_verified:
            badges.append(
                '<span style="background:#28a745;color:white;padding:1px 4px;border-radius:2px;font-size:10px;">📱 تایید شده</span>')
        else:
            badges.append(
                '<span style="background:#dc3545;color:white;padding:1px 4px;border-radius:2px;font-size:10px;">📱 تایید نشده</span>')

        if user.is_email_verified:
            badges.append(
                '<span style="background:#28a745;color:white;padding:1px 4px;border-radius:2px;font-size:10px;">✉️ تایید شده</span>')
        else:
            badges.append(
                '<span style="background:#dc3545;color:white;padding:1px 4px;border-radius:2px;font-size:10px;">✉️ تایید نشده</span>')

        return mark_safe('<br>'.join(badges))

    verification_badges.short_description = 'تایید هویت'

    list_display = [
        'profile_image_display',
        'user_info',
        'user_status_display',
        'verification_badges',
        'created_jalali',
        'updated_jalali'
    ]

    list_filter = [
        'user__is_active',
        'user__is_staff',
        'user__is_superuser',
        'user__is_phone_verified',
        'user__is_email_verified',
        ('created_jalali', JDateFieldListFilter),
        ('updated_jalali', JDateFieldListFilter),
    ]

    search_fields = [
        'user__username',
        'user__email',
        'user__mobile',
        'user__first_name',
        'user__last_name',
        'user__slug'
    ]

    readonly_fields = ['created_jalali', 'updated_jalali']

    fieldsets = (
        ('اطلاعات پروفایل', {
            'fields': ('user', 'image')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_jalali', 'updated_jalali'),
            'classes': ('collapse',)
        }),
    )

    # Custom actions
    actions = ['delete_profile_images']

    def delete_profile_images(self, request, queryset):
        """Delete profile images"""
        count = 0
        for profile in queryset:
            if profile.image:
                profile.image.delete()
                count += 1
        self.message_user(request, f'{count} تصویر پروفایل حذف شد.')

    delete_profile_images.short_description = 'حذف تصاویر پروفایل'


@admin.register(RegisterToken)
class RegisterTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created', 'is_valid_display']
    list_filter = ['created']
    search_fields = ['user__username', 'user__email', 'user__mobile', 'code']
    readonly_fields = ['created']

    def is_valid_display(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ معتبر</span>')
        return format_html('<span style="color: red;">✗ منقضی</span>')

    is_valid_display.short_description = 'وضعیت'


@admin.register(VerificationToken)
class VerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_type', 'token', 'created_at', 'is_used', 'is_valid_display']
    list_filter = ['token_type', 'is_used', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__mobile', 'token']
    readonly_fields = ['created_at', 'email_token']

    def is_valid_display(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ معتبر</span>')
        return format_html('<span style="color: red;">✗ منقضی</span>')

    is_valid_display.short_description = 'وضعیت'

    fieldsets = (
        ('اطلاعات توکن', {
            'fields': ('user', 'token_type', 'token', 'email_token')
        }),
        ('وضعیت', {
            'fields': ('is_used', 'created_at')
        }),
    )


# Admin site customization
admin.site.site_header = 'پنل مدیریت'
admin.site.site_title = 'پنل مدیریت'
admin.site.index_title = 'خوش آمدید به پنل مدیریت'