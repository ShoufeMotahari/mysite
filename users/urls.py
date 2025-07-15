from django.urls import path
from .views import profile_edit, user_profile

urlpatterns = [
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/<slug:slug>/', user_profile, name='user_profile'),
]