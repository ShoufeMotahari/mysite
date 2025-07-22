# users/forms.py - Improved forms configuration
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from ckeditor.widgets import CKEditorWidget
from django_pwned.validators import PwnedPasswordValidator
import logging
import re

# Import models
from users.models import Profile, PasswordEntry, Comment
from emails.models import EmailTemplate

# Setup logging
logger = logging.getLogger(__name__)

# Get the User model properly
User = get_user_model()


# User Registration and Authentication Forms
class CustomUserCreationForm(UserCreationForm):
    """Enhanced user creation form with email validation and pwned password checking"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        logger.debug(f"Validating username: {username}")

        if not username:
            raise ValidationError("Username is required.")

        if User.objects.filter(username=username).exists():
            logger.warning(f"Username already exists: {username}")
            raise ValidationError("Username already exists.")

        # Add username pattern validation
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")

        logger.debug(f"Username validation passed: {username}")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        logger.debug(f"Validating email: {email}")

        if not email:
            raise ValidationError("Email is required.")

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
    """Simple signup form with username, mobile, and password"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام کاربری',
            'required': True
        }),
        label='نام کاربری'
    )

    mobile = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09123456789',
            'required': True
        }),
        label='شماره موبایل'
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@domain.com (اختیاری)'
        }),
        label='ایمیل (اختیاری)'
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور',
            'required': True
        }),
        label='رمز عبور'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError("نام کاربری الزامی است.")

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("نام کاربری فقط می‌تواند شامل حروف، اعداد و خط تیره باشد.")

        if User.objects.filter(username=username).exists():
            raise ValidationError("این نام کاربری قبلاً گرفته شده است.")

        return username

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if not mobile:
            raise ValidationError("شماره موبایل الزامی است.")

        # Remove any non-digit characters
        mobile = re.sub(r'\D', '', mobile)

        if not mobile.startswith('09') or len(mobile) != 11:
            raise ValidationError("شماره موبایل باید 11 رقم باشد و با 09 شروع شود.")

        if User.objects.filter(mobile=mobile).exists():
            existing_user = User.objects.get(mobile=mobile)
            if existing_user.is_active and existing_user.is_phone_verified:
                raise ValidationError("این شماره موبایل قبلاً ثبت شده و فعال است.")

        return mobile

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email=email).exists():
                raise ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise ValidationError("رمز عبور الزامی است.")

        if len(password) < 8:
            raise ValidationError("رمز عبور باید حداقل 8 کاراکتر باشد.")

        return password

class LoginForm(forms.Form):
    """Login form accepting mobile or email"""
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'شماره موبایل یا ایمیل'
        }),
        label='شماره موبایل یا ایمیل'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور'
        }),
        label='رمز عبور'
    )

class ForgotPasswordForm(forms.Form):
    """Password reset form"""
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'شماره موبایل یا ایمیل'
        }),
        label='شماره موبایل یا ایمیل'
    )


class VerificationForm(forms.Form):
    """Form for entering SMS verification code"""
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '123456',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'required': True,
            'style': 'font-size: 1.5rem; letter-spacing: 0.5rem;'
        }),
        label='کد تایید'
    )

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code or not code.isdigit() or len(code) != 6:
            raise ValidationError("کد تایید باید 6 رقم باشد.")
        return code



