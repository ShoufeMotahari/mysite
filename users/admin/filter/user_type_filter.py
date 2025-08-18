import logging
from users.models import userType
from django.contrib import admin

from users.models.userType import UserType

logger = logging.getLogger(__name__)

class UserTypeFilter(admin.SimpleListFilter):
    """Filter users by user type"""

    title = "نوع کاربری"
    parameter_name = "user_type"

    def lookups(self, request, model_admin):
        user_types = UserType.objects.filter(is_active=True)
        return [(ut.id, ut.name) for ut in user_types] + [("none", "بدون نوع")]

    def queryset(self, request, queryset):
        if self.value() == "none":
            return queryset.filter(user_type__isnull=True)
        elif self.value():
            return queryset.filter(user_type_id=self.value())
        return queryset
