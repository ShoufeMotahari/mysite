import logging

logger = logging.getLogger('sections')


def my_view(request):
    logger.info('سکشن')


from django.shortcuts import render

# Create your views here.
