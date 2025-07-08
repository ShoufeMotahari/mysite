from django import forms
from .models import User, Profile

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'mobile']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']