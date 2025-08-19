from django.contrib import admin

from filemanager.models import ImageGallery


@admin.register(ImageGallery)
class ImageGalleryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "created_by",
        "created_at",
        "is_public",
        "get_images_count",
        "get_total_size_display",
    ]
    list_filter = ["created_at", "is_public", "created_by"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["images"]
    list_per_page = 20

    fieldsets = (
        (
            "اطلاعات اصلی",
            {"fields": ("name", "description", "created_by", "is_public")},
        ),
        ("تصاویر", {"fields": ("cover_image", "images")}),
        (
            "زمان‌بندی",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
