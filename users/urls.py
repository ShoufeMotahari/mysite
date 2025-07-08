from django.urls import path
from .views import profile_edit

urlpatterns = [
    path('profile/edit/', profile_edit, name='profile_edit'),
]