import re
from django.utils.text import slugify as django_slugify

def slugify(value):
    return django_slugify(value)

def validate_mobile(mobile):
    return bool(re.match(r'^09\d{9}$', mobile))
