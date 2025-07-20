from django.db import models
from django_jalali.db import models as jmodels
from django.utils.translation import gettext_lazy as _

class BaseModel(models.Model):
    created_jalali = jmodels.jDateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد (شمسی)"))
    updated_jalali = jmodels.jDateTimeField(auto_now=True, verbose_name=_("تاریخ بروزرسانی (شمسی)"))

    class Meta:
        abstract = True
        ordering = ['-created_jalali']
