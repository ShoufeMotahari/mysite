import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from filemanager.forms.bulkImage_process_form import BulkImageProcessForm
from filemanager.forms.image_gallery_form import ImageSearchForm
from filemanager.forms.image_upload_form import ImageUploadForm
from filemanager.models import ImageGallery, ImageUpload

logger = logging.getLogger(__name__)

@login_required
def image_list(request):
    """List all images with search and filtering"""
    form = ImageSearchForm(request.GET or None)
    images = ImageUpload.objects.filter(uploaded_by=request.user, is_active=True)

    if form.is_valid():
        # Apply search filters
        search = form.cleaned_data.get("search")
        if search:
            images = images.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        minification_level = form.cleaned_data.get("minification_level")
        if minification_level:
            images = images.filter(minification_level=minification_level)

        resize_option = form.cleaned_data.get("resize_option")
        if resize_option:
            images = images.filter(resize_option=resize_option)

        convert_to_webp = form.cleaned_data.get("convert_to_webp")
        if convert_to_webp:
            images = images.filter(convert_to_webp=(convert_to_webp == "True"))

        processing_status = form.cleaned_data.get("processing_status")
        if processing_status:
            images = images.filter(processing_status=processing_status)

    # Order by creation date
    images = images.order_by("-created_at")

    # Pagination
    paginator = Paginator(images, 12)  # 12 images per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "form": form,
    }
    return render(request, "filemanager/image_list.html", context)


@login_required
def image_detail(request, pk):
    """Image detail view"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)

    # Get galleries containing this image
    galleries = ImageGallery.objects.filter(images=image, created_by=request.user)

    context = {
        "image": image,
        "galleries": galleries,
    }
    return render(request, "filemanager/image_detail.html", context)


@login_required
def image_upload(request):
    """Upload new image"""
    if request.method == "POST":
        form = ImageUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            image = form.save()
            messages.success(
                request, "تصویر با موفقیت آپلود شد و در صف پردازش قرار گرفت."
            )
            logger.info(f"Image uploaded: {image.title} by {request.user.username}")
            return redirect("filemanager:image_detail", pk=image.pk)
        else:
            messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")
    else:
        form = ImageUploadForm(user=request.user)

    return render(request, "filemanager/image_upload.html", {"form": form})


@login_required
def image_edit(request, pk):
    """Edit image"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)

    if request.method == "POST":
        form = ImageUploadForm(
            request.POST, request.FILES, instance=image, user=request.user
        )
        if form.is_valid():
            # Check if processing settings changed
            old_settings = {
                "minification_level": image.minification_level,
                "resize_option": image.resize_option,
                "convert_to_webp": image.convert_to_webp,
            }

            updated_image = form.save()

            new_settings = {
                "minification_level": updated_image.minification_level,
                "resize_option": updated_image.resize_option,
                "convert_to_webp": updated_image.convert_to_webp,
            }

            # If processing settings changed, trigger reprocessing
            if old_settings != new_settings:
                updated_image.processing_status = "pending"
                updated_image.save(update_fields=["processing_status"])
                updated_image.process_image_async()
                messages.success(request, "تصویر بروزرسانی شد و مجدداً پردازش خواهد شد.")
            else:
                messages.success(request, "تصویر با موفقیت بروزرسانی شد.")

            logger.info(f"Image updated: {image.title} by {request.user.username}")
            return redirect("filemanager:image_detail", pk=image.pk)
        else:
            messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")
    else:
        form = ImageUploadForm(instance=image, user=request.user)

    return render(
        request, "filemanager/image_edit.html", {"form": form, "image": image}
    )


@login_required
@require_POST
def image_delete(request, pk):
    """Delete image (soft delete)"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)
    image.is_active = False
    image.save(update_fields=["is_active"])
    messages.success(request, "تصویر با موفقیت حذف شد.")
    logger.info(f"Image deleted: {image.title} by {request.user.username}")
    return redirect("filemanager:image_list")


@login_required
@require_POST
def image_reprocess(request, pk):
    """Reprocess image with current settings"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)

    if image.reprocess_image():
        messages.success(request, "تصویر مجدداً پردازش شد.")
        logger.info(f"Image reprocessed: {image.title} by {request.user.username}")
    else:
        messages.error(request, "خطا در پردازش مجدد تصویر.")
        logger.error(f"Failed to reprocess image: {image.title}")

    return redirect("filemanager:image_detail", pk=image.pk)


@login_required
def bulk_image_process(request):
    """Bulk process multiple images"""
    if request.method == "POST":
        form = BulkImageProcessForm(request.POST, user=request.user)
        if form.is_valid():
            # Get images to process
            if form.cleaned_data["apply_to_all"]:
                images = ImageUpload.objects.filter(
                    uploaded_by=request.user, is_active=True
                )
            else:
                images = form.cleaned_data["selected_images"]

            # Apply processing settings
            processed_count = 0
            for image in images:
                settings_changed = False

                if form.cleaned_data["minification_level"]:
                    image.minification_level = form.cleaned_data["minification_level"]
                    settings_changed = True

                if form.cleaned_data["resize_option"]:
                    image.resize_option = form.cleaned_data["resize_option"]
                    settings_changed = True

                if form.cleaned_data["convert_to_webp"]:
                    image.convert_to_webp = True
                    settings_changed = True

                if form.cleaned_data["maintain_aspect_ratio"] is not None:
                    image.maintain_aspect_ratio = form.cleaned_data[
                        "maintain_aspect_ratio"
                    ]
                    settings_changed = True

                if settings_changed:
                    image.processing_status = "pending"
                    image.save()
                    image.process_image_async()
                    processed_count += 1

            messages.success(request, f"{processed_count} تصویر برای پردازش انتخاب شد.")
            logger.info(
                f"Bulk processing initiated for {processed_count} images by {request.user.username}"
            )
            return redirect("filemanager:image_list")
        else:
            messages.error(request, "لطفاً تنظیمات فرم را بررسی کنید.")
    else:
        form = BulkImageProcessForm(user=request.user)

    return render(request, "filemanager/bulk_image_process.html", {"form": form})
