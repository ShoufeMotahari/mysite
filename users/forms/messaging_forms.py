# messaging/forms.py
from django import forms

from users.models import AdminMessage, AdminMessageReply


class AdminMessageForm(forms.ModelForm):
    """Form for message admins to send messages"""

    class Meta:
        model = AdminMessage
        fields = ["subject", "message", "priority"]

        widgets = {
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "موضوع پیام را وارد کنید...",
                    "dir": "rtl",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "متن پیام خود را اینجا بنویسید...",
                    "dir": "rtl",
                }
            ),
            "priority": forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        }

        labels = {"subject": "موضوع پیام", "message": "متن پیام", "priority": "اولویت"}

        help_texts = {
            "subject": "موضوع کوتاه و گویا برای پیام انتخاب کنید",
            "message": "متن کامل پیام را با جزئیات لازم بنویسید",
            "priority": "اولویت پیام را بر اساس اهمیت آن تعیین کنید",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add CSS classes and customize fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, "attrs"):
                field.widget.attrs.update(
                    {"class": field.widget.attrs.get("class", "") + " form-control"}
                )

        # Make subject and message required
        self.fields["subject"].required = True
        self.fields["message"].required = True

    def clean_subject(self):
        """Validate subject field"""
        subject = self.cleaned_data.get("subject")
        if subject:
            subject = subject.strip()
            if len(subject) < 5:
                raise forms.ValidationError("موضوع پیام باید حداقل 5 کاراکتر باشد.")
            if len(subject) > 200:
                raise forms.ValidationError(
                    "موضوع پیام نمی‌تواند بیش از 200 کاراکتر باشد."
                )
        return subject

    def clean_message(self):
        """Validate message field"""
        message = self.cleaned_data.get("message")
        if message:
            message = message.strip()
            if len(message) < 10:
                raise forms.ValidationError("متن پیام باید حداقل 10 کاراکتر باشد.")
            if len(message) > 5000:
                raise forms.ValidationError(
                    "متن پیام نمی‌تواند بیش از 5000 کاراکتر باشد."
                )
        return message


class AdminMessageReplyForm(forms.ModelForm):
    """Form for superuser admins to reply to messages"""

    class Meta:
        model = AdminMessageReply
        fields = ["reply_text"]

        widgets = {
            "reply_text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "پاسخ خود را اینجا بنویسید...",
                    "dir": "rtl",
                }
            )
        }

        labels = {"reply_text": "متن پاسخ"}

        help_texts = {"reply_text": "پاسخ خود را به پیام ارسالی بنویسید"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make reply text required
        self.fields["reply_text"].required = True

    def clean_reply_text(self):
        """Validate reply text field"""
        reply_text = self.cleaned_data.get("reply_text")
        if reply_text:
            reply_text = reply_text.strip()
            if len(reply_text) < 5:
                raise forms.ValidationError("متن پاسخ باید حداقل 5 کاراکتر باشد.")
            if len(reply_text) > 2000:
                raise forms.ValidationError(
                    "متن پاسخ نمی‌تواند بیش از 2000 کاراکتر باشد."
                )
        return reply_text


class MessageSearchForm(forms.Form):
    """Form for searching messages"""

    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "جستجو در موضوع و متن پیام...",
                "dir": "rtl",
            }
        ),
        label="جستجو",
    )

    status = forms.ChoiceField(
        choices=[("", "همه وضعیت‌ها")] + AdminMessage.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="وضعیت",
    )

    priority = forms.ChoiceField(
        choices=[("", "همه اولویت‌ها")] + AdminMessage.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "dir": "rtl"}),
        label="اولویت",
    )
