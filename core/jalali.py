import jdatetime
from django.utils import timezone

def to_jalali(dt):
    """تبدیل datetime میلادی به شمسی"""
    if not dt:
        return ''
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    jdt = jdatetime.datetime.fromgregorian(datetime=dt)
    return jdt.strftime('%Y/%m/%d %H:%M')
