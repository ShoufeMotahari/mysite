from django.contrib import admin

from django.contrib import admin
from .models import Profile
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter

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
