from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    signup_view, verify_view, login_view, verify_login_view, dashboard_view,
    second_password_view, change_second_password_view, activate_account_view,
    forgot_password_view, reset_password_view, reset_password_email_view
)

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('verify/', verify_view, name='verify'),
    path('login/', login_view, name='login'),
    path('verify-login/', verify_login_view, name='verify-login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('second-password/', second_password_view, name='second-password'),
    path('change-second-password/', change_second_password_view, name='change-second-password'),
    path('activate/', activate_account_view, name='activate'),

    # Password recovery URLs
    path('forgot-password/', forgot_password_view, name='forgot-password'),
    path('reset-password/', reset_password_view, name='reset-password'),
    path('reset-password-email/', reset_password_email_view, name='reset-password-email'),
]