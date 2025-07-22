from django.shortcuts import render
from django.http import HttpResponse
import logging
logger = logging.getLogger('core')
def home_view(request):
    return HttpResponse("<h1>من بالاخره اجرا شدم :)✅</h1>")
