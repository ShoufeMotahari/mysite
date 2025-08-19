from django.contrib import admin
from django.utils.html import format_html

from filemanager.models import ImageUpload


@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "uploaded_by",
        "created_at",
        "is_active",
        "processing_status",
        "get_original_size_display",
        "get_compression_display",
        "processed_url_link",
    ]
    list_filter = [
        "created_at",
        "is_active",
        "uploaded_by",
        "processing_status",
        "minification_level",
        "resize_option",
        "convert_to_webp",
    ]
    search_fields = ["title", "description"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "processed_at",
        "original_size",
        "processed_size",
        "compression_ratio",
        "original_url",
        "processed_url",
        "processing_status",
    ]
    list_per_page = 20

    fieldsets = (
        (
            "اطلاعات اصلی",
            {
                "fields": (
                    "title",
                    "description",
                    "original_image",
                    "uploaded_by",
                    "is_active",
                )
            },
        ),
        (
            "تنظیمات پردازش",
            {
                "fields": (
                    "minification_level",
                    "resize_option",
                    "maintain_aspect_ratio",
                    "convert_to_webp",
                )
            },
        ),
        (
            "اطلاعات فایل",
            {
                "fields": ("original_size", "processed_size", "compression_ratio"),
                "classes": ("collapse",),
            },
        ),
        (
            "URL ها",
            {
                "fields": ("original_url", "processed_url"),
                "classes": ("collapse",),
            },
        ),
        (
            "زمان‌بندی",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "processed_at",
                    "processing_status",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["reprocess_images", "activate_images", "deactivate_images"]

    def processed_url_link(self, obj):
        if obj.processed_url:
            return format_html('<a href="{}" target="_blank">{}</a>', obj.processed_url, "لینک")
        return "-"

    processed_url_link.short_description = "لینک"

    def reprocess_images(self, request, queryset):
        """Reprocess selected images"""
        count = 0
        for image in queryset:
            if image.reprocess_image():
                count += 1
        self.message_user(request, f"{count} تصویر با موفقیت مجدداً پردازش شد.")

    reprocess_images.short_description = "پردازش مجدد تصاویر انتخاب شده"

    def activate_images(self, request, queryset):
        """Activate selected images"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} تصویر فعال شد.")

    activate_images.short_description = "فعال کردن تصاویر انتخاب شده"

    def deactivate_images(self, request, queryset):
        """Deactivate selected images"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} تصویر غیرفعال شد.")

    deactivate_images.short_description = "غیرفعال کردن تصاویر انتخاب شده"
