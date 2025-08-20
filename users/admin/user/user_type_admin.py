import logging
from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html

from users.models.user.user_type import UserType

logger = logging.getLogger(__name__)

@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    """Admin for User Types"""

    list_display = [
        "name",
        "slug",
        "permissions_summary",
        "limits_summary",
        "users_count",
        "is_active",
        "is_default",
        "created_at",
    ]
    list_editable = ["is_active"]
    list_filter = ["is_active", "is_default", "can_access_admin", "created_at"]
    search_fields = ["name", "slug", "description"]
    readonly_fields = ["created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (
            "اطلاعات پایه",
            {"fields": ("name", "slug", "description", "is_active", "is_default")},
        ),
        (
            "مجوزهای محتوا",
            {
                "fields": (
                    "can_create_content",
                    "can_edit_content",
                    "can_delete_content",
                )
            },
        ),
        (
            "مجوزهای مدیریتی",
            {"fields": ("can_manage_users", "can_view_analytics", "can_access_admin")},
        ),
        (
            "محدودیت‌های محتوا",
            {
                "fields": (
                    "max_posts_per_day",
                    "max_comments_per_day",
                    "max_file_upload_size_mb",
                )
            },
        ),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = [
        "activate_user_types",
        "deactivate_user_types",
        "create_predefined_types",
    ]

    def get_queryset(self, request):
        """Annotate with user count"""
        return super().get_queryset(request).annotate(users_count_num=Count("user"))

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
            perms.append(
                '<span style="color: darkred; font-weight: bold;">ادمین</span>'
            )

        return (
            format_html(" | ".join(perms))
            if perms
            else format_html('<em style="color: #888;">بدون مجوز</em>')
        )

    permissions_summary.short_description = "مجوزها"

    def limits_summary(self, obj):
        """Show content limits summary"""
        limits = []
        if obj.max_posts_per_day:
            limits.append(f"{obj.max_posts_per_day} پست/روز")
        if obj.max_comments_per_day:
            limits.append(f"{obj.max_comments_per_day} نظر/روز")
        if obj.max_file_upload_size_mb:
            limits.append(f"{obj.max_file_upload_size_mb}MB فایل")

        return ", ".join(limits) if limits else "بدون محدودیت"

    limits_summary.short_description = "محدودیت‌ها"

    def users_count(self, obj):
        """Show number of users with this type"""
        count = getattr(obj, "users_count_num", obj.user_set.count())
        if count == 0:
            return format_html('<span style="color: #888;">0</span>')
        return format_html(f"<strong>{count}</strong>")

    users_count.short_description = "تعداد کاربران"

    def activate_user_types(self, request, queryset):
        """Activate selected user types"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, f"{updated} نوع کاربری فعال شد.", level=messages.SUCCESS
        )

    activate_user_types.short_description = "فعال کردن انواع کاربری انتخاب شده"

    def deactivate_user_types(self, request, queryset):
        """Deactivate selected user types"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, f"{updated} نوع کاربری غیرفعال شد.", level=messages.WARNING
        )

    deactivate_user_types.short_description = "غیرفعال کردن انواع کاربری انتخاب شده"

    def create_predefined_types(self, request, queryset):
        """Create predefined user types"""
        predefined_types = [
            {
                "name": "مدیر سیستم",
                "slug": "admin",
                "description": "دسترسی کامل به سیستم",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": True,
                "can_manage_users": True,
                "can_view_analytics": True,
                "can_access_admin": True,
                "max_file_upload_size_mb": 100,
            },
            {
                "name": "مدیر محتوا",
                "slug": "manager",
                "description": "مدیریت محتوا و کاربران",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": True,
                "can_manage_users": True,
                "can_view_analytics": True,
                "can_access_admin": True,
                "max_posts_per_day": 50,
                "max_comments_per_day": 100,
                "max_file_upload_size_mb": 50,
            },
            {
                "name": "ویرایشگر",
                "slug": "editor",
                "description": "ویرایش و مدیریت محتوا",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": False,
                "can_manage_users": False,
                "can_view_analytics": True,
                "can_access_admin": True,
                "max_posts_per_day": 30,
                "max_comments_per_day": 50,
                "max_file_upload_size_mb": 25,
            },
            {
                "name": "نویسنده",
                "slug": "author",
                "description": "ایجاد و ویرایش محتوای شخصی",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": False,
                "can_manage_users": False,
                "can_view_analytics": False,
                "can_access_admin": False,
                "max_posts_per_day": 10,
                "max_comments_per_day": 30,
                "max_file_upload_size_mb": 15,
            },
            {
                "name": "مشترک",
                "slug": "subscriber",
                "description": "کاربر عادی سیستم",
                "can_create_content": False,
                "can_edit_content": False,
                "can_delete_content": False,
                "can_manage_users": False,
                "can_view_analytics": False,
                "can_access_admin": False,
                "max_posts_per_day": 0,
                "max_comments_per_day": 10,
                "max_file_upload_size_mb": 5,
                "is_default": True,
            },
        ]

        created_count = 0
        for type_data in predefined_types:
            user_type, created = UserType.objects.get_or_create(
                slug=type_data["slug"], defaults=type_data
            )
            if created:
                created_count += 1

        if created_count > 0:
            self.message_user(
                request,
                f"{created_count} نوع کاربری پیش‌فرض ایجاد شد.",
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "تمام انواع کاربری پیش‌فرض از قبل وجود دارند.",
                level=messages.INFO,
            )

    create_predefined_types.short_description = "ایجاد انواع کاربری پیش‌فرض"
