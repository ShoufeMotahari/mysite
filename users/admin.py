# users/admin.py - Enhanced User Admin Panel with User Types
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
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
import logging

# Import models
from users.models import User, Profile, PasswordEntry, Comment, UserType,AdminMessage,AdminMessageReadStatus
from emails.models import EmailTemplate

# Import forms and services
from users.forms.forms import EmailForm
from users.managers.email_manager import EmailManager, SendEmailCommand
from users.services.email_service import EmailValidator

# Import django-jalali admin components
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter

# Setup logging
logger = logging.getLogger('users')
password_logger = logging.getLogger(__name__)


class UserTypeFilter(admin.SimpleListFilter):
    """Filter users by user type"""
    title = 'نوع کاربری'
    parameter_name = 'user_type'

    def lookups(self, request, model_admin):
        user_types = UserType.objects.filter(is_active=True)
        return [(ut.id, ut.name) for ut in user_types] + [('none', 'بدون نوع')]

    def queryset(self, request, queryset):
        if self.value() == 'none':
            return queryset.filter(user_type__isnull=True)
        elif self.value():
            return queryset.filter(user_type_id=self.value())
        return queryset


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


@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    """Admin for User Types"""
    list_display = [
        'name', 'slug', 'permissions_summary', 'limits_summary',
        'users_count', 'is_active', 'is_default', 'created_at'
    ]
    list_editable = ['is_active']
    list_filter = ['is_active', 'is_default', 'can_access_admin', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'slug', 'description', 'is_active', 'is_default')
        }),
        ('مجوزهای محتوا', {
            'fields': ('can_create_content', 'can_edit_content', 'can_delete_content')
        }),
        ('مجوزهای مدیریتی', {
            'fields': ('can_manage_users', 'can_view_analytics', 'can_access_admin')
        }),
        ('محدودیت‌های محتوا', {
            'fields': ('max_posts_per_day', 'max_comments_per_day', 'max_file_upload_size_mb')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['activate_user_types', 'deactivate_user_types', 'create_predefined_types']

    def get_queryset(self, request):
        """Annotate with user count"""
        return super().get_queryset(request).annotate(
            users_count_num=Count('user')
        )

    def permissions_summary(self, obj):
        """Show a summary of permissions"""
        perms = []
        if obj.can_create_content:
            perms.append('<span style="color: green;">ایجاد</span>')
        if obj.can_edit_content:
            perms.append('<span style="color: blue;">ویرایش</span>')
        if obj.can_delete_content:
            perms.append('<span style="color: red;">حذف</span>')
        if obj.can_manage_users:
            perms.append('<span style="color: purple;">مدیریت کاربران</span>')
        if obj.can_view_analytics:
            perms.append('<span style="color: orange;">آمار</span>')
        if obj.can_access_admin:
            perms.append('<span style="color: darkred; font-weight: bold;">ادمین</span>')

        return format_html(' | '.join(perms)) if perms else format_html('<em style="color: #888;">بدون مجوز</em>')

    permissions_summary.short_description = 'مجوزها'

    def limits_summary(self, obj):
        """Show content limits summary"""
        limits = []
        if obj.max_posts_per_day:
            limits.append(f'{obj.max_posts_per_day} پست/روز')
        if obj.max_comments_per_day:
            limits.append(f'{obj.max_comments_per_day} نظر/روز')
        if obj.max_file_upload_size_mb:
            limits.append(f'{obj.max_file_upload_size_mb}MB فایل')

        return ', '.join(limits) if limits else 'بدون محدودیت'

    limits_summary.short_description = 'محدودیت‌ها'

    def users_count(self, obj):
        """Show number of users with this type"""
        count = getattr(obj, 'users_count_num', obj.user_set.count())
        if count == 0:
            return format_html('<span style="color: #888;">0</span>')
        return format_html(f'<strong>{count}</strong>')

    users_count.short_description = 'تعداد کاربران'

    def activate_user_types(self, request, queryset):
        """Activate selected user types"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} نوع کاربری فعال شد.', level=messages.SUCCESS)

    activate_user_types.short_description = 'فعال کردن انواع کاربری انتخاب شده'

    def deactivate_user_types(self, request, queryset):
        """Deactivate selected user types"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} نوع کاربری غیرفعال شد.', level=messages.WARNING)

    deactivate_user_types.short_description = 'غیرفعال کردن انواع کاربری انتخاب شده'

    def create_predefined_types(self, request, queryset):
        """Create predefined user types"""
        predefined_types = [
            {
                'name': 'مدیر سیستم',
                'slug': 'admin',
                'description': 'دسترسی کامل به سیستم',
                'can_create_content': True,
                'can_edit_content': True,
                'can_delete_content': True,
                'can_manage_users': True,
                'can_view_analytics': True,
                'can_access_admin': True,
                'max_file_upload_size_mb': 100,
            },
            {
                'name': 'مدیر محتوا',
                'slug': 'manager',
                'description': 'مدیریت محتوا و کاربران',
                'can_create_content': True,
                'can_edit_content': True,
                'can_delete_content': True,
                'can_manage_users': True,
                'can_view_analytics': True,
                'can_access_admin': True,
                'max_posts_per_day': 50,
                'max_comments_per_day': 100,
                'max_file_upload_size_mb': 50,
            },
            {
                'name': 'ویرایشگر',
                'slug': 'editor',
                'description': 'ویرایش و مدیریت محتوا',
                'can_create_content': True,
                'can_edit_content': True,
                'can_delete_content': False,
                'can_manage_users': False,
                'can_view_analytics': True,
                'can_access_admin': True,
                'max_posts_per_day': 30,
                'max_comments_per_day': 50,
                'max_file_upload_size_mb': 25,
            },
            {
                'name': 'نویسنده',
                'slug': 'author',
                'description': 'ایجاد و ویرایش محتوای شخصی',
                'can_create_content': True,
                'can_edit_content': True,
                'can_delete_content': False,
                'can_manage_users': False,
                'can_view_analytics': False,
                'can_access_admin': False,
                'max_posts_per_day': 10,
                'max_comments_per_day': 30,
                'max_file_upload_size_mb': 15,
            },
            {
                'name': 'مشترک',
                'slug': 'subscriber',
                'description': 'کاربر عادی سیستم',
                'can_create_content': False,
                'can_edit_content': False,
                'can_delete_content': False,
                'can_manage_users': False,
                'can_view_analytics': False,
                'can_access_admin': False,
                'max_posts_per_day': 0,
                'max_comments_per_day': 10,
                'max_file_upload_size_mb': 5,
                'is_default': True,
            }
        ]

        created_count = 0
        for type_data in predefined_types:
            user_type, created = UserType.objects.get_or_create(
                slug=type_data['slug'],
                defaults=type_data
            )
            if created:
                created_count += 1

        if created_count > 0:
            self.message_user(
                request,
                f'{created_count} نوع کاربری پیش‌فرض ایجاد شد.',
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'تمام انواع کاربری پیش‌فرض از قبل وجود دارند.',
                level=messages.INFO
            )

    create_predefined_types.short_description = 'ایجاد انواع کاربری پیش‌فرض'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # List display with user types
    list_display = [
        'username', 'email', 'mobile', 'full_name_display', 'user_type_display',
        'is_active', 'is_staff', 'email_status', 'phone_status',
        'comments_count', 'last_login', 'created_at'
    ]

    # Enable editing in the list view
    list_editable = ['is_active', 'is_staff']

    # Comprehensive filters including user type
    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser',
        UserTypeFilter,
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
        'slug', 'comments__content', 'user_type__name'
    ]

    # Enhanced actions
    actions = [
        'send_email_action', 'activate_users', 'deactivate_users',
        'verify_emails', 'verify_phones', 'change_user_type_action',
        'promote_to_staff', 'demote_from_staff'
    ]

    # Pagination
    list_per_page = 50
    list_max_show_all = 200

    # Ordering
    ordering = ['-created_at']

    # Add inlines
    inlines = [ProfileInline, CommentInline]

    # Enhanced fieldsets for better organization
    fieldsets = (
        ('اطلاعات کاربری', {
            'fields': ('username', 'email', 'mobile', 'slug')
        }),
        ('اطلاعات شخصی', {
            'fields': ('first_name', 'last_name', 'bio', 'birth_date')
        }),
        ('نوع کاربری و دسترسی', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser'),
            'description': 'نوع کاربری تعیین کننده سطح دسترسی کاربر است'
        }),
        ('وضعیت تایید', {
            'fields': ('is_phone_verified', 'is_email_verified')
        }),
        ('مجوزها', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('آمار فعالیت', {
            'fields': ('posts_count', 'comments_count', 'last_activity'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('last_login', 'date_joined', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'date_joined', 'last_login', 'last_activity', 'posts_count', 'comments_count']

    # Optimize queries
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Annotate with comment count for efficiency
        queryset = queryset.annotate(
            comments_count_num=Count('comments'),
            approved_comments_count=Count('comments', filter=Q(comments__is_approved=True))
        )
        # Select related for efficiency
        queryset = queryset.select_related('profile', 'user_type')
        return queryset

    # Custom display methods
    def full_name_display(self, obj):
        """Display full name or fallback"""
        full_name = obj.get_full_name().strip()
        if full_name:
            return full_name
        return format_html('<em style="color: #888;">بدون نام</em>')

    full_name_display.short_description = 'نام کامل'

    def user_type_display(self, obj):
        """Display user type with color coding"""
        if not obj.user_type:
            return format_html('<em style="color: #888;">نامشخص</em>')

        # Color code based on permissions
        if obj.user_type.can_access_admin:
            color = 'darkred'
            weight = 'bold'
        elif obj.user_type.can_manage_users:
            color = 'purple'
            weight = 'bold'
        elif obj.user_type.can_create_content:
            color = 'green'
            weight = 'normal'
        else:
            color = 'blue'
            weight = 'normal'

        return format_html(
            '<span style="color: {}; font-weight: {};">{}</span>',
            color, weight, obj.user_type.name
        )

    user_type_display.short_description = 'نوع کاربری'

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
        self.message_user(request, f'{updated} کاربر غیرفعال شد.', level=messages.WARNING)

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

    def change_user_type_action(self, request, queryset):
        """Change user type for selected users"""
        selected = queryset.values_list('id', flat=True)
        request.session['selected_users_for_type_change'] = list(selected)
        return HttpResponseRedirect(reverse('admin:change_user_type'))

    change_user_type_action.short_description = 'تغییر نوع کاربری کاربران انتخاب شده'

    def promote_to_staff(self, request, queryset):
        """Promote users to staff status"""
        updated = queryset.update(is_staff=True)
        logger.info(f"👨‍💼 Admin {request.user.username} promoted {updated} users to staff")
        self.message_user(request, f'{updated} کاربر به عضو کادر ارتقا یافت.', level=messages.SUCCESS)

    promote_to_staff.short_description = 'ارتقا به عضو کادر'

    def demote_from_staff(self, request, queryset):
        """Demote users from staff status"""
        updated = queryset.update(is_staff=False)
        logger.info(f"👨‍💼 Admin {request.user.username} demoted {updated} users from staff")
        self.message_user(request, f'{updated} کاربر از عضویت کادر خارج شد.', level=messages.WARNING)

    demote_from_staff.short_description = 'خروج از عضویت کادر'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-email/', self.send_email_view, name='send_email'),
            path('send-email-all/', self.send_email_all_view, name='send_email_all'),
            path('change-user-type/', self.change_user_type_view, name='change_user_type'),
            path('create-user-with-type/', self.create_user_with_type_view, name='create_user_with_type'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add custom buttons"""
        extra_context = extra_context or {}
        extra_context['show_send_all_email_button'] = True
        extra_context['show_create_user_with_type_button'] = True
        extra_context['user_types'] = UserType.objects.filter(is_active=True)
        return super().changelist_view(request, extra_context=extra_context)

    def create_user_with_type_view(self, request):
        """Create user with specific type"""
        if request.method == 'POST':
            return self._handle_create_user_post(request)
        else:
            return self._handle_create_user_get(request)

    def _handle_create_user_get(self, request):
        """Handle GET request for create user form"""
        user_types = UserType.objects.filter(is_active=True)
        context = {
            'title': 'ایجاد کاربر با نوع مشخص',
            'user_types': user_types,
        }
        return render(request, 'admin/create_user_with_type.html', context)

    def _handle_create_user_post(self, request):
        """Handle POST request for create user"""
        try:
            # Get form data
            username = request.POST.get('username')
            email = request.POST.get('email')
            mobile = request.POST.get('mobile')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            user_type_id = request.POST.get('user_type')
            password = request.POST.get('password')
            is_active = request.POST.get('is_active') == 'on'
            is_staff = request.POST.get('is_staff') == 'on'

            # Validation
            if not any([username, email, mobile]):
                messages.error(request, 'حداقل یکی از فیلدهای نام کاربری، ایمیل یا موبایل باید پر شود.')
                return self._handle_create_user_get(request)

            if not password:
                messages.error(request, 'رمز عبور الزامی است.')
                return self._handle_create_user_get(request)

            # Get user type
            user_type = None
            if user_type_id:
                try:
                    user_type = UserType.objects.get(id=user_type_id, is_active=True)
                except UserType.DoesNotExist:
                    messages.error(request, 'نوع کاربری انتخاب شده معتبر نیست.')
                    return self._handle_create_user_get(request)

            # Create user
            user = User.objects.create_user(
                username=username or None,
                email=email or None,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=is_active,
                is_staff=is_staff,
            )

            # Set additional fields
            if mobile:
                user.mobile = mobile
            if user_type:
                user.user_type = user_type

            user.save()

            # Create profile
            Profile.objects.get_or_create(user=user)

            logger.info(
                f"👨‍💼 Admin {request.user.username} created user: {user.get_display_name()} with type: {user_type.name if user_type else 'None'}")

            messages.success(
                request,
                f'کاربر {user.get_display_name()} با نوع کاربری "{user_type.name if user_type else "پیش‌فرض"}" ایجاد شد.'
            )
            return redirect('admin:users_user_changelist')

        except Exception as e:
            logger.error(f"❌ Error creating user by admin {request.user.username}: {str(e)}")
            messages.error(request, f'خطا در ایجاد کاربر: {str(e)}')
            return self._handle_create_user_get(request)

    def change_user_type_view(self, request):
        """Change user type for selected users"""
        if request.method == 'POST':
            return self._handle_change_type_post(request)
        else:
            return self._handle_change_type_get(request)

    def _handle_change_type_get(self, request):
        """Handle GET request for change type form"""
        selected_users = request.session.get('selected_users_for_type_change', [])
        if not selected_users:
            messages.error(request, 'هیچ کاربری انتخاب نشده است.')
            return redirect('admin:users_user_changelist')

        users = User.objects.filter(id__in=selected_users)
        user_types = UserType.objects.filter(is_active=True)

        context = {
            'title': 'تغییر نوع کاربری',
            'users': users,
            'user_types': user_types,
            'total_users': len(users),
        }
        return render(request, 'admin/change_user_type.html', context)

    def _handle_change_type_post(self, request):
        """Handle POST request for change type"""
        try:
            selected_users = request.session.get('selected_users_for_type_change', [])
            new_type_id = request.POST.get('user_type')

            if not selected_users:
                messages.error(request, 'هیچ کاربری انتخاب نشده است.')
                return redirect('admin:users_user_changelist')

            # Get new user type
            new_type = None
            if new_type_id:
                try:
                    new_type = UserType.objects.get(id=new_type_id, is_active=True)
                except UserType.DoesNotExist:
                    messages.error(request, 'نوع کاربری انتخاب شده معتبر نیست.')
                    return self._handle_change_type_get(request)

            # Update users
            users = User.objects.filter(id__in=selected_users)
            updated_count = 0

            for user in users:
                old_type = user.user_type
                user.user_type = new_type

                # Auto-update staff status based on new type
                if new_type and new_type.can_access_admin:
                    user.is_staff = True
                elif old_type and old_type.can_access_admin and new_type and not new_type.can_access_admin:
                    user.is_staff = False

                user.save()
                updated_count += 1

                logger.info(
                    f"👨‍💼 Admin {request.user.username} changed user type for {user.get_display_name()} from {old_type.name if old_type else 'None'} to {new_type.name if new_type else 'None'}")

            # Clear session
            if 'selected_users_for_type_change' in request.session:
                del request.session['selected_users_for_type_change']

            type_name = new_type.name if new_type else 'پیش‌فرض'
            messages.success(
                request,
                f'نوع کاربری {updated_count} کاربر به "{type_name}" تغییر کرد.'
            )
            return redirect('admin:users_user_changelist')

        except Exception as e:
            logger.error(f"❌ Error changing user types by admin {request.user.username}: {str(e)}")
            messages.error(request, f'خطا در تغییر نوع کاربری: {str(e)}')
            return self._handle_change_type_get(request)

    # Keep existing email methods from original admin
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


# messaging/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter

from .models import AdminMessage, AdminMessageReadStatus, AdminMessageReply

# messaging/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter

from .models import AdminMessage, AdminMessageReadStatus, AdminMessageReply


class AdminMessageReadStatusInline(admin.TabularInline):
    """Inline for showing who has read the message"""
    model = AdminMessageReadStatus
    extra = 0
    readonly_fields = ['user', 'read_at']

    def has_add_permission(self, request, obj=None):
        return False


class AdminMessageReplyInline(admin.TabularInline):
    """Inline for message replies"""
    model = AdminMessageReply
    extra = 0
    readonly_fields = ['sender', 'created_at']
    fields = ['sender', 'reply_text', 'created_at']


@admin.register(AdminMessage)
class AdminMessageAdmin(admin.ModelAdmin):
    """Admin interface for AdminMessage - Only visible to superusers"""

    list_display = [
        'subject', 'sender_display', 'priority_display', 'status_display',
        'read_count', 'created_at'
    ]

    list_filter = [
        'status', 'priority', 'sender',
        ('created_at', JDateFieldListFilter),
    ]

    search_fields = ['subject', 'message', 'sender__username', 'sender__email']

    readonly_fields = ['sender', 'created_at', 'read_at', 'updated_at']

    ordering = ['-created_at']
    list_per_page = 25

    actions = ['mark_as_read', 'mark_as_archived', 'mark_as_unread']

    inlines = [AdminMessageReplyInline, AdminMessageReadStatusInline]

    fieldsets = (
        ('اطلاعات پیام', {
            'fields': ('sender', 'subject', 'message', 'priority')
        }),
        ('وضعیت', {
            'fields': ('status', 'read_at')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        """Add annotations for efficient queries"""
        return super().get_queryset(request).annotate(
            read_count_num=Count('read_by', distinct=True)
        ).select_related('sender')

    def sender_display(self, obj):
        """Display sender with user type"""
        sender = obj.sender
        # Add safety check for sender existence
        if not sender:
            return format_html('<span style="color: #dc3545;">فرستنده حذف شده</span>')

        # Add safety check for user_type attribute
        try:
            type_name = sender.get_user_type_display() if hasattr(sender,
                                                                  'user_type') and sender.user_type else 'نامشخص'
        except (AttributeError, ValueError):
            type_name = 'نامشخص'

        # Add safety check for get_display_name method
        try:
            display_name = sender.get_display_name() if hasattr(sender, 'get_display_name') else str(sender)
        except (AttributeError, ValueError):
            display_name = str(sender)

        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">{}</small>',
            display_name,
            type_name
        )

    sender_display.short_description = 'فرستنده'

    def priority_display(self, obj):
        """Display priority with color and icon"""
        # Add safety checks for priority methods
        try:
            color_class = obj.get_priority_color() if hasattr(obj, 'get_priority_color') else ''
            icon = obj.get_priority_icon() if hasattr(obj, 'get_priority_icon') else ''
            priority_text = obj.get_priority_display() if hasattr(obj, 'get_priority_display') else str(obj.priority)
        except (AttributeError, ValueError):
            color_class = ''
            icon = ''
            priority_text = str(obj.priority) if obj.priority else 'نامشخص'

        return format_html(
            '<span class="{}">{} {}</span>',
            color_class,
            icon,
            priority_text
        )

    priority_display.short_description = 'اولویت'

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'unread': 'color: #d63384; font-weight: bold;',
            'read': 'color: #198754;',
            'archived': 'color: #6c757d;'
        }
        style = colors.get(obj.status, '')

        # Add safety check for get_status_display
        try:
            status_text = obj.get_status_display() if hasattr(obj, 'get_status_display') else str(obj.status)
        except (AttributeError, ValueError):
            status_text = str(obj.status) if obj.status else 'نامشخص'

        return format_html(
            '<span style="{}">{}</span>',
            style,
            status_text
        )

    status_display.short_description = 'وضعیت'

    def read_count(self, obj):
        """Show how many people have read the message"""
        try:
            count = getattr(obj, 'read_count_num', None)
            if count is None:
                # Fallback to direct count if annotation failed
                count = obj.read_by.count() if hasattr(obj, 'read_by') else 0
        except (AttributeError, ValueError):
            count = 0

        if count == 0:
            return format_html('<span style="color: #6c757d;">هیچ‌کس</span>')
        return format_html('<span style="color: #198754;">{} نفر</span>', count)

    read_count.short_description = 'خوانده شده توسط'

    def mark_as_read(self, request, queryset):
        """Mark selected messages as read"""
        count = 0
        for message in queryset:
            try:
                if hasattr(message, 'mark_as_read'):
                    message.mark_as_read(request.user)
                    count += 1
                else:
                    # Fallback method
                    message.status = 'read'
                    message.read_at = timezone.now()
                    message.save()
                    count += 1
            except Exception as e:
                # Log error but continue with other messages
                self.message_user(
                    request,
                    f'خطا در علامت‌گذاری پیام {message.id}: {str(e)}',
                    messages.ERROR
                )

        if count > 0:
            self.message_user(
                request,
                f'{count} پیام به عنوان خوانده شده علامت‌گذاری شد.',
                messages.SUCCESS
            )

    mark_as_read.short_description = 'علامت‌گذاری به عنوان خوانده شده'

    def mark_as_archived(self, request, queryset):
        """Archive selected messages"""
        try:
            updated = queryset.update(status='archived')
            self.message_user(
                request,
                f'{updated} پیام آرشیو شد.',
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                f'خطا در آرشیو کردن پیام‌ها: {str(e)}',
                messages.ERROR
            )

    mark_as_archived.short_description = 'آرشیو کردن'

    def mark_as_unread(self, request, queryset):
        """Mark selected messages as unread"""
        try:
            updated = queryset.update(status='unread', read_at=None)
            self.message_user(
                request,
                f'{updated} پیام به عنوان خوانده نشده علامت‌گذاری شد.',
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                f'خطا در علامت‌گذاری پیام‌ها: {str(e)}',
                messages.ERROR
            )

    mark_as_unread.short_description = 'علامت‌گذاری به عنوان خوانده نشده'

    def has_module_permission(self, request):
        """Only superusers can access this module"""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """Only superusers can view messages"""
        return request.user.is_superuser

    def has_add_permission(self, request):
        """Superusers cannot add messages from admin (they come from message admins)"""
        return False

    def has_change_permission(self, request, obj=None):
        """Superusers can change status and add replies"""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete messages"""
        return request.user.is_superuser

    def changelist_view(self, request, extra_context=None):
        """Add notification count to changelist"""
        extra_context = extra_context or {}
        try:
            # Add safety check for get_unread_count method
            if hasattr(AdminMessage, 'get_unread_count'):
                extra_context['unread_count'] = AdminMessage.get_unread_count()
            else:
                # Fallback to direct query
                extra_context['unread_count'] = AdminMessage.objects.filter(status='unread').count()
        except Exception as e:
            # If there's an error, set count to 0
            extra_context['unread_count'] = 0

        return super().changelist_view(request, extra_context=extra_context)


@admin.register(AdminMessageReply)
class AdminMessageReplyAdmin(admin.ModelAdmin):
    """Admin for message replies"""

    list_display = ['original_message', 'sender', 'reply_preview', 'created_at']
    list_filter = [('created_at', JDateFieldListFilter), 'sender']
    search_fields = ['reply_text', 'original_message__subject', 'sender__username']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def reply_preview(self, obj):
        """Show preview of reply text"""
        if not obj.reply_text:
            return 'پاسخ خالی'

        preview = obj.reply_text[:100]
        if len(obj.reply_text) > 100:
            preview += "..."
        return preview

    reply_preview.short_description = 'پیش‌نمایش پاسخ'

    def has_module_permission(self, request):
        """Only superusers can access this module"""
        return request.user.is_superuser
# Customize admin site
admin.site.site_header = 'پنل مدیریت'
admin.site.site_title = 'پنل مدیریت'
admin.site.index_title = 'خوش آمدید به پنل مدیریت'