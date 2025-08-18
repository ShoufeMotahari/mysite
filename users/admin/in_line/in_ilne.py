import logging
from django.contrib import admin
from users.models.adminMessage import AdminMessageReply, AdminMessageReadStatus
logger = logging.getLogger(__name__)


class AdminMessageReadStatusInline(admin.TabularInline):
    """Inline for showing who has read the message"""

    model = AdminMessageReadStatus
    extra = 0
    readonly_fields = ["user", "read_at"]

    def has_add_permission(self, request, obj=None):
        return False


class AdminMessageReplyInline(admin.TabularInline):
    """Inline for message replies"""

    model = AdminMessageReply
    extra = 0
    readonly_fields = ["sender", "created_at"]
    fields = ["sender", "reply_text", "created_at"]
