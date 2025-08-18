import logging

from django.contrib import admin, messages
from django.db.models import Func, F
from django.utils import timezone
from django.utils.html import format_html
from django_jalali.admin.filters import JDateFieldListFilter

from users.admin.in_line.in_ilne import AdminMessageReplyInline, AdminMessageReadStatusInline
from users.models.adminMessage import AdminMessage

logger = logging.getLogger(__name__)


@admin.register(AdminMessage)
class AdminMessageAdmin(admin.ModelAdmin):
    """Admin interface for AdminMessage - Only visible to superusers"""

    list_display = [
        "subject",
        "sender_display",
        "priority_display",
        "status_display",
        "read_count",
        "created_at",
    ]

    list_filter = [
        "status",
        "priority",
        "sender",
        ("created_at", JDateFieldListFilter),
    ]

    search_fields = ["subject", "message", "sender__username", "sender__email"]

    readonly_fields = ["sender", "created_at", "read_at", "updated_at"]

    ordering = ["-created_at"]
    list_per_page = 25

    actions = ["mark_as_read", "mark_as_archived", "mark_as_unread"]

    inlines = [AdminMessageReplyInline, AdminMessageReadStatusInline]

    fieldsets = (
        ("اطلاعات پیام", {"fields": ("sender", "subject", "message", "priority")}),
        ("وضعیت", {"fields": ("status", "read_at")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'user', 'content_type'
        ).prefetch_related('content_object')
        # Optional: truncate microseconds
        return qs.annotate(
            created_at_no_microseconds=Func(F('created_at'), function='DATE_FORMAT',
                                            template="%(function)s(%(expressions)s,'%%Y-%%m-%%d %%H:%%i:%%s')")
        )

    def sender_display(self, obj):
        """Display sender with user type"""
        sender = obj.sender
        # Add safety check for sender existence
        if not sender:
            return format_html('<span style="color: #dc3545;">فرستنده حذف شده</span>')

        # Add safety check for user_type attribute
        try:
            type_name = (
                sender.get_user_type_display()
                if hasattr(sender, "user_type") and sender.user_type
                else "نامشخص"
            )
        except (AttributeError, ValueError):
            type_name = "نامشخص"

        # Add safety check for get_display_name method
        try:
            display_name = (
                sender.get_display_name()
                if hasattr(sender, "get_display_name")
                else str(sender)
            )
        except (AttributeError, ValueError):
            display_name = str(sender)

        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">{}</small>',
            display_name,
            type_name,
        )

    sender_display.short_description = "فرستنده"

    def priority_display(self, obj):
        """Display priority with color and icon"""
        # Add safety checks for priority methods
        try:
            color_class = (
                obj.get_priority_color() if hasattr(obj, "get_priority_color") else ""
            )
            icon = obj.get_priority_icon() if hasattr(obj, "get_priority_icon") else ""
            priority_text = (
                obj.get_priority_display()
                if hasattr(obj, "get_priority_display")
                else str(obj.priority)
            )
        except (AttributeError, ValueError):
            color_class = ""
            icon = ""
            priority_text = str(obj.priority) if obj.priority else "نامشخص"

        return format_html(
            '<span class="{}">{} {}</span>', color_class, icon, priority_text
        )

    priority_display.short_description = "اولویت"

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            "unread": "color: #d63384; font-weight: bold;",
            "read": "color: #198754;",
            "archived": "color: #6c757d;",
        }
        style = colors.get(obj.status, "")

        # Add safety check for get_status_display
        try:
            status_text = (
                obj.get_status_display()
                if hasattr(obj, "get_status_display")
                else str(obj.status)
            )
        except (AttributeError, ValueError):
            status_text = str(obj.status) if obj.status else "نامشخص"

        return format_html('<span style="{}">{}</span>', style, status_text)

    status_display.short_description = "وضعیت"

    def read_count(self, obj):
        """Show how many people have read the message"""
        try:
            count = getattr(obj, "read_count_num", None)
            if count is None:
                # Fallback to direct count if annotation failed
                count = obj.read_by.count() if hasattr(obj, "read_by") else 0
        except (AttributeError, ValueError):
            count = 0

        if count == 0:
            return format_html('<span style="color: #6c757d;">هیچ‌کس</span>')
        return format_html('<span style="color: #198754;">{} نفر</span>', count)

    read_count.short_description = "خوانده شده توسط"

    def mark_as_read(self, request, queryset):
        """Mark selected messages as read"""
        count = 0
        for message in queryset:
            try:
                if hasattr(message, "mark_as_read"):
                    message.mark_as_read(request.user)
                    count += 1
                else:
                    # Fallback method
                    message.status = "read"
                    message.read_at = timezone.now()
                    message.save()
                    count += 1
            except Exception as e:
                # Log error but continue with other messages
                self.message_user(
                    request,
                    f"خطا در علامت‌گذاری پیام {message.id}: {str(e)}",
                    messages.ERROR,
                )

        if count > 0:
            self.message_user(
                request,
                f"{count} پیام به عنوان خوانده شده علامت‌گذاری شد.",
                messages.SUCCESS,
            )

    mark_as_read.short_description = "علامت‌گذاری به عنوان خوانده شده"

    def mark_as_archived(self, request, queryset):
        """Archive selected messages"""
        try:
            updated = queryset.update(status="archived")
            self.message_user(request, f"{updated} پیام آرشیو شد.", messages.SUCCESS)
        except Exception as e:
            self.message_user(
                request, f"خطا در آرشیو کردن پیام‌ها: {str(e)}", messages.ERROR
            )

    mark_as_archived.short_description = "آرشیو کردن"

    def mark_as_unread(self, request, queryset):
        """Mark selected messages as unread"""
        try:
            updated = queryset.update(status="unread", read_at=None)
            self.message_user(
                request,
                f"{updated} پیام به عنوان خوانده نشده علامت‌گذاری شد.",
                messages.SUCCESS,
            )
        except Exception as e:
            self.message_user(
                request, f"خطا در علامت‌گذاری پیام‌ها: {str(e)}", messages.ERROR
            )

    mark_as_unread.short_description = "علامت‌گذاری به عنوان خوانده نشده"

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
            if hasattr(AdminMessage, "get_unread_count"):
                extra_context["unread_count"] = AdminMessage.get_unread_count()
            else:
                # Fallback to direct query
                extra_context["unread_count"] = AdminMessage.objects.filter(
                    status="unread"
                ).count()
        except Exception as e:
            # If there's an error, set count to 0
            extra_context["unread_count"] = 0

        return super().changelist_view(request, extra_context=extra_context)
