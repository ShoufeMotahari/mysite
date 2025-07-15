from django.urls import path
from . import views

app_name = 'emails'

urlpatterns = [
    path('statistics/', views.email_statistics, name='email_statistics'),
    path('logs/', views.email_logs, name='email_logs'),
    path('log-file/', views.view_log_file, name='view_log_file'),
    path('test-logging/', views.test_email_logging, name='test_email_logging'),
]