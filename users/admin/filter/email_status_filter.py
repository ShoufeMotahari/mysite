import logging
from django.contrib import admin
from django.db.models import Q

logger = logging.getLogger(__name__)


class EmailStatusFilter(admin.SimpleListFilter):
    """Filter users by email validation status"""

    title = "وضعیت ایمیل"
    parameter_name = "email_status"

    def lookups(self, request, model_admin):
        return (
            ("valid", "ایمیل معتبر"),
            ("invalid", "ایمیل نامعتبر"),
            ("no_email", "بدون ایمیل"),
            ("verified", "ایمیل تایید شده"),
            ("unverified", "ایمیل تایید نشده"),
        )

    def queryset(self, request, queryset):
        if self.value() == "valid":
            return queryset.exclude(email__isnull=True).exclude(email="")
        elif self.value() == "invalid":
            return queryset.filter(Q(email__isnull=True) | Q(email=""))
        elif self.value() == "no_email":
            return queryset.filter(Q(email__isnull=True) | Q(email=""))
        elif self.value() == "verified":
            return queryset.filter(is_email_verified=True)
        elif self.value() == "unverified":
            return queryset.filter(is_email_verified=False)
        return queryset
