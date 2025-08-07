from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from PIL import Image as PILImage
import os

from .models import ImageUpload, ImageGallery, Document

User = get_user_model()


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
        self.user = kwargs.pop('user', None)
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
            if self.user:
                existing_query = ImageUpload.objects.filter(
                    title=title,
                    uploaded_by=self.user
                )
                if self.instance.pk:
                    existing_query = existing_query.exclude(pk=self.instance.pk)

                if existing_query.exists():
                    raise ValidationError('شما قبلاً تصویری با این عنوان آپلود کرده‌اید.')

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

        # Warn about potential quality loss
        if minification_level in ['high', 'maximum'] and not convert_to_webp:
            self.add_error(
                'minification_level',
                'توجه: فشرده‌سازی بالا ممکن است کیفیت تصویر را کاهش دهد. '
                'استفاده از فرمت WebP توصیه می‌شود.'
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.uploaded_by = self.user
        if commit:
            instance.save()
        return instance


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
        queryset=ImageUpload.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label='تصاویر انتخابی'
    )

    apply_to_all = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='اعمال به همه تصاویر'
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['selected_images'].queryset = ImageUpload.objects.filter(
                uploaded_by=user,
                is_active=True
            ).order_by('-created_at')

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
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter cover_image and images to only user's active images
        if user:
            active_images = ImageUpload.objects.filter(uploaded_by=user, is_active=True)
            self.fields['cover_image'].queryset = active_images
            self.fields['images'].queryset = active_images
        else:
            # Fallback to all active images if no user provided
            active_images = ImageUpload.objects.filter(is_active=True)
            self.fields['cover_image'].queryset = active_images
            self.fields['images'].queryset = active_images

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

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()

        cover_image = cleaned_data.get('cover_image')
        images = cleaned_data.get('images')

        # If cover_image is selected, it should be in the images list
        if cover_image and images and cover_image not in images:
            cleaned_data['images'] = list(images) + [cover_image]

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, 'user') and self.user:
            instance.created_by = self.user
        if commit:
            instance.save()
            self.save_m2m()  # Save many-to-many relationships
        return instance


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

    processing_status = forms.ChoiceField(
        choices=[('', 'همه وضعیت‌ها')] + ImageUpload._meta.get_field('processing_status').choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='وضعیت پردازش'
    )

    uploaded_by = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='آپلود شده توسط'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set uploaded_by queryset to users who have uploaded images
        self.fields['uploaded_by'].queryset = User.objects.filter(
            uploaded_images__isnull=False
        ).distinct().order_by('username')


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'description', 'file', 'file_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام فایل',
                'dir': 'rtl'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'توضیحات فایل',
                'dir': 'rtl'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'file_type': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
        }

        labels = {
            'name': 'نام فایل',
            'description': 'توضیحات',
            'file': 'فایل',
            'file_type': 'نوع فایل'
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Make name required
        self.fields['name'].required = True
        self.fields['file'].required = True

    def clean_name(self):
        """Validate document name"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 3:
                raise ValidationError('نام فایل باید حداقل 3 کاراکتر باشد.')
            if len(name) > 200:
                raise ValidationError('نام فایل نمی‌تواند بیش از 200 کاراکتر باشد.')
        return name

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('حجم فایل نباید بیش از 10 مگابایت باشد.')

            # Check file extension
            allowed_extensions = [choice[0] for choice in Document.DOCUMENT_TYPES if choice[0] != 'other']
            file_extension = os.path.splitext(file.name)[1].lower().lstrip('.')

            if file_extension and file_extension not in allowed_extensions:
                # It's okay if it's not in the list, will be marked as 'other'
                pass

        return file

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.uploaded_by = self.user
        if commit:
            instance.save()
        return instance


class DocumentSearchForm(forms.Form):
    """Form for searching and filtering documents"""

    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'جستجو در نام و توضیحات...',
            'dir': 'rtl'
        }),
        label='جستجو'
    )

    file_type = forms.ChoiceField(
        choices=[('', 'همه انواع')] + Document.DOCUMENT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='نوع فایل'
    )

    is_active = forms.ChoiceField(
        choices=[('', 'همه'), ('True', 'فعال'), ('False', 'غیرفعال')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='وضعیت'
    )

    uploaded_by = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        label='آپلود شده توسط'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set uploaded_by queryset to users who have uploaded documents
        self.fields['uploaded_by'].queryset = User.objects.filter(
            document_set__isnull=False
        ).distinct().order_by('username')