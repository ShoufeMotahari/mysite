import logging

logger = logging.getLogger('comments')


def my_view(request):
    logger.info('کامنت')


from django.shortcuts import render

# Create your views here.
