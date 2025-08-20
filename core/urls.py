# core/urls.py
from django.urls import path
from .views import (
    home_view,
    test_email_view,
    test_email_configuration_view,
    send_bulk_email_view,
    email_service_test_view,
    email_stats_view
)

app_name = 'core'

urlpatterns = [
    # Basic views
    path("", home_view, name="home"),

    # Email testing views
    path("test-email/", test_email_view, name="test-email"),
    path("test-email-config/", test_email_configuration_view, name="test-email-config"),
    path("email-service-test/", email_service_test_view, name="email-service-test"),

    path("send-bulk-email/", send_bulk_email_view, name="send-bulk-email"),
    path("email-stats/", email_stats_view, name="email-stats"),
]