# User Profile Forms
class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""

    class Meta:
        model = User
        fields = ['email', 'mobile', 'username', 'first_name', 'last_name']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            mobile = re.sub(r'\D', '', mobile)
            if not mobile.startswith('09') or len(mobile) != 11:
                raise ValidationError("شماره موبایل باید 11 رقم باشد و با 09 شروع شود.")

            # Check if mobile exists for other users
            if User.objects.filter(mobile=mobile).exclude(pk=self.instance.pk).exists():
                raise ValidationError("این شماره موبایل برای کاربر دیگری ثبت شده است.")

        return mobile

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email exists for other users
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError("این ایمیل برای کاربر دیگری ثبت شده است.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
                raise ValidationError("این نام کاربری برای کاربر دیگری ثبت شده است.")
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                raise ValidationError("نام کاربری فقط می‌تواند شامل حروف، اعداد و خط تیره باشد.")
        return username


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""

    class Meta:
        model = Profile
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (limit to 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("حجم تصویر نباید بیشتر از 5 مگابایت باشد.")

            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if image.content_type not in allowed_types:
                raise ValidationError("فقط فایل‌های تصویری مجاز هستند (JPEG, PNG, GIF).")

        return image


# Password Entry Forms
class PasswordEntryForm(forms.ModelForm):
    """Form for managing password entries with pwned password validation"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
        max_length=200
    )

    class Meta:
        model = PasswordEntry
        fields = ['service_name', 'username', 'password', 'notes']
        widgets = {
            'service_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service Name'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional notes (optional)',
                'rows': 3
            }),
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
                    "This password has been found in data breaches. Please choose a different password.")
            except Exception as e:
                logger.error(f"Password validation error for service {service_name}: {str(e)}")
                # Don't block entry if pwned check fails

        return password

    def clean(self):
        cleaned_data = super().clean()
        service_name = cleaned_data.get('service_name')
        username = cleaned_data.get('username')
        user = getattr(self, 'user', None)

        # Check for duplicate entries for the same user
        if user and service_name and username:
            existing = PasswordEntry.objects.filter(
                user=user,
                service_name=service_name,
                username=username
            )

            # Exclude current instance if updating
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(
                    f"A password entry for {service_name} with username {username} already exists."
                )

        logger.debug(f"Validating form data - Service: {service_name}, Username: {username}")
        return cleaned_data


# Comment Forms
class CommentForm(forms.ModelForm):
    """Form for user comments"""

    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'نظر خود را بنویسید...',
                'rows': 4
            })
        }

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if not content or not content.strip():
            raise ValidationError("محتوای نظر نمی‌تواند خالی باشد.")

        if len(content) < 10:
            raise ValidationError("نظر باید حداقل 10 کاراکتر باشد.")

        return content.strip()


# Email Management Forms
class EmailForm(forms.Form):
    """Enhanced email form for admin email sending functionality"""
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='قالب ایمیل',
        empty_label='انتخاب قالب ایمیل...',
        required=False
    )

    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True, email__isnull=False).exclude(email=''),
        widget=forms.CheckboxSelectMultiple(),
        label='گیرندگان',
        required=False
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

    def clean(self):
        cleaned_data = super().clean()
        template = cleaned_data.get('template')
        subject = cleaned_data.get('subject')
        content = cleaned_data.get('content')

        # At least template or custom subject/content must be provided
        if not template and not (subject or content):
            raise ValidationError("حداقل یک قالب یا موضوع/محتوای سفارشی باید انتخاب شود.")

        return cleaned_data


class EmailTemplateForm(forms.ModelForm):
    """Form for managing email templates"""

    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'content', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'content': CKEditorWidget(),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if not content or not content.strip():
            raise ValidationError("Template content cannot be empty.")
        return content.strip()


# Password Change Form
class ChangePasswordForm(forms.Form):
    """Form for changing user password"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور فعلی'
        }),
        label='رمز عبور فعلی'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور جدید'
        }),
        label='رمز عبور جدید'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'تکرار رمز عبور جدید'
        }),
        label='تکرار رمز عبور جدید'
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise ValidationError("رمز عبور فعلی صحیح نیست.")
        return current_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            validator = PwnedPasswordValidator()
            try:
                validator.validate(new_password)
            except ValidationError:
                raise ValidationError("این رمز عبور در نشت اطلاعاتی یافت شده است. رمز دیگری انتخاب کنید.")
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError("رمزهای عبور جدید مطابقت ندارند.")

        return cleaned_data