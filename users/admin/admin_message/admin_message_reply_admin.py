import logging

from django.contrib import admin
from django_jalali.admin.filters import JDateFieldListFilter

from users.models.adminMessage import AdminMessageReply

logger = logging.getLogger(__name__)


@admin.register(AdminMessageReply)
class AdminMessageReplyAdmin(admin.ModelAdmin):
    """Admin for message replies"""

    list_display = ["original_message", "sender", "reply_preview", "created_at"]
    list_filter = [("created_at", JDateFieldListFilter), "sender"]
    search_fields = ["reply_text", "original_message__subject", "sender__username"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]

    def reply_preview(self, obj):
        """Show preview of reply text"""
        if not obj.reply_text:
            return "پاسخ خالی"

        preview = obj.reply_text[:100]
        if len(obj.reply_text) > 100:
            preview += "..."
        return preview

    reply_preview.short_description = "پیش‌نمایش پاسخ"

    def has_module_permission(self, request):
        """Only superusers can access this module"""
        return request.user.is_superuser
