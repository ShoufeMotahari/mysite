from django.urls import path
from .views import signup_view, verify_view

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('verify/', verify_view, name='verify'),
]