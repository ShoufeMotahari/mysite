from django.urls import path

from . import views

app_name = "filemanager"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Image URLs (updated from photos to images)
    path("images/", views.image_list, name="image_list"),
    path("images/upload/", views.image_upload, name="image_upload"),
    path("images/<int:pk>/", views.image_detail, name="image_detail"),
    path("images/<int:pk>/edit/", views.image_edit, name="image_edit"),
    path("images/<int:pk>/delete/", views.image_delete, name="image_delete"),
    path(
        "images/<int:pk>/delete-ajax/",
        views.image_delete_ajax,
        name="image_delete_ajax",
    ),
    path("images/<int:pk>/reprocess/", views.image_reprocess, name="image_reprocess"),
    path("images/bulk-process/", views.bulk_image_process, name="bulk_image_process"),
    # Gallery URLs
    path("galleries/", views.gallery_list, name="gallery_list"),
    path("galleries/create/", views.gallery_create, name="gallery_create"),
    path("galleries/<int:pk>/", views.gallery_detail, name="gallery_detail"),
    path("galleries/<int:pk>/edit/", views.gallery_edit, name="gallery_edit"),
    path("galleries/<int:pk>/delete/", views.gallery_delete, name="gallery_delete"),
    # Document URLs
    path("documents/", views.document_list, name="document_list"),
    path("documents/upload/", views.document_upload, name="document_upload"),
    path("documents/<int:pk>/", views.document_detail, name="document_detail"),
    path("documents/<int:pk>/edit/", views.document_edit, name="document_edit"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path(
        "documents/<int:pk>/delete-ajax/",
        views.document_delete_ajax,
        name="document_delete_ajax",
    ),
    path(
        "documents/<int:pk>/download/",
        views.document_download,
        name="document_download",
    ),
    # API/AJAX URLs
    path("api/storage-stats/", views.storage_stats_api, name="storage_stats_api"),
    path(
        "api/compression-stats/",
        views.compression_stats_api,
        name="compression_stats_api",
    ),
]
