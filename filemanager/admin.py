from django.contrib import admin
from .models import ImageUpload, ImageGallery, Document


@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'uploaded_by',
        'created_at',
        'is_active',
        'processing_status',
        'get_original_size_display',
        'get_compression_display'
    ]
    list_filter = [
        'created_at',
        'is_active',
        'uploaded_by',
        'processing_status',
        'minification_level',
        'resize_option',
        'convert_to_webp'
    ]
    search_fields = ['title', 'description']
    readonly_fields = [
        'created_at',
        'updated_at',
        'processed_at',
        'original_size',
        'processed_size',
        'compression_ratio',
        'original_url',
        'processed_url',
        'processing_status'
    ]
    list_per_page = 20

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'description', 'original_image', 'uploaded_by', 'is_active')
        }),
        ('تنظیمات پردازش', {
            'fields': ('minification_level', 'resize_option', 'maintain_aspect_ratio', 'convert_to_webp')
        }),
        ('اطلاعات فایل', {
            'fields': ('original_size', 'processed_size', 'compression_ratio'),
            'classes': ('collapse',),
        }),
        ('URL ها', {
            'fields': ('original_url', 'processed_url'),
            'classes': ('collapse',),
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at', 'processed_at', 'processing_status'),
            'classes': ('collapse',),
        }),
    )

    actions = ['reprocess_images', 'activate_images', 'deactivate_images']

    def reprocess_images(self, request, queryset):
        """Reprocess selected images"""
        count = 0
        for image in queryset:
            if image.reprocess_image():
                count += 1
        self.message_user(request, f'{count} تصویر با موفقیت مجدداً پردازش شد.')

    reprocess_images.short_description = 'پردازش مجدد تصاویر انتخاب شده'

    def activate_images(self, request, queryset):
        """Activate selected images"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} تصویر فعال شد.')

    activate_images.short_description = 'فعال کردن تصاویر انتخاب شده'

    def deactivate_images(self, request, queryset):
        """Deactivate selected images"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} تصویر غیرفعال شد.')

    deactivate_images.short_description = 'غیرفعال کردن تصاویر انتخاب شده'


@admin.register(ImageGallery)
class ImageGalleryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'created_by',
        'created_at',
        'is_public',
        'get_images_count',
        'get_total_size_display'
    ]
    list_filter = [
        'created_at',
        'is_public',
        'created_by'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['images']
    list_per_page = 20

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'description', 'created_by', 'is_public')
        }),
        ('تصاویر', {
            'fields': ('cover_image', 'images')
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'file_type',
        'uploaded_by',
        'uploaded_at',
        'is_active',
        'download_count',
        'get_file_size_display'
    ]
    list_filter = [
        'uploaded_at',
        'is_active',
        'file_type',
        'uploaded_by'
    ]
    search_fields = ['name', 'description']
    readonly_fields = [
        'uploaded_at',
        'updated_at',
        'file_size',
        'download_count'
    ]
    list_per_page = 20

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'description', 'file', 'file_type', 'uploaded_by', 'is_active')
        }),
        ('آمار', {
            'fields': ('file_size', 'download_count'),
            'classes': ('collapse',),
        }),
        ('زمان‌بندی', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['activate_documents', 'deactivate_documents', 'reset_download_count']

    def activate_documents(self, request, queryset):
        """Activate selected documents"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} سند فعال شد.')

    activate_documents.short_description = 'فعال کردن اسناد انتخاب شده'

    def deactivate_documents(self, request, queryset):
        """Deactivate selected documents"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} سند غیرفعال شد.')

    deactivate_documents.short_description = 'غیرفعال کردن اسناد انتخاب شده'

    def reset_download_count(self, request, queryset):
        """Reset download count for selected documents"""
        count = queryset.update(download_count=0)
        self.message_user(request, f'تعداد دانلود {count} سند بازنشانی شد.')

    reset_download_count.short_description = 'بازنشانی تعداد دانلود'