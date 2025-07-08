from django.shortcuts import render
from django.http import HttpResponse

def home_view(request):
    return HttpResponse("<h1>من بالاخره اجرا شدم :)✅</h1>")

import logging
logger = logging.getLogger('core')

def my_view(request):
    logger.info('صفحه اصلی')