from django.contrib import admin
from .models import Photo, Document


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['title', 'uploaded_by', 'uploaded_at', 'is_active', 'get_file_size_display']
    list_filter = ['uploaded_at', 'is_active', 'uploaded_by']
    search_fields = ['title', 'description', 'alt_text']
    readonly_fields = ['uploaded_at', 'updated_at', 'file_size']
    list_per_page = 20


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'file_type', 'uploaded_by', 'uploaded_at', 'is_active', 'download_count',
                    'get_file_size_display']
    list_filter = ['uploaded_at', 'is_active', 'file_type', 'uploaded_by']
    search_fields = ['name', 'description']
    readonly_fields = ['uploaded_at', 'updated_at', 'file_size', 'download_count']
    list_per_page = 20


from django.contrib import admin

# Register your models here.
