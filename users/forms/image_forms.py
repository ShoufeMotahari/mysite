# users/forms/image_forms.py - CREATE THIS NEW FILE

from django import forms
from django.core.exceptions import ValidationError
from PIL import Image as PILImage
import os

from ..models import ImageUpload, ImageGallery


class ImageUploadForm(forms.ModelForm):
    """Enhanced form for image upload with preview and validation"""

    class Meta:
        model = ImageUpload
        fields = [
            'title', 'description', 'original_image', 'minification_level',
            'resize_option', 'maintain_aspect_ratio', 'convert_to_webp', 'is_active'
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان تصویر را وارد کنید...',
                'dir': 'rtl'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'توضیحات تصویر (اختیاری)...',
                'dir': 'rtl'
            }),
            'original_image': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*',
                'onchange': 'previewImage(this)'
            }),
            'minification_level': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'resize_option': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'maintain_aspect_ratio': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'convert_to_webp': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

        labels = {
            'title': 'عنوان تصویر',
            'description': 'توضیحات',
            'original_image': 'فایل تصویر',
            'minification_level': 'سطح فشرده‌سازی',
            'resize_option': 'تغییر اندازه',
            'maintain_aspect_ratio': 'حفظ نسبت ابعاد',
            'convert_to_webp': 'تبدیل به فرمت WebP',
            'is_active': 'فعال'
        }

        help_texts = {
            'title': 'عنوان توضیحی برای تصویر انتخاب کنید',
            'description': 'توضیحات تکمیلی در مورد تصویر (اختیاری)',
            'original_image': 'فرمت‌های مجاز: JPG, PNG, GIF, WebP (حداکثر 10MB)',
            'minification_level': 'سطح فشرده‌سازی تصویر - کیفیت بالاتر = حجم بیشتر',
            'resize_option': 'تغییر اندازه تصویر به ابعاد از پیش تعریف شده',
            'maintain_aspect_ratio': 'حفظ نسبت طول و عرض هنگام تغییر اندازه',
            'convert_to_webp': 'تبدیل به فرمت WebP برای کاهش بیشتر حجم',
            'is_active': 'آیا این تصویر فعال و قابل نمایش باشد؟'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add custom CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                current_class = field.widget.attrs.get('class', '')
                if 'form-control' not in current_class and 'form-check-input' not in current_class:
                    field.widget.attrs['class'] = current_class + ' form-control'

        # Make title required
        self.fields['title'].required = True
        self.fields['original_image'].required = True

    def clean_title(self):
        """Validate title field"""
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip()
            if len(title) < 3:
                raise ValidationError('عنوان تصویر باید حداقل 3 کاراکتر باشد.')
            if len(title) > 200:
                raise ValidationError('عنوان تصویر نمی‌تواند بیش از 200 کاراکتر باشد.')

            # Check for duplicate titles for the same user
            if self.instance.pk:
                existing = ImageUpload.objects.filter(
                    title=title,
                    uploaded_by=self.instance.uploaded_by
                ).exclude(pk=self.instance.pk)
            else:
                # For new uploads, we'll check in the view since we need the user
                pass

        return title

    def clean_original_image(self):
        """Validate uploaded image"""
        image = self.cleaned_data.get('original_image')

        if image:
            # Check file size (10MB limit)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(
                    'حجم فایل نمی‌تواند بیش از 10 مگابایت باشد. '
                    f'حجم فایل شما: {image.size / (1024 * 1024):.1f} مگابایت'
                )

            # Check file format
            allowed_formats = ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP']
            try:
                with PILImage.open(image) as img:
                    if img.format not in allowed_formats:
                        raise ValidationError(
                            f'فرمت فایل پشتیبانی نمی‌شود. فرمت‌های مجاز: {", ".join(allowed_formats)}'
                        )

                    # Check image dimensions
                    width, height = img.size
                    if width < 50 or height < 50:
                        raise ValidationError('حداقل ابعاد تصویر باید 50x50 پیکسل باشد.')

                    if width > 8000 or height > 8000:
                        raise ValidationError('حداکثر ابعاد تصویر نمی‌تواند بیش از 8000x8000 پیکسل باشد.')

            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ValidationError('فایل آپلود شده یک تصویر معتبر نیست.')

        return image

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()

        minification_level = cleaned_data.get('minification_level')
        convert_to_webp = cleaned_data.get('convert_to_webp')
        resize_option = cleaned_data.get('resize_option')

        # Warn about potential quality loss
        if minification_level in ['high', 'maximum'] and not convert_to_webp:
            self.add_error(
                'minification_level',
                'توجه: فشرده‌سازی بالا ممکن است کیفیت تصویر را کاهش دهد. '
                'استفاده از فرمت WebP توصیه می‌شود.'
            )

        return cleaned_data


