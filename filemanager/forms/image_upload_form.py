from PIL import Image as PILImage
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from filemanager.models import ImageUpload

User = get_user_model()


class ImageUploadForm(forms.ModelForm):
    """Enhanced form for image upload with preview and validation"""

    class Meta:
        model = ImageUpload
        fields = [
            "title",
            "description",
            "original_image",
            "minification_level",
            "resize_option",
            "maintain_aspect_ratio",
            "convert_to_webp",
            "is_active",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "عنوان تصویر را وارد کنید...",
                    "dir": "rtl",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "توضیحات تصویر (اختیاری)...",
                    "dir": "rtl",
                }
            ),
            "original_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control-file",
                    "accept": "image/*",
                    "onchange": "previewImage(this)",
                }
            ),
            "minification_level": forms.Select(
                attrs={"class": "form-control", "dir": "rtl"}
            ),
            "resize_option": forms.Select(
                attrs={"class": "form-control", "dir": "rtl"}
            ),
            "maintain_aspect_ratio": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "convert_to_webp": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        labels = {
            "title": "عنوان تصویر",
            "description": "توضیحات",
            "original_image": "فایل تصویر",
            "minification_level": "سطح فشرده‌سازی",
            "resize_option": "تغییر اندازه",
            "maintain_aspect_ratio": "حفظ نسبت ابعاد",
            "convert_to_webp": "تبدیل به فرمت WebP",
            "is_active": "فعال",
        }

        help_texts = {
            "title": "عنوان توضیحی برای تصویر انتخاب کنید",
            "description": "توضیحات تکمیلی در مورد تصویر (اختیاری)",
            "original_image": "فرمت‌های مجاز: JPG, PNG, GIF, WebP (حداکثر 10MB)",
            "minification_level": "سطح فشرده‌سازی تصویر - کیفیت بالاتر = حجم بیشتر",
            "resize_option": "تغییر اندازه تصویر به ابعاد از پیش تعریف شده",
            "maintain_aspect_ratio": "حفظ نسبت طول و عرض هنگام تغییر اندازه",
            "convert_to_webp": "تبدیل به فرمت WebP برای کاهش بیشتر حجم",
            "is_active": "آیا این تصویر فعال و قابل نمایش باشد؟",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Add custom CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                current_class = field.widget.attrs.get("class", "")
                if (
                        "form-control" not in current_class
                        and "form-check-input" not in current_class
                ):
                    field.widget.attrs["class"] = current_class + " form-control"

        # Make title required
        self.fields["title"].required = True
        self.fields["original_image"].required = True

    def clean_title(self):
        """Validate title field"""
        title = self.cleaned_data.get("title")
        if title:
            title = title.strip()
            if len(title) < 3:
                raise ValidationError("عنوان تصویر باید حداقل 3 کاراکتر باشد.")
            if len(title) > 200:
                raise ValidationError("عنوان تصویر نمی‌تواند بیش از 200 کاراکتر باشد.")

            # Check for duplicate titles for the same user
            if self.user:
                existing_query = ImageUpload.objects.filter(
                    title=title, uploaded_by=self.user
                )
                if self.instance.pk:
                    existing_query = existing_query.exclude(pk=self.instance.pk)

                if existing_query.exists():
                    raise ValidationError("شما قبلاً تصویری با این عنوان آپلود کرده‌اید.")

        return title

    def clean_original_image(self):
        """Validate uploaded image"""
        image = self.cleaned_data.get("original_image")

        if image:
            # Check file size (10MB limit)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(
                    "حجم فایل نمی‌تواند بیش از 10 مگابایت باشد. "
                    f"حجم فایل شما: {image.size / (1024 * 1024):.1f} مگابایت"
                )

            # Check file format
            allowed_formats = ["JPEG", "JPG", "PNG", "GIF", "WEBP"]
            try:
                with PILImage.open(image) as img:
                    if img.format not in allowed_formats:
                        raise ValidationError(
                            f'فرمت فایل پشتیبانی نمی‌شود. فرمت‌های مجاز: {", ".join(allowed_formats)}'
                        )

                    # Check image dimensions
                    width, height = img.size
                    if width < 50 or height < 50:
                        raise ValidationError(
                            "حداقل ابعاد تصویر باید 50x50 پیکسل باشد."
                        )

                    if width > 8000 or height > 8000:
                        raise ValidationError(
                            "حداکثر ابعاد تصویر نمی‌تواند بیش از 8000x8000 پیکسل باشد."
                        )

            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ValidationError("فایل آپلود شده یک تصویر معتبر نیست.")

        return image

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()

        minification_level = cleaned_data.get("minification_level")
        convert_to_webp = cleaned_data.get("convert_to_webp")

        # Warn about potential quality loss
        if minification_level in ["high", "maximum"] and not convert_to_webp:
            self.add_error(
                "minification_level",
                "توجه: فشرده‌سازی بالا ممکن است کیفیت تصویر را کاهش دهد. "
                "استفاده از فرمت WebP توصیه می‌شود.",
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.uploaded_by = self.user
        if commit:
            instance.save()
        return instance
