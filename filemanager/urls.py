from django.urls import path
from . import views

app_name = 'filemanager'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Photo URLs
    path('photos/', views.photo_list, name='photo_list'),
    path('photos/upload/', views.photo_upload, name='photo_upload'),
    path('photos/<int:pk>/', views.photo_detail, name='photo_detail'),
    path('photos/<int:pk>/edit/', views.photo_edit, name='photo_edit'),
    path('photos/<int:pk>/delete/', views.photo_delete, name='photo_delete'),
    path('photos/<int:pk>/delete-ajax/', views.photo_delete_ajax, name='photo_delete_ajax'),

    # Document URLs
    path('documents/', views.document_list, name='document_list'),
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:pk>/', views.document_detail, name='document_detail'),
    path('documents/<int:pk>/edit/', views.document_edit, name='document_edit'),
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
    path('documents/<int:pk>/delete-ajax/', views.document_delete_ajax, name='document_delete_ajax'),
    path('documents/<int:pk>/download/', views.document_download, name='document_download'),
]