class BulkImageProcessForm(forms.Form):
    """Form for bulk processing multiple images"""

    minification_level = forms.ChoiceField(
        choices=[('', 'بدون تغییر')] + ImageUpload.MINIFICATION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='سطح فشرده‌سازی'
    )

    resize_option = forms.ChoiceField(
        choices=[('', 'بدون تغییر')] + ImageUpload.SIZE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='تغییر اندازه'
    )

    convert_to_webp = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='تبدیل به فرمت WebP'
    )

    maintain_aspect_ratio = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='حفظ نسبت ابعاد'
    )

    selected_images = forms.ModelMultipleChoiceField(
        queryset=ImageUpload.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label='تصاویر انتخابی'
    )

    apply_to_all = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='اعمال به همه تصاویر'
    )

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()

        selected_images = cleaned_data.get('selected_images')
        apply_to_all = cleaned_data.get('apply_to_all')

        if not apply_to_all and not selected_images:
            raise ValidationError(
                'لطفاً تصاویری را انتخاب کنید یا گزینه "اعمال به همه تصاویر" را فعال کنید.'
            )

        # Check if at least one processing option is selected
        minification_level = cleaned_data.get('minification_level')
        resize_option = cleaned_data.get('resize_option')
        convert_to_webp = cleaned_data.get('convert_to_webp')

        if not any([minification_level, resize_option, convert_to_webp]):
            raise ValidationError(
                'لطفاً حداقل یک گزینه پردازش را انتخاب کنید.'
            )

        return cleaned_data


class ImageGalleryForm(forms.ModelForm):
    """Form for creating and editing image galleries"""

    class Meta:
        model = ImageGallery
        fields = ['name', 'description', 'cover_image', 'images', 'is_public']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام گالری را وارد کنید...',
                'dir': 'rtl'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'توضیحات گالری (اختیاری)...',
                'dir': 'rtl'
            }),
            'cover_image': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'images': forms.CheckboxSelectMultiple(),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

        labels = {
            'name': 'نام گالری',
            'description': 'توضیحات',
            'cover_image': 'تصویر کاور',
            'images': 'تصاویر گالری',
            'is_public': 'عمومی'
        }

        help_texts = {
            'name': 'نام گالری تصاویر',
            'description': 'توضیحات تکمیلی در مورد گالری',
            'cover_image': 'تصویر کاور برای نمایش گالری',
            'images': 'تصاویری که در این گالری قرار خواهند گرفت',
            'is_public': 'آیا این گالری برای همه قابل مشاهده باشد؟'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter cover_image choices to only active images
        self.fields['cover_image'].queryset = ImageUpload.objects.filter(is_active=True)

        # Filter images to only active images
        self.fields['images'].queryset = ImageUpload.objects.filter(is_active=True)

        # Make name required
        self.fields['name'].required = True

    def clean_name(self):
        """Validate gallery name"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 3:
                raise ValidationError('نام گالری باید حداقل 3 کاراکتر باشد.')
            if len(name) > 200:
                raise ValidationError('نام گالری نمی‌تواند بیش از 200 کاراکتر باشد.')
        return name


class ImageSearchForm(forms.Form):
    """Form for searching and filtering images"""

    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'جستجو در عنوان و توضیحات...',
            'dir': 'rtl'
        }),
        label='جستجو'
    )

    minification_level = forms.ChoiceField(
        choices=[('', 'همه سطوح')] + ImageUpload.MINIFICATION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='سطح فشرده‌سازی'
    )

    resize_option = forms.ChoiceField(
        choices=[('', 'همه اندازه‌ها')] + ImageUpload.SIZE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='اندازه'
    )

    convert_to_webp = forms.ChoiceField(
        choices=[('', 'همه فرمت‌ها'), ('True', 'WebP'), ('False', 'سایر فرمت‌ها')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='فرمت'
    )

    is_active = forms.ChoiceField(
        choices=[('', 'همه'), ('True', 'فعال'), ('False', 'غیرفعال')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='وضعیت'
    )

    uploaded_by = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='آپلود شده توسط'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set uploaded_by queryset to users who have uploaded images
        from django.contrib.auth import get_user_model
        User = get_user_model()

        self.fields['uploaded_by'].queryset = User.objects.filter(
            uploaded_images__isnull=False
        ).distinct().order_by('username')