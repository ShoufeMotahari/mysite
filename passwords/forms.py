from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django_pwned.validators import PwnedPasswordValidator
import logging

from users.models import PasswordEntry

logger = logging.getLogger(__name__)


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data.get('username')
        logger.debug(f"Validating username: {username}")

        if User.objects.filter(username=username).exists():
            logger.warning(f"Username already exists: {username}")
            raise ValidationError("Username already exists.")

        logger.debug(f"Username validation passed: {username}")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        logger.debug(f"Validating email: {email}")

        if User.objects.filter(email=email).exists():
            logger.warning(f"Email already exists: {email}")
            raise ValidationError("Email already exists.")

        logger.debug(f"Email validation passed: {email}")
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        username = self.cleaned_data.get('username')

        if password1:
            logger.debug(f"Validating password for user: {username}")
            validator = PwnedPasswordValidator()
            try:
                validator.validate(password1)
                logger.info(f"Password validation passed for user: {username}")
            except ValidationError:
                logger.warning(f"Pwned password attempted for user: {username}")
                raise ValidationError("رمز عبور شما در نشت اطلاعاتی یافت شده است. رمز دیگری انتخاب کنید.")
            except Exception as e:
                logger.error(f"Password validation error for user {username}: {str(e)}")
                # Continue with registration even if pwned check fails

        return password1

    def save(self, commit=True):
        logger.debug(f"Saving user: {self.cleaned_data.get('username')}")
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            logger.info(f"User created successfully: {user.username}, Email: {user.email}")

        return user


class PasswordEntryForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), max_length=200)

    class Meta:
        model = PasswordEntry
        fields = ['service_name', 'username', 'password']
        widgets = {
            'service_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service Name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def clean_service_name(self):
        service_name = self.cleaned_data.get('service_name')
        logger.debug(f"Validating service name: {service_name}")

        if not service_name or not service_name.strip():
            logger.warning("Empty service name submitted")
            raise ValidationError("Service name cannot be empty.")

        return service_name.strip()

    def clean_username(self):
        username = self.cleaned_data.get('username')
        logger.debug(f"Validating username: {username}")

        if not username or not username.strip():
            logger.warning("Empty username submitted")
            raise ValidationError("Username cannot be empty.")

        return username.strip()

    def clean_password(self):
        password = self.cleaned_data.get('password')
        service_name = self.cleaned_data.get('service_name')

        if password:
            logger.debug(f"Validating password for service: {service_name}")
            validator = PwnedPasswordValidator()
            try:
                validator.validate(password)
                logger.info(f"Password validation passed for service: {service_name}")
            except ValidationError:
                logger.warning(f"Pwned password attempted for service: {service_name}")
                raise ValidationError(
                    "This password has been found in data breaches. Please choose a different password.")
            except Exception as e:
                logger.error(f"Password validation error for service {service_name}: {str(e)}")
                # Don't block entry if pwned check fails

        return password

    def clean(self):
        cleaned_data = super().clean()
        service_name = cleaned_data.get('service_name')
        username = cleaned_data.get('username')

        logger.debug(f"Validating form data - Service: {service_name}, Username: {username}")

        return cleaned_data
