import logging

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_pwned.validators import PwnedPasswordValidator

from users.models.password.password_entry import PasswordEntry

logger = logging.getLogger(__name__)
User = get_user_model()


class PasswordEntryForm(forms.ModelForm):
    """Form for managing password entries with pwned password validation"""

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        ),
        max_length=200,
    )

    class Meta:
        model = PasswordEntry
        fields = ["service_name", "username", "password", "notes"]
        widgets = {
            "service_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Service Name"}
            ),
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Username"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Additional notes (optional)",
                    "rows": 3,
                }
            ),
        }

    def clean_service_name(self):
        service_name = self.cleaned_data.get("service_name")
        logger.debug(f"Validating service name: {service_name}")

        if not service_name or not service_name.strip():
            logger.warning("Empty service name submitted")
            raise ValidationError("Service name cannot be empty.")

        return service_name.strip()

    def clean_username(self):
        username = self.cleaned_data.get("username")
        logger.debug(f"Validating username: {username}")

        if not username or not username.strip():
            logger.warning("Empty username submitted")
            raise ValidationError("Username cannot be empty.")

        return username.strip()

    def clean_password(self):
        password = self.cleaned_data.get("password")
        service_name = self.cleaned_data.get("service_name")

        if not password:
            raise ValidationError("Password is required.")

        if password:
            logger.debug(f"Validating password for service: {service_name}")
            validator = PwnedPasswordValidator()
            try:
                validator.validate(password)
                logger.info(f"Password validation passed for service: {service_name}")
            except ValidationError:
                logger.warning(f"Pwned password attempted for service: {service_name}")
                raise ValidationError(
                    "This password has been found in data breaches. Please choose a different password."
                )
            except Exception as e:
                logger.error(
                    f"Password validation error for service {service_name}: {str(e)}"
                )
                # Don't block entry if pwned check fails

        return password

    def clean(self):
        cleaned_data = super().clean()
        service_name = cleaned_data.get("service_name")
        username = cleaned_data.get("username")
        user = getattr(self, "user", None)

        # Check for duplicate entries for the same user
        if user and service_name and username:
            existing = PasswordEntry.objects.filter(
                user=user, service_name=service_name, username=username
            )

            # Exclude current instance if updating
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(
                    f"A password entry for {service_name} with username {username} already exists."
                )

        logger.debug(
            f"Validating form data - Service: {service_name}, Username: {username}"
        )
        return cleaned_data


class ChangePasswordForm(forms.Form):
    """Form for changing user password"""

    current_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "رمز عبور فعلی"}
        ),
        label="رمز عبور فعلی",
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "رمز عبور جدید"}
        ),
        label="رمز عبور جدید",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "تکرار رمز عبور جدید"}
        ),
        label="تکرار رمز عبور جدید",
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            raise ValidationError("رمز عبور فعلی صحیح نیست.")
        return current_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            validator = PwnedPasswordValidator()
            try:
                validator.validate(new_password)
            except ValidationError:
                raise ValidationError(
                    "این رمز عبور در نشت اطلاعاتی یافت شده است. رمز دیگری انتخاب کنید."
                )
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError("رمزهای عبور جدید مطابقت ندارند.")

        return cleaned_data
