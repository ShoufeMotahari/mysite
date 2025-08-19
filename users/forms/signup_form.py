import logging
import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from users.utils.password_utils import get_password_strength

logger = logging.getLogger(__name__)
User = get_user_model()


class SignupForm(forms.Form):
    """Signup form with username, mobile, password strength check, and custom hashing"""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "نام کاربری", "required": True}),
        label="نام کاربری",
    )
    mobile = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "09123456789", "required": True}),
        label="شماره موبایل",
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@domain.com (اختیاری)"}),
        label="ایمیل (اختیاری)",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "رمز عبور", "required": True}),
        label="رمز عبور",
    )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if not username:
            raise ValidationError("نام کاربری الزامی است.")
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            raise ValidationError("نام کاربری فقط می‌تواند شامل حروف، اعداد و خط تیره باشد.")
        if User.objects.filter(username=username).exists():
            raise ValidationError("این نام کاربری قبلاً گرفته شده است.")
        return username

    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile")
        if not mobile:
            raise ValidationError("شماره موبایل الزامی است.")
        mobile = re.sub(r"\D", "", mobile)
        if not mobile.startswith("09") or len(mobile) != 11:
            raise ValidationError("شماره موبایل باید 11 رقم باشد و با 09 شروع شود.")
        if User.objects.filter(mobile=mobile).exists():
            existing_user = User.objects.get(mobile=mobile)
            if existing_user.is_active and existing_user.is_phone_verified:
                raise ValidationError("این شماره موبایل قبلاً ثبت شده و فعال است.")
        return mobile

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            raise ValidationError("رمز عبور الزامی است.")
        if len(password) < 8:
            raise ValidationError("رمز عبور باید حداقل 8 کاراکتر باشد.")

        # Strength check
        strength = get_password_strength(password)
        if strength["score"] < 3:
            raise ValidationError(
                f"Password is too weak ({strength['strength']}). "
                f"Suggestions: {', '.join(strength['suggestions'])}"
            )

        return password
