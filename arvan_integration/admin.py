# arvan_integration/admin.py
from django.contrib import admin
from django.utils.html import format_html

from arvan_integration.services import ArvanService


def get_image_preview(image_field, height=50):
    """
    Generate image preview for admin
    """
    if image_field and hasattr(image_field, "name") and image_field.name:
        # Use Django's default storage URL generation
        url = image_field.url
        return format_html(
            '<img src="{}" height="{}" style="border-radius: 4px; object-fit: cover;" />',
            url,
            height,
        )
    return "No image"


def get_file_link(file_field, link_text="Download"):
    """
    Generate download link for admin
    """
    if file_field and hasattr(file_field, "name") and file_field.name:
        url = file_field.url
        return format_html(
            '<a href="{}" target="_blank" class="button">{}</a>', url, link_text
        )
    return "No file"


# Example usage in your model admin:
class YourModelAdmin(admin.ModelAdmin):
    list_display = ["title", "image_preview", "file_link"]
    readonly_fields = ["image_preview", "file_link"]

    def image_preview(self, obj):
        return get_image_preview(obj.image, height=60)

    image_preview.short_description = "Image Preview"

    def file_link(self, obj):
        return get_file_link(obj.file, "Download File")

    file_link.short_description = "File Link"


# If you want to use your custom service (not recommended with django-storages):
def custom_avatar_preview(obj, field_name="image"):
    """
    Custom avatar preview using ArvanService
    """
    field = getattr(obj, field_name)
    if field and hasattr(field, "name") and field.name:
        url = ArvanService.get_url(field.name)
        return format_html(
            '<img src="{}" height="50" style="border-radius: 4px;" />', url
        )
    return "No image"
