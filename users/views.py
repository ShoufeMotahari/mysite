import logging

logger = logging.getLogger('users')


def my_view(request):
    logger.info('یوزر')


from django.shortcuts import render

# Create your views here.
