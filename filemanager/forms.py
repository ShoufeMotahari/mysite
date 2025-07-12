from django import forms
from .models import Photo, Document


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['title', 'description', 'image', 'alt_text']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان تصویر'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'توضیحات تصویر'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'متن جایگزین برای تصویر'
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('حجم فایل نباید بیش از 5 مگابایت باشد.')

            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise forms.ValidationError('فقط فایل‌های تصویری مجاز هستند.')

        return image


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'description', 'file', 'file_type']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام فایل'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'توضیحات فایل'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'file_type': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('حجم فایل نباید بیش از 10 مگابایت باشد.')

        return file