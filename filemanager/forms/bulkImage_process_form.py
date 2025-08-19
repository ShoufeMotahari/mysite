from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from filemanager.models import ImageUpload

User = get_user_model()


class BulkImageProcessForm(forms.Form):
    """Form for bulk processing multiple images"""

    minification_level = forms.ChoiceField(
        choices=[("", "بدون تغییر")] + ImageUpload.MINIFICATION_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="سطح فشرده‌سازی",
    )

    resize_option = forms.ChoiceField(
        choices=[("", "بدون تغییر")] + ImageUpload.SIZE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="تغییر اندازه",
    )

    convert_to_webp = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="تبدیل به فرمت WebP",
    )

    maintain_aspect_ratio = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="حفظ نسبت ابعاد",
    )

    selected_images = forms.ModelMultipleChoiceField(
        queryset=ImageUpload.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="تصاویر انتخابی",
    )

    apply_to_all = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="اعمال به همه تصاویر",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["selected_images"].queryset = ImageUpload.objects.filter(
                uploaded_by=user, is_active=True
            ).order_by("-created_at")

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()

        selected_images = cleaned_data.get("selected_images")
        apply_to_all = cleaned_data.get("apply_to_all")

        if not apply_to_all and not selected_images:
            raise ValidationError(
                'لطفاً تصاویری را انتخاب کنید یا گزینه "اعمال به همه تصاویر" را فعال کنید.'
            )

        # Check if at least one processing option is selected
        minification_level = cleaned_data.get("minification_level")
        resize_option = cleaned_data.get("resize_option")
        convert_to_webp = cleaned_data.get("convert_to_webp")

        if not any([minification_level, resize_option, convert_to_webp]):
            raise ValidationError("لطفاً حداقل یک گزینه پردازش را انتخاب کنید.")

        return cleaned_data
