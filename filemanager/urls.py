from django.urls import path

from  filemanager.views.image_view import *
from  filemanager.views.gallery_view import *
from  filemanager.views.document_view import *
from  filemanager.views.dashboard_view import *
from  filemanager.views.api_view import *
from  filemanager.views.ajax_view import *

app_name = "filemanager"

urlpatterns = [
    # Dashboard
    path("", dashboard, name="dashboard"),
    # Image URLs (updated from photos to images)
    path("images/", image_list, name="image_list"),
    path("images/upload/", image_upload, name="image_upload"),
    path("images/<int:pk>/", image_detail, name="image_detail"),
    path("images/<int:pk>/edit/", image_edit, name="image_edit"),
    path("images/<int:pk>/delete/", image_delete, name="image_delete"),
    path("images/<int:pk>/delete-ajax/",image_delete_ajax,name="image_delete_ajax" ),
    path("images/<int:pk>/reprocess/", image_reprocess, name="image_reprocess"),
    path("images/bulk-process/", bulk_image_process, name="bulk_image_process"),
    # Gallery URLs
    path("galleries/", gallery_list, name="gallery_list"),
    path("galleries/create/", gallery_create, name="gallery_create"),
    path("galleries/<int:pk>/", gallery_detail, name="gallery_detail"),
    path("galleries/<int:pk>/edit/", gallery_edit, name="gallery_edit"),
    path("galleries/<int:pk>/delete/", gallery_delete, name="gallery_delete"),
    # Document URLs
    path("documents/", document_list, name="document_list"),
    path("documents/upload/", document_upload, name="document_upload"),
    path("documents/<int:pk>/", document_detail, name="document_detail"),
    path("documents/<int:pk>/edit/", document_edit, name="document_edit"),
    path("documents/<int:pk>/delete/", document_delete, name="document_delete"),
    path("documents/<int:pk>/delete-ajax/",document_delete_ajax,name="document_delete_ajax"),
    path("documents/<int:pk>/download/",document_download,name="document_download"),
    # API/AJAX URLs
    path("api/storage-stats/", storage_stats_api, name="storage_stats_api"),
    path("api/compression-stats/",compression_stats_api,name="compression_stats_api"),
]
