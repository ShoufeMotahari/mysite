import logging

from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from users.models.email_template import EmailTemplate

logger = logging.getLogger(__name__)
User = get_user_model()

class EmailForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="قالب ایمیل",
        empty_label="انتخاب قالب ایمیل...",
        required=False,
    )

    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        label="گیرندگان",
        required=False,
    )

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "موضوع سفارشی (اختیاری)"}
        ),
        label="موضوع (اختیاری)",
        required=False,
    )

    content = forms.CharField(
        widget=CKEditorWidget(), label="محتوا (اختیاری)", required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = EmailTemplate.objects.filter(is_active=True)
        self.fields['recipients'].queryset = (
            User.objects.filter(is_active=True, email__isnull=False).exclude(email="")
        )

    def clean(self):
        cleaned_data = super().clean()
        template = cleaned_data.get("template")
        subject = cleaned_data.get("subject")
        content = cleaned_data.get("content")

        if not template and not (subject or content):
            raise ValidationError(
                "حداقل یک قالب یا موضوع/محتوای سفارشی باید انتخاب شود."
            )

        return cleaned_data


class EmailTemplateForm(forms.ModelForm):
    """Form for managing email templates"""

    class Meta:
        model = EmailTemplate
        fields = ["name", "subject", "content", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "content": CKEditorWidget(),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name or not name.strip():
            raise ValidationError("Template name cannot be empty.")
        return name.strip()

    def clean_subject(self):
        subject = self.cleaned_data.get("subject")
        if not subject or not subject.strip():
            raise ValidationError("Template subject cannot be empty.")
        return subject.strip()

    def clean_content(self):
        content = self.cleaned_data.get("content")
        if not content or not content.strip():
            raise ValidationError("Template content cannot be empty.")
        return content.strip()
