# from django.contrib import admin
# from django.contrib.auth.models import User
# from django.utils.html import format_html
# from .models import PasswordEntry
# import logging
#
# logger = logging.getLogger(__name__)
#
#
# @admin.register(PasswordEntry)
# class PasswordEntryAdmin(admin.ModelAdmin):
#     list_display = ['user', 'service_name', 'username', 'created_at', 'updated_at']
#     list_filter = ['created_at', 'updated_at']
#     search_fields = ['user__username', 'service_name', 'username']
#     readonly_fields = ['created_at', 'updated_at']
#     ordering = ['-created_at']
#
#     def get_readonly_fields(self, request, obj=None):
#         readonly_fields = list(self.readonly_fields)
#         if obj:  # Editing existing object
#             readonly_fields.append('password')  # Make password readonly when editing
#         return readonly_fields
#
#     def has_change_permission(self, request, obj=None):
#         has_permission = request.user.is_superuser
#         if obj:
#             logger.info(
#                 f"Admin change permission check - User: {request.user.username}, Object: {obj.service_name}, Permission: {has_permission}")
#         return has_permission
#
#     def has_delete_permission(self, request, obj=None):
#         has_permission = request.user.is_superuser
#         if obj:
#             logger.info(
#                 f"Admin delete permission check - User: {request.user.username}, Object: {obj.service_name}, Permission: {has_permission}")
#         return has_permission
#
#     def has_view_permission(self, request, obj=None):
#         has_permission = request.user.is_superuser
#         if obj:
#             logger.info(
#                 f"Admin view permission check - User: {request.user.username}, Object: {obj.service_name}, Permission: {has_permission}")
#         return has_permission
#
#     def save_model(self, request, obj, form, change):
#         if change:
#             logger.info(
#                 f"Admin updating password entry - Admin: {request.user.username}, Entry: {obj.service_name}, User: {obj.user.username}")
#         else:
#             logger.info(
#                 f"Admin creating password entry - Admin: {request.user.username}, Entry: {obj.service_name}, User: {obj.user.username}")
#
#         super().save_model(request, obj, form, change)
#
#     def delete_model(self, request, obj):
#         logger.info(
#             f"Admin deleting password entry - Admin: {request.user.username}, Entry: {obj.service_name}, User: {obj.user.username}")
#         super().delete_model(request, obj)
#
#     def changelist_view(self, request, extra_context=None):
#         logger.info(f"Admin changelist accessed - Admin: {request.user.username}")
#         return super().changelist_view(request, extra_context)
#
#     def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
#         if object_id:
#             logger.info(f"Admin change form accessed - Admin: {request.user.username}, Object ID: {object_id}")
#         else:
#             logger.info(f"Admin add form accessed - Admin: {request.user.username}")
#         return super().changeform_view(request, object_id, form_url, extra_context)
