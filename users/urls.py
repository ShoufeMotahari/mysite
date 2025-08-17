# users/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

from .views import dashboard_views
# Import views from different modules
from .views.auth_views import (
    activate_account_view,
    login_view,
    register,
    send_sms_view,
    signup_view,
    verify_login_view,
    verify_reset_password_view,
    verify_view,
    # New password management views
    # API views for password functionality
    generate_password_view,
    check_password_strength_view,
)
from .views.dashboard_views import dashboard_view, dashboard
from .views.logout_view import message_admin_logout_view, smart_logout_view
from .views.messaging_views import (
    admin_notifications_api,
    mark_message_read_api,
    message_admin_dashboard,
    message_detail_view,
    my_messages_view,
    send_message_view,
)
from .views.password_views import (
    add_password,forgot_password_view,resend_reset_code_view,
    delete_password,
    edit_password,
    reset_password_email_view,
    reset_password_view,
    view_password,    change_password_view,
    password_history_view,
    security_settings_view,
)
from .views.view_googlelogin import debug_oauth_config, google_callback, google_login
from .views.views import profile_edit, user_profile

app_name = "users"
urlpatterns = [
    # ========== AUTHENTICATION URLS ==========
    # Registration and Login
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", smart_logout_view, name="logout"),
    path("register/", register, name="register"),  # Alternative registration

    # Verification
    path("verify/", verify_view, name="verify"),
    path("verify-login/", verify_login_view, name="verify_login"),
    path("activate/", activate_account_view, name="activate"),

    # ========== PASSWORD RESET URLS ==========
    # Forgot Password Flow
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("verify-reset-password/", verify_reset_password_view, name="verify_reset_password"),
    path("reset-password/", reset_password_view, name="reset_password"),
    path("resend-reset-code/", resend_reset_code_view, name="resend_reset_code"),

    # Legacy password reset (keeping for compatibility)
    path("reset-password-email/", reset_password_email_view, name="reset_password_email"),

    # ========== PASSWORD MANAGEMENT URLS ==========
    # New Password Management Views
    path("change-password/", change_password_view, name="change_password"),
    path("password-history/", password_history_view, name="password_history"),
    path("security-settings/", security_settings_view, name="security_settings"),

    # Legacy Password Management (keeping for compatibility)
    path("add-password/", add_password, name="add_password"),
    path("view-password/<int:password_id>/", view_password, name="view_password"),
    path("edit-password/<int:password_id>/", edit_password, name="edit_password"),
    path("delete-password/<int:password_id>/", delete_password, name="delete_password"),

    # ========== API URLS FOR AJAX REQUESTS ==========
    path("api/generate-password/", generate_password_view, name="generate_password"),
    path("api/check-password-strength/", check_password_strength_view, name="check_password_strength"),
    path("api/notifications/", admin_notifications_api, name="admin_notifications_api"),
    path("api/mark-read/<int:message_id>/", mark_message_read_api, name="mark_message_read_api"),

    # ========== DASHBOARD AND PROFILE URLS ==========
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/edit/", profile_edit, name="profile_edit"),
    path("profile/<slug:slug>/", user_profile, name="user_profile"),

    # ========== MESSAGING URLS ==========
    # Message Admin URLs (restricted access)
    path("message_admin/", message_admin_dashboard, name="message_admin_dashboard"),
    path("message_admin/send/", send_message_view, name="send_message"),
    path("message_admin/my-messages/", my_messages_view, name="my_messages"),
    path("message_admin/message/<int:message_id>/", message_detail_view, name="message_detail"),
    path("message_admin/logout/", message_admin_logout_view, name="message_admin_logout"),

    # ========== GOOGLE OAUTH URLS ==========
    path("login/google/", google_login, name="google_login"),
    path("login/google/callback/", google_callback, name="google_callback"),

    # ========== UTILITY URLS ==========
    # Development and Testing
    path("send-sms/", send_sms_view, name="send_sms"),  # For development
    path("debug/oauth/", debug_oauth_config, name="debug_oauth_config"),  # Remove in production

    # ========== DJANGO AUTH URLS (FALLBACK) ==========
    # Default Django auth views (keeping as fallback)
    path("auth/login/", auth_views.LoginView.as_view(template_name="users/registration/login.html"), name="auth_login"),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="auth_logout"),
    path('comments/', dashboard_views.user_comments, name='user_comments'),
    path('comments/bulk-delete/', dashboard_views.bulk_delete_comments, name='bulk_delete_comments'),
    path('comments/stats/', dashboard_views.comment_statistics, name='comment_stats'),
]

# ========== URL MAPPING REFERENCE ==========
# This comment section shows the URL patterns for easy reference:

"""
Authentication URLs:
- /users/signup/ → signup_view
- /users/login/ → login_view  
- /users/logout/ → smart_logout_view
- /users/register/ → register (alternative)

Verification URLs:
- /users/verify/ → verify_view
- /users/verify-login/ → verify_login_view
- /users/activate/ → activate_account_view

Password Reset URLs:
- /users/forgot-password/ → forgot_password_view
- /users/verify-reset-password/ → verify_reset_password_view
- /users/reset-password/ → reset_password_view
- /users/resend-reset-code/ → resend_reset_code_view

Password Management URLs:
- /users/change-password/ → change_password_view (NEW)
- /users/password-history/ → password_history_view (NEW)
- /users/security-settings/ → security_settings_view (NEW)

API URLs:
- /users/api/generate-password/ → generate_password_view (NEW)
- /users/api/check-password-strength/ → check_password_strength_view (NEW)
- /users/api/notifications/ → admin_notifications_api
- /users/api/mark-read/<id>/ → mark_message_read_api

Dashboard and Profile URLs:
- /users/dashboard/ → dashboard_view
- /users/profile/edit/ → profile_edit
- /users/profile/<slug>/ → user_profile

HTML Templates Required:
- users/password/change_password.html
- users/password/password_history.html  
- users/password/security_settings.html
"""