"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Import Google OAuth views directly
from users.views.view_googlelogin import google_login, google_callback

urlpatterns = [
    # path('emails/', include('emails.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('filemanager/', include('filemanager.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('sections/', include('sections.urls')),

    # ADDED: Direct Google OAuth URLs to match .env redirect URI
    path('accounts/login/google/', google_login, name='google_login_direct'),
    path('accounts/login/google/callback/', google_callback, name='google_callback_direct'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)