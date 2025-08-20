import logging

from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)
User = get_user_model()


class EmailForm(forms.Form):
    """Simplified email form for direct composition without database templates"""

    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        label="گیرندگان",
        required=False,
        help_text="کاربرانی که در لیست مدیریت انتخاب شده‌اند به صورت خودکار دریافت خواهند کرد"
    )

    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "موضوع ایمیل را وارد کنید",
                "dir": "rtl"
            }
        ),
        label="موضوع ایمیل",
        required=True,
        help_text="موضوع ایمیل که در inbox گیرندگان نمایش داده می‌شود"
    )

    content = forms.CharField(
        widget=CKEditorWidget(
            config_name='email_editor',
            attrs={
                'placeholder': 'محتوای ایمیل خود را اینجا بنویسید...',
                'dir': 'rtl'
            }
        ),
        label="محتوای ایمیل",
        required=True,
        help_text="از ویرایشگر HTML برای قالب‌بندی متن استفاده کنید"
    )

    send_as_html = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="ارسال به صورت HTML",
        help_text="فعال کردن این گزینه امکان استفاده از قالب‌بندی و استایل را فراهم می‌کند"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active users with valid emails
        self.fields['recipients'].queryset = (
            User.objects.filter(is_active=True, email__isnull=False)
            .exclude(email="")
            .order_by('username')
        )

    def clean_subject(self):
        subject = self.cleaned_data.get("subject")
        if not subject or not subject.strip():
            raise ValidationError("موضوع ایمیل نمی‌تواند خالی باشد.")

        # Remove excessive whitespace
        subject = subject.strip()

        # Check for reasonable length
        if len(subject) > 200:
            raise ValidationError("موضوع ایمیل نمی‌تواند بیش از 200 کاراکتر باشد.")

        return subject

    def clean_content(self):
        content = self.cleaned_data.get("content")
        if not content or not content.strip():
            raise ValidationError("محتوای ایمیل نمی‌تواند خالی باشد.")

        # Basic content validation
        content = content.strip()

        # Check minimum content length (after removing HTML tags for basic validation)
        import re
        text_content = re.sub(r'<[^>]+>', '', content).strip()
        if len(text_content) < 10:
            raise ValidationError("محتوای ایمیل باید حداقل 10 کاراکتر متن داشته باشد.")

        return content

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get("subject")
        content = cleaned_data.get("content")

        # Ensure both subject and content are provided
        if not subject or not content:
            raise ValidationError("هم موضوع و هم محتوای ایمیل باید پر شوند.")

        return cleaned_data


class QuickEmailTemplateForm(forms.Form):
    """Optional form for predefined quick templates (not stored in DB)"""

    QUICK_TEMPLATES = [
        ('welcome', 'خوش‌آمدگویی به کاربران جدید'),
        ('announcement', 'اطلاع‌رسانی عمومی'),
        ('maintenance', 'اطلاع‌رسانی تعمیرات سیستم'),
        ('newsletter', 'خبرنامه'),
        ('custom', 'قالب سفارشی'),
    ]

    template_type = forms.ChoiceField(
        choices=QUICK_TEMPLATES,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="قالب آماده",
        required=False,
        help_text="انتخاب قالب آماده برای شروع سریع"
    )

    @staticmethod
    def get_template_content(template_type):
        """Get predefined template content"""
        templates = {
            'welcome': {
                'subject': 'خوش آمدید به وب‌سایت ما!',
                'content': '''
                <div style="font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right;">
                    <h2 style="color: #366092;">خوش آمدید!</h2>
                    <p>کاربر گرامی،</p>
                    <p>از شما بابت عضویت در وب‌سایت ما متشکریم. امیدواریم تجربه خوبی داشته باشید.</p>
                    <p>با تشکر،<br>تیم پشتیبانی</p>
                </div>
                '''
            },
            'announcement': {
                'subject': 'اطلاع‌رسانی مهم',
                'content': '''
                <div style="font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right;">
                    <h2 style="color: #366092;">اطلاع‌رسانی</h2>
                    <p>کاربران گرامی،</p>
                    <p>[متن اطلاع‌رسانی خود را اینجا وارد کنید]</p>
                    <p>با تشکر،<br>تیم مدیریت</p>
                </div>
                '''
            },
            'maintenance': {
                'subject': 'اطلاع‌رسانی تعمیرات سیستم',
                'content': '''
                <div style="font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right;">
                    <h2 style="color: #ff6b35;">تعمیرات سیستم</h2>
                    <p>کاربران گرامی،</p>
                    <p>به اطلاع می‌رساند که سیستم برای تعمیرات برنامه‌ریزی شده موقتاً غیرفعال خواهد شد.</p>
                    <p><strong>زمان تعمیرات:</strong> [زمان را مشخص کنید]</p>
                    <p>از صبر و شکیبایی شما متشکریم.</p>
                    <p>با تشکر،<br>تیم فنی</p>
                </div>
                '''
            },
            'newsletter': {
                'subject': 'خبرنامه هفتگی',
                'content': '''
                <div style="font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right;">
                    <h2 style="color: #366092;">خبرنامه</h2>
                    <p>کاربران گرامی،</p>
                    <p>در ادامه آخرین اخبار و به‌روزرسانی‌های سایت را مطالعه کنید:</p>
                    <ul>
                        <li>[خبر اول]</li>
                        <li>[خبر دوم]</li>
                        <li>[خبر سوم]</li>
                    </ul>
                    <p>با تشکر،<br>تیم محتوا</p>
                </div>
                '''
            }
        }

        return templates.get(template_type, {
            'subject': '',
            'content': '''
            <div style="font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right;">
                <p>محتوای ایمیل خود را اینجا بنویسید...</p>
            </div>
            '''
        })