from django.urls import path
from .views import submit_comment

urlpatterns = [
    path('submit/', submit_comment, name='submit-comment'),
]
