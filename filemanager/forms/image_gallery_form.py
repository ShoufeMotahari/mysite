from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from filemanager.models import ImageGallery, ImageUpload

User = get_user_model()


class ImageGalleryForm(forms.ModelForm):
    """Form for creating and editing image galleries"""

    class Meta:
        model = ImageGallery
        fields = ["name", "description", "cover_image", "images", "is_public"]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "نام گالری را وارد کنید...",
                    "dir": "rtl",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "توضیحات گالری (اختیاری)...",
                    "dir": "rtl",
                }
            ),
            "cover_image": forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
            "images": forms.CheckboxSelectMultiple(),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

        labels = {
            "name": "نام گالری",
            "description": "توضیحات",
            "cover_image": "تصویر کاور",
            "images": "تصاویر گالری",
            "is_public": "عمومی",
        }

        help_texts = {
            "name": "نام گالری تصاویر",
            "description": "توضیحات تکمیلی در مورد گالری",
            "cover_image": "تصویر کاور برای نمایش گالری",
            "images": "تصاویری که در این گالری قرار خواهند گرفت",
            "is_public": "آیا این گالری برای همه قابل مشاهده باشد؟",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter cover_image and images to only user's active images
        if user:
            active_images = ImageUpload.objects.filter(uploaded_by=user, is_active=True)
            self.fields["cover_image"].queryset = active_images
            self.fields["images"].queryset = active_images
        else:
            # Fallback to all active images if no user provided
            active_images = ImageUpload.objects.filter(is_active=True)
            self.fields["cover_image"].queryset = active_images
            self.fields["images"].queryset = active_images

        # Make name required
        self.fields["name"].required = True

    def clean_name(self):
        """Validate gallery name"""
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            if len(name) < 3:
                raise ValidationError("نام گالری باید حداقل 3 کاراکتر باشد.")
            if len(name) > 200:
                raise ValidationError("نام گالری نمی‌تواند بیش از 200 کاراکتر باشد.")
        return name

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()

        cover_image = cleaned_data.get("cover_image")
        images = cleaned_data.get("images")

        # If cover_image is selected, it should be in the images list
        if cover_image and images and cover_image not in images:
            cleaned_data["images"] = list(images) + [cover_image]

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, "user") and self.user:
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
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "جستجو در عنوان و توضیحات...",
                "dir": "rtl",
            }
        ),
        label="جستجو",
    )

    minification_level = forms.ChoiceField(
        choices=[("", "همه سطوح")] + ImageUpload.MINIFICATION_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="سطح فشرده‌سازی",
    )

    resize_option = forms.ChoiceField(
        choices=[("", "همه اندازه‌ها")] + ImageUpload.SIZE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="اندازه",
    )

    convert_to_webp = forms.ChoiceField(
        choices=[("", "همه فرمت‌ها"), ("True", "WebP"), ("False", "سایر فرمت‌ها")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="فرمت",
    )

    is_active = forms.ChoiceField(
        choices=[("", "همه"), ("True", "فعال"), ("False", "غیرفعال")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="وضعیت",
    )

    processing_status = forms.ChoiceField(
        choices=[("", "همه وضعیت‌ها")]
                + ImageUpload._meta.get_field("processing_status").choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="وضعیت پردازش",
    )

    uploaded_by = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="آپلود شده توسط",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set uploaded_by queryset to users who have uploaded images
        self.fields["uploaded_by"].queryset = (
            User.objects.filter(uploaded_images__isnull=False)
            .distinct()
            .order_by("username")
        )
