import logging
from django.contrib import admin
from django_jalali.admin.filters import JDateFieldListFilter

from users.models.emailTemplate import EmailTemplate

logger = logging.getLogger(__name__)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active", ("created_at", JDateFieldListFilter)]
    search_fields = ["name", "subject"]
    readonly_fields = ["created_at", "updated_at"]

    # Add fieldsets for better organization
    fieldsets = (
        (None, {"fields": ("name", "subject", "content", "is_active")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        if change:
            logger.info(
                f"📝 Email template updated: '{obj.name}' by {request.user.username}"
            )
        else:
            logger.info(
                f"➕ New email template created: '{obj.name}' by {request.user.username}"
            )
        super().save_model(request, obj, form, change)
