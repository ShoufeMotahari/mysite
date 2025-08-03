from django.urls import path
from .views import home_view
from core.views import test_email_view
urlpatterns = [
    path('', home_view, name='home'),
    path('test-email/', test_email_view, name='test-email'),
]
