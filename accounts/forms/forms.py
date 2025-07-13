# forms.py (Enhanced EmailForm)
from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib.auth import get_user_model

from core.models import EmailTemplate

User = get_user_model()


class SignupForm(forms.Form):
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
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'شماره موبایل یا ایمیل'}),
        label='شماره موبایل یا ایمیل'
    )


class ForgotPasswordForm(forms.Form):
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'شماره موبایل یا ایمیل'}),
        label='شماره موبایل یا ایمیل'
    )


class SecondPasswordForm(forms.Form):
    second_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'رمز دوم'}),
        label='رمز دوم'
    )


class ChangeSecondPasswordForm(forms.Form):
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


class EmailForm(forms.Form):
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
        required=False  # Made optional
    )

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'موضوع سفارشی (اختیاری)'
        }),)