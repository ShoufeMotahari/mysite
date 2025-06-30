from django import forms
from users.models import User

class SignupForm(forms.Form):
    mobile = forms.CharField(max_length=11)

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        if not mobile.startswith('09') or len(mobile) != 11:
            raise forms.ValidationError("شماره موبایل نامعتبر است.")
        return mobile
