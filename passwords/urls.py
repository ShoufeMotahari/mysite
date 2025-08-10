# File: urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="passwords/registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("add-password/", views.add_password, name="add_password"),
    path("view-password/<int:password_id>/", views.view_password, name="view_password"),
    path("edit-password/<int:password_id>/", views.edit_password, name="edit_password"),
    path(
        "delete-password/<int:password_id>/",
        views.delete_password,
        name="delete_password",
    ),
]
