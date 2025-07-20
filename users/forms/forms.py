# users/forms.py - Merged forms configuration
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from ckeditor.widgets import CKEditorWidget
from django_pwned.validators import PwnedPasswordValidator
import logging

# Import models
from users.models import User, Profile, PasswordEntry
from emails.models import EmailTemplate

# Setup logging
logger = logging.getLogger(__name__)

# Get the User model
User = get_user_model()


# User Registration and Authentication Forms
class CustomUserCreationForm(UserCreationForm):
    """Enhanced user creation form with email validation and pwned password checking"""
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


class SignupForm(forms.Form):
    """Mobile-based signup form"""
    mobile = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={'placeholder': 'شماره موبایل'}),
        label='شماره موبایل'
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'placeholder': 'ایمیل (اختیاری)'}),
        label='ایمیل'
    )

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        if not mobile.startswith('09') or len(mobile) != 11:
            raise forms.ValidationError("شماره موبایل باید 11 رقم باشد و با 09 شروع شود.")
        return mobile


class LoginForm(forms.Form):
    """Login form accepting mobile or email"""
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'شماره موبایل یا ایمیل'}),
        label='شماره موبایل یا ایمیل'
    )


class ForgotPasswordForm(forms.Form):
    """Password reset form"""
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'شماره موبایل یا ایمیل'}),
        label='شماره موبایل یا ایمیل'
    )


# User Profile Forms
class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""
    class Meta:
        model = User
        fields = ['email', 'mobile']


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    class Meta:
        model = Profile
        fields = ['image']


# Second Password Forms
class SecondPasswordForm(forms.Form):
    """Form for entering second password"""
    second_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز دوم'}),
        label='رمز دوم'
    )


class ChangeSecondPasswordForm(forms.Form):
    """Form for changing second password"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز دوم فعلی'}),
        label='رمز دوم فعلی'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز دوم جدید'}),
        label='رمز دوم جدید'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'تکرار رمز دوم جدید'}),
        label='تکرار رمز دوم جدید'
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("رمزهای عبور مطابقت ندارند.")

        return cleaned_data


# Password Entry Forms
class PasswordEntryForm(forms.ModelForm):
    """Form for managing password entries with pwned password validation"""
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


# Email Management Forms
class EmailForm(forms.Form):
    """Enhanced email form for admin email sending functionality"""
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='قالب ایمیل',
        empty_label='انتخاب قالب ایمیل...'
    )

    # Make recipients optional since we handle this in the admin view
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        label='گیرندگان',
        required=False  # Made optional for admin bulk operations
    )

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'موضوع سفارشی (اختیاری)'
        }),
        label='موضوع (اختیاری)',
        required=False
    )

    content = forms.CharField(
        widget=CKEditorWidget(),
        label='محتوا (اختیاری)',
        required=False
    )


class EmailTemplateForm(forms.ModelForm):
    """Form for managing email templates"""
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'content', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'content': CKEditorWidget(),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or not name.strip():
            raise ValidationError("Template name cannot be empty.")
        return name.strip()

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if not subject or not subject.strip():
            raise ValidationError("Template subject cannot be empty.")
        return subject.strip()