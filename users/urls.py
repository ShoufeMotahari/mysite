from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    profile_edit, user_profile,
    signup_view, verify_view, login_view, verify_login_view, dashboard_view,
    second_password_view, change_second_password_view, activate_account_view,
    forgot_password_view, reset_password_view, reset_password_email_view, logout_view,
    register, add_password, view_password, edit_password, delete_password
)

urlpatterns = [
    # پروفایل
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/<slug:slug>/', user_profile, name='user_profile'),

    # ثبت‌نام و ورود
    path('signup/', signup_view, name='signup'),
    path('verify/', verify_view, name='verify'),
    path('login/', login_view, name='login'),
    path('verify-login/', verify_login_view, name='verify-login'),
    path('logout/', logout_view, name='logout'),

    # داشبورد
    path('dashboard/', dashboard_view, name='dashboard'),

    # پسورد دوم
    path('second-password/', second_password_view, name='second-password'),
    path('change-second-password/', change_second_password_view, name='change-second-password'),

    # فعال‌سازی
    path('activate/', activate_account_view, name='activate'),

    # بازیابی رمز عبور
    path('forgot-password/', forgot_password_view, name='forgot-password'),
    path('reset-password/', reset_password_view, name='reset-password'),
    path('reset-password-email/', reset_password_email_view, name='reset-password-email'),

    # مدیریت پسوردها
    path('register/', register, name='register'),
    path('add-password/', add_password, name='add_password'),
    path('view-password/<int:password_id>/', view_password, name='view_password'),
    path('edit-password/<int:password_id>/', edit_password, name='edit_password'),
    path('delete-password/<int:password_id>/', delete_password, name='delete_password'),

    # ورود و خروج پیش‌فرض Django (برای login template)
    path('auth/login/', auth_views.LoginView.as_view(template_name='passwords/registration/login.html'), name='auth_login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='auth_logout'),
]
