from django.contrib import admin

from django.contrib import admin
from .models import Profile
import django_jalali.admin as jadmin
from django_jalali.admin.filters import JDateFieldListFilter

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_jalali']
    list_filter = (
        ('created_jalali', JDateFieldListFilter),
    )

