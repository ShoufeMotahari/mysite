# forms_.py (add to your existing forms)
from django import forms
from django.contrib.auth import get_user_model
from ckeditor.widgets import CKEditorWidget

from core.models import EmailTemplate

User = get_user_model()

class EmailForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='قالب ایمیل'
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        label='گیرندگان'
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='موضوع (اختیاری)',
        required=False
    )
    content = forms.CharField(
        widget=CKEditorWidget(),
        label='محتوا (اختیاری)',
        required=False
    )

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'content', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'content': CKEditorWidget(),
        }