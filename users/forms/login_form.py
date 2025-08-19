import logging

from django import forms
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class LoginForm(forms.Form):
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "شماره موبایل یا ایمیل"}),
        label="شماره موبایل یا ایمیل",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "رمز عبور"}),
        label="رمز عبور",
    )
