import logging

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)
User = get_user_model()


class VerificationForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control text-center",
                "placeholder": "123456",
                "maxlength": "6",
                "pattern": "[0-9]{6}",
                "required": True,
                "style": "font-size: 1.5rem; letter-spacing: 0.5rem;",
            }
        ),
        label="کد تایید",
    )

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not code or not code.isdigit() or len(code) != 6:
            raise ValidationError("کد تایید باید 6 رقم باشد.")
        return code
