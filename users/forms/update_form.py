import logging
import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)
User = get_user_model()


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""

    class Meta:
        model = User
        fields = ["email", "mobile", "username", "first_name", "last_name"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")
        if mobile:
            mobile = re.sub(r"\D", "", mobile)
            if not mobile.startswith("09") or len(mobile) != 11:
                raise ValidationError("شماره موبایل باید 11 رقم باشد و با 09 شروع شود.")

            # Check if mobile exists for other users
            if User.objects.filter(mobile=mobile).exclude(pk=self.instance.pk).exists():
                raise ValidationError("این شماره موبایل برای کاربر دیگری ثبت شده است.")

        return mobile

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            # Check if email exists for other users
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError("این ایمیل برای کاربر دیگری ثبت شده است.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            if (
                    User.objects.filter(username=username)
                            .exclude(pk=self.instance.pk)
                            .exists()
            ):
                raise ValidationError("این نام کاربری برای کاربر دیگری ثبت شده است.")
            if not re.match(r"^[a-zA-Z0-9_]+$", username):
                raise ValidationError(
                    "نام کاربری فقط می‌تواند شامل حروف، اعداد و خط تیره باشد."
                )
        return username


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""

    class Meta:
        fields = ["image"]
        widgets = {
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            )
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            # Check file size (limit to 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("حجم تصویر نباید بیشتر از 5 مگابایت باشد.")

            # Check file type
            allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif"]
            if image.content_type not in allowed_types:
                raise ValidationError("فقط فایل‌های تصویری مجاز هستند (JPEG, PNG, GIF).")

        return image
