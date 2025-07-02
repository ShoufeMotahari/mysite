from django import forms
from users.models import User


class SignupForm(forms.Form):
    mobile = forms.CharField(max_length=11)

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        # if not mobile.startswith('09') or len(mobile) != 11:
        #     raise forms.ValidationError("شماره موبایل نامعتبر است.")
        return mobile


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