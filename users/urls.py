from django.urls import path
from django.contrib.auth import views as auth_views
from .views.auth_views import (
    signup_view, activate_account_view, login_view, forgot_password_view,
    send_sms_view, register, verify_view, verify_login_view, verify_reset_password_view, resend_reset_code_view
)
from .views.password_views import (
    reset_password_view, reset_password_email_view,
    add_password, view_password, edit_password, delete_password
)
from .views.dashboard_views import dashboard_view
from .views.views import profile_edit, user_profile
from .views.logout_view import logout_view

urlpatterns = [
    # پروفایل
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/<slug:slug>/', user_profile, name='user_profile'),

    # ثبت‌نام و ورود
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),  # Updated to use new login_view
    path('verify/', verify_view, name='verify'),
    path('verify-login/', verify_login_view, name='verify-login'),
    path('logout/', logout_view, name='logout'),

    # فراموشی رمز عبور
    path('forgot-password/', forgot_password_view, name='forgot-password'),

    # داشبورد
    path('dashboard/', dashboard_view, name='dashboard'),

    # فعال‌سازی
    path('activate/', activate_account_view, name='activate'),

    # بازیابی رمز عبور (existing views)
    path('reset-password/', reset_password_view, name='reset-password'),
    path('reset-password-email/', reset_password_email_view, name='reset-password-email'),

    # مدیریت پسوردها
    path('register/', register, name='register'),
    path('add-password/', add_password, name='add_password'),
    path('view-password/<int:password_id>/', view_password, name='view_password'),
    path('edit-password/<int:password_id>/', edit_password, name='edit_password'),
    path('delete-password/<int:password_id>/', delete_password, name='delete_password'),

    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('verify-reset-password/', verify_reset_password_view, name='verify_reset_password'),
    path('reset-password/', reset_password_view, name='reset_password'),
    path('resend-reset-code/', resend_reset_code_view, name='resend_reset_code'),

    # تست SMS (فقط برای توسعه)
    path('send-sms/', send_sms_view, name='send_sms'),

    # ورود و خروج پیش‌فرض Django
    path('auth/login/', auth_views.LoginView.as_view(template_name='users/registration/login.html'), name='auth_login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='auth_logout'),
]