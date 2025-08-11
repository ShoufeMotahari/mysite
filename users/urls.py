from django.contrib.auth import views as auth_views
from django.urls import path

from .views.auth_views import (
    activate_account_view,
    forgot_password_view,
    login_view,
    register,
    resend_reset_code_view,
    send_sms_view,
    signup_view,
    verify_login_view,
    verify_reset_password_view,
    verify_view,
)
from .views.dashboard_views import dashboard_view
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
    add_password,
    delete_password,
    edit_password,
    reset_password_email_view,
    reset_password_view,
    view_password,
)
from .views.view_googlelogin import debug_oauth_config, google_callback, google_login
from .views.views import profile_edit, user_profile

app_name = "users"
urlpatterns = [
    # پروفایل
    path("profile/edit/", profile_edit, name="profile_edit"),
    path("profile/<slug:slug>/", user_profile, name="user_profile"),
    # ثبت‌نام و ورود
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),  # Updated to use new login_view
    path("verify/", verify_view, name="verify"),
    path("verify-login/", verify_login_view, name="verify-login"),
    path("logout/", smart_logout_view, name="logout"),
    path(
        "message_admin/logout/", message_admin_logout_view, name="message_admin_logout"
    ),
    # فراموشی رمز عبور
    path("forgot-password/", forgot_password_view, name="forgot-password"),
    # داشبورد
    path("dashboard/", dashboard_view, name="dashboard"),
    # فعال‌سازی
    path("activate/", activate_account_view, name="activate"),
    # بازیابی رمز عبور (existing views)
    path("reset-password/", reset_password_view, name="reset-password"),
    path(
        "reset-password-email/", reset_password_email_view, name="reset-password-email"
    ),
    # مدیریت پسوردها
    path("register/", register, name="register"),
    path("add-password/", add_password, name="add_password"),
    path("view-password/<int:password_id>/", view_password, name="view_password"),
    path("edit-password/<int:password_id>/", edit_password, name="edit_password"),
    path("delete-password/<int:password_id>/", delete_password, name="delete_password"),
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("verify-reset-password/",verify_reset_password_view,name="verify_reset_password" ),
    path("reset-password/", reset_password_view, name="reset_password"),
    path("resend-reset-code/", resend_reset_code_view, name="resend_reset_code"),
    # تست SMS (فقط برای توسعه)
    path("send-sms/", send_sms_view, name="send_sms"),
    # ورود و خروج پیش‌فرض Django
    path("auth/login/",auth_views.LoginView.as_view(template_name="users/registration/login.html"),name="auth_login" ),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="auth_logout"),
    # Message admin URLs (restricted access)

    path("message_admin/", message_admin_dashboard, name="message_admin_dashboard"),
    path("message_admin/send/", send_message_view, name="send_message"),
    path("message_admin/my-messages/", my_messages_view, name="my_messages"),
    path(  "message_admin/message/<int:message_id>/",message_detail_view,name="message_detail"),
    # API endpoints for superuser admins
    path("api/notifications/", admin_notifications_api, name="admin_notifications_api"),
    path("api/mark-read/<int:message_id>/",  mark_message_read_api, name="mark_message_read_api",),
    # FIXED: Google OAuth URLs (removed 'accounts/' prefix to match .env redirect URI)
    path("login/google/", google_login, name="google_login"),
    path("login/google/callback/", google_callback, name="google_callback"),
    # DEBUG: OAuth configuration checker (remove in production)
    path("debug/oauth/", debug_oauth_config, name="debug_oauth_config"),
]
