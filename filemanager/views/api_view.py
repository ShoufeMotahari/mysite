import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from filemanager.models import Document, ImageUpload

logger = logging.getLogger(__name__)


@login_required
def storage_stats_api(request):
    """API endpoint for storage statistics"""
    user_images = ImageUpload.objects.filter(uploaded_by=request.user, is_active=True)
    user_documents = Document.objects.filter(uploaded_by=request.user, is_active=True)

    image_storage = {
        "original": sum(img.original_size for img in user_images),
        "processed": sum(img.processed_size for img in user_images),
    }
    image_storage["saved"] = image_storage["original"] - image_storage["processed"]

    document_storage = sum(doc.file_size or 0 for doc in user_documents)

    total_storage = (
            image_storage["original"] + image_storage["processed"] + document_storage
    )

    return JsonResponse(
        {
            "image_original": image_storage["original"],
            "image_processed": image_storage["processed"],
            "image_saved": image_storage["saved"],
            "document_storage": document_storage,
            "total_storage": total_storage,
        }
    )


@login_required
def compression_stats_api(request):
    """API endpoint for compression statistics"""
    user_images = ImageUpload.objects.filter(
        uploaded_by=request.user, is_active=True, compression_ratio__gt=0
    )

    if user_images.exists():
        total_original = sum(img.original_size for img in user_images)
        total_processed = sum(img.processed_size for img in user_images)
        total_saved = total_original - total_processed
        avg_compression = sum(img.compression_ratio for img in user_images) / len(
            user_images
        )

        return JsonResponse(
            {
                "total_original": total_original,
                "total_processed": total_processed,
                "total_saved": total_saved,
                "average_compression": avg_compression,
                "processed_count": len(user_images),
            }
        )
    else:
        return JsonResponse(
            {
                "total_original": 0,
                "total_processed": 0,
                "total_saved": 0,
                "average_compression": 0,
                "processed_count": 0,
            }
        )
