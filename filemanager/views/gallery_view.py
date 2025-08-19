import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from filemanager.forms.image_gallery_form import ImageGalleryForm
from filemanager.models import ImageGallery

logger = logging.getLogger(__name__)


@login_required
def gallery_list(request):
    """List all galleries"""
    galleries = ImageGallery.objects.filter(created_by=request.user).order_by(
        "-created_at"
    )

    # Pagination
    paginator = Paginator(galleries, 9)  # 9 galleries per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
    }
    return render(request, "filemanager/gallery_list.html", context)


@login_required
def gallery_detail(request, pk):
    """Gallery detail view"""
    gallery = get_object_or_404(ImageGallery, pk=pk, created_by=request.user)
    images = gallery.images.filter(is_active=True).order_by("-created_at")

    # Pagination for gallery images
    paginator = Paginator(images, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "gallery": gallery,
        "page_obj": page_obj,
    }
    return render(request, "filemanager/gallery_detail.html", context)


@login_required
def gallery_create(request):
    """Create new gallery"""
    if request.method == "POST":
        form = ImageGalleryForm(request.POST, user=request.user)
        if form.is_valid():
            gallery = form.save(commit=False)
            gallery.created_by = request.user
            gallery.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, "گالری با موفقیت ایجاد شد.")
            logger.info(f"Gallery created: {gallery.name} by {request.user.username}")
            return redirect("filemanager:gallery_detail", pk=gallery.pk)
        else:
            messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")
    else:
        form = ImageGalleryForm(user=request.user)

    return render(request, "filemanager/gallery_create.html", {"form": form})


@login_required
def gallery_edit(request, pk):
    """Edit gallery"""
    gallery = get_object_or_404(ImageGallery, pk=pk, created_by=request.user)

    if request.method == "POST":
        form = ImageGalleryForm(request.POST, instance=gallery, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "گالری با موفقیت بروزرسانی شد.")
            logger.info(f"Gallery updated: {gallery.name} by {request.user.username}")
            return redirect("filemanager:gallery_detail", pk=gallery.pk)
        else:
            messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")
    else:
        form = ImageGalleryForm(instance=gallery, user=request.user)

    return render(
        request, "filemanager/gallery_edit.html", {"form": form, "gallery": gallery}
    )


@login_required
@require_POST
def gallery_delete(request, pk):
    """Delete gallery"""
    gallery = get_object_or_404(ImageGallery, pk=pk, created_by=request.user)
    gallery_name = gallery.name
    gallery.delete()
    messages.success(request, f'گالری "{gallery_name}" با موفقیت حذف شد.')
    logger.info(f"Gallery deleted: {gallery_name} by {request.user.username}")
    return redirect("filemanager:gallery_list")
