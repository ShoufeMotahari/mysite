import os

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from filemanager.models import Document

User = get_user_model()


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["name", "description", "file", "file_type"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام فایل", "dir": "rtl"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "توضیحات فایل",
                    "dir": "rtl",
                }
            ),
            "file": forms.FileInput(attrs={"class": "form-control"}),
            "file_type": forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        }

        labels = {
            "name": "نام فایل",
            "description": "توضیحات",
            "file": "فایل",
            "file_type": "نوع فایل",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Make name required
        self.fields["name"].required = True
        self.fields["file"].required = True

    def clean_name(self):
        """Validate document name"""
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            if len(name) < 3:
                raise ValidationError("نام فایل باید حداقل 3 کاراکتر باشد.")
            if len(name) > 200:
                raise ValidationError("نام فایل نمی‌تواند بیش از 200 کاراکتر باشد.")
        return name

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("حجم فایل نباید بیش از 10 مگابایت باشد.")

            # Check file extension
            allowed_extensions = [
                choice[0] for choice in Document.DOCUMENT_TYPES if choice[0] != "other"
            ]
            file_extension = os.path.splitext(file.name)[1].lower().lstrip(".")

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
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "جستجو در نام و توضیحات...",
                "dir": "rtl",
            }
        ),
        label="جستجو",
    )

    file_type = forms.ChoiceField(
        choices=[("", "همه انواع")] + Document.DOCUMENT_TYPES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="نوع فایل",
    )

    is_active = forms.ChoiceField(
        choices=[("", "همه"), ("True", "فعال"), ("False", "غیرفعال")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="وضعیت",
    )

    uploaded_by = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="آپلود شده توسط",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set uploaded_by queryset to users who have uploaded documents
        self.fields["uploaded_by"].queryset = (
            User.objects.filter(document_set__isnull=False)
            .distinct()
            .order_by("username")
        )
