from django import forms
from users.models import User
from django.core.validators import validate_email

class SignupForm(forms.Form):
    mobile = forms.CharField(max_length=11)
    email = forms.EmailField(required=False)  # 👈 فیلد ایمیل اختیاری

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        # اعتبارسنجی دلخواه مثلاً:
        # if not mobile.startswith('09') or len(mobile) != 11:
        #     raise forms.ValidationError("شماره موبایل نامعتبر است.")
        return mobile

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            validate_email(email)
        return email


class LoginForm(forms.Form):
    identifier = forms.CharField(label="موبایل یا ایمیل")

    def clean_identifier(self):
        value = self.cleaned_data['identifier']
        if '@' in value:
            # ایمیله
            return value.lower()
        elif value.startswith('09') and len(value) == 11:
            # موبایل معتبر
            return value
        else:
            raise forms.ValidationError("ایمیل یا شماره موبایل معتبر وارد کنید.")

class SecondPasswordForm(forms.Form):
    second_password = forms.CharField(
        label="رمز دوم",
        max_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز عددی'}),
    )
class ChangeSecondPasswordForm(forms.Form):
    current_password = forms.CharField(
        label="رمز دوم فعلی",
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز دوم فعلی'}),
        max_length=6,
        required=True
    )
    new_password = forms.CharField(
        label="رمز دوم جدید",
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز دوم جدید'}),
        max_length=6,
        required=True
    )