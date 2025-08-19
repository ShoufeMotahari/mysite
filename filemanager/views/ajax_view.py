import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from filemanager.models import Document, ImageUpload

logger = logging.getLogger(__name__)


@login_required
@require_POST
def image_delete_ajax(request, pk):
    """Delete image via AJAX"""
    try:
        image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)
        image.is_active = False
        image.save(update_fields=["is_active"])
        logger.info(f"Image deleted via AJAX: {image.title} by {request.user.username}")
        return JsonResponse({"success": True, "message": "تصویر حذف شد"})
    except Exception as e:
        logger.error(f"Error deleting image via AJAX: {str(e)}")
        return JsonResponse({"success": False, "message": "خطا در حذف تصویر"})


@login_required
@require_POST
def document_delete_ajax(request, pk):
    """Delete document via AJAX"""
    try:
        document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
        document.is_active = False
        document.save(update_fields=["is_active"])
        logger.info(
            f"Document deleted via AJAX: {document.name} by {request.user.username}"
        )
        return JsonResponse({"success": True, "message": "فایل حذف شد"})
    except Exception as e:
        logger.error(f"Error deleting document via AJAX: {str(e)}")
        return JsonResponse({"success": False, "message": "خطا در حذف فایل"})
