import logging

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from users.models.comment import Comment

logger = logging.getLogger(__name__)
User = get_user_model()

class CommentForm(forms.ModelForm):
    """Form for user comments"""

    class Meta:
        model = Comment
        fields = ["subject", "content"]  # Include both fields
        widgets = {
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "موضوع نظر (اختیاری)...",
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "نظر خود را بنویسید...",
                    "rows": 4,
                }
            )
        }

    def clean_subject(self):
        subject = self.cleaned_data.get("subject")
        # Since subject is optional, allow empty values
        if subject:
            subject = subject.strip()
            if len(subject) < 3:
                raise ValidationError("موضوع باید حداقل 3 کاراکتر باشد.")
            return subject
        return subject  # Can be None or empty

    def clean_content(self):
        content = self.cleaned_data.get("content")
        if not content or not content.strip():
            raise ValidationError("محتوای نظر نمی‌تواند خالی باشد.")

        if len(content.strip()) < 10:
            raise ValidationError("نظر باید حداقل 10 کاراکتر باشد.")

        return content.strip()
