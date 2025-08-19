import logging
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django_pwned.validators import PwnedPasswordValidator

from users.utils.password_utils import get_password_strength, make_password

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Enhanced user creation form with email validation, pwned check, and password strength"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
        }

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if not username:
            raise ValidationError("Username is required.")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists.")
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise ValidationError("Email is required.")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists.")
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        username = self.cleaned_data.get("username")

        if password1:
            # Pwned check
            validator = PwnedPasswordValidator()
            try:
                validator.validate(password1)
            except ValidationError:
                raise ValidationError("رمز عبور شما در نشت اطلاعاتی یافت شده است. رمز دیگری انتخاب کنید.")

            # Strength check
            strength = get_password_strength(password1)
            if strength["score"] < 3:
                raise ValidationError(
                    f"Password is too weak ({strength['strength']}). "
                    f"Suggestions: {', '.join(strength['suggestions'])}"
                )

        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        # Use custom password hashing
        user.password = make_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
