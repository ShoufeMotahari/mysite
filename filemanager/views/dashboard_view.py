import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from filemanager.models import Document, ImageGallery, ImageUpload

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """File management dashboard"""
    user_images = ImageUpload.objects.filter(uploaded_by=request.user, is_active=True)
    user_documents = Document.objects.filter(uploaded_by=request.user, is_active=True)
    user_galleries = ImageGallery.objects.filter(created_by=request.user)

    # Get recent items
    recent_images = user_images.order_by("-created_at")[:5]
    recent_documents = user_documents.order_by("-uploaded_at")[:5]
    recent_galleries = user_galleries.order_by("-created_at")[:3]

    # Calculate statistics
    ImageUpload.get_total_storage_used()
    user_storage = {
        "original": sum(img.original_size for img in user_images),
        "processed": sum(img.processed_size for img in user_images),
    }
    user_storage["total"] = user_storage["original"] + user_storage["processed"]
    user_storage["saved"] = user_storage["original"] - user_storage["processed"]

    context = {
        "recent_images": recent_images,
        "recent_documents": recent_documents,
        "recent_galleries": recent_galleries,
        "total_images": user_images.count(),
        "total_documents": user_documents.count(),
        "total_galleries": user_galleries.count(),
        "storage_stats": user_storage,
        "processing_images": user_images.filter(processing_status="processing").count(),
        "failed_images": user_images.filter(processing_status="failed").count(),
    }
    return render(request, "filemanager/dashboard.html", context)
