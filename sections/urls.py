from django.urls import path
from . import views

app_name = 'sections'

urlpatterns = [
    # Public views
    path('', views.sections_list, name='sections_list'),
    path('<int:section_id>/', views.section_detail, name='section_detail'),
    path('slug/<slug:slug>/', views.section_by_slug, name='section_by_slug'),

    # API endpoints
    path('api/tree/', views.section_tree, name='api_tree'),
    path('api/navigation/', views.section_navigation, name='api_navigation'),

    # Admin views
    path('admin/preview/', views.admin_sections_preview, name='admin_preview'),
    path('admin/toggle/<int:section_id>/', views.admin_section_toggle_status, name='admin_toggle_status'),
    path('admin/bulk-action/', views.admin_sections_bulk_action, name='admin_bulk_action'),

    # Keep your original view
    path('my-view/', views.my_view, name='my_view'),
]