import logging

logger = logging.getLogger('dashboard')


def my_view(request):
    logger.info('دشبرد')


from django.shortcuts import render

# Create your views here.
