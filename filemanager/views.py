from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied

from .models import ImageUpload, ImageGallery, Document
from .forms import (
    ImageUploadForm, ImageGalleryForm, DocumentForm,
    BulkImageProcessForm, ImageSearchForm, DocumentSearchForm
)
import logging
import os
from django.conf import settings

logger = logging.getLogger('filemanager')


@login_required
def dashboard(request):
    """File management dashboard"""
    user_images = ImageUpload.objects.filter(uploaded_by=request.user, is_active=True)
    user_documents = Document.objects.filter(uploaded_by=request.user, is_active=True)
    user_galleries = ImageGallery.objects.filter(created_by=request.user)

    # Get recent items
    recent_images = user_images.order_by('-created_at')[:5]
    recent_documents = user_documents.order_by('-uploaded_at')[:5]
    recent_galleries = user_galleries.order_by('-created_at')[:3]

    # Calculate statistics
    storage_stats = ImageUpload.get_total_storage_used()
    user_storage = {
        'original': sum(img.original_size for img in user_images),
        'processed': sum(img.processed_size for img in user_images),
    }
    user_storage['total'] = user_storage['original'] + user_storage['processed']
    user_storage['saved'] = user_storage['original'] - user_storage['processed']

    context = {
        'recent_images': recent_images,
        'recent_documents': recent_documents,
        'recent_galleries': recent_galleries,
        'total_images': user_images.count(),
        'total_documents': user_documents.count(),
        'total_galleries': user_galleries.count(),
        'storage_stats': user_storage,
        'processing_images': user_images.filter(processing_status='processing').count(),
        'failed_images': user_images.filter(processing_status='failed').count(),
    }
    return render(request, 'filemanager/dashboard.html', context)


# Image Views
@login_required
def image_list(request):
    """List all images with search and filtering"""
    form = ImageSearchForm(request.GET or None)
    images = ImageUpload.objects.filter(uploaded_by=request.user, is_active=True)

    if form.is_valid():
        # Apply search filters
        search = form.cleaned_data.get('search')
        if search:
            images = images.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        minification_level = form.cleaned_data.get('minification_level')
        if minification_level:
            images = images.filter(minification_level=minification_level)

        resize_option = form.cleaned_data.get('resize_option')
        if resize_option:
            images = images.filter(resize_option=resize_option)

        convert_to_webp = form.cleaned_data.get('convert_to_webp')
        if convert_to_webp:
            images = images.filter(convert_to_webp=(convert_to_webp == 'True'))

        processing_status = form.cleaned_data.get('processing_status')
        if processing_status:
            images = images.filter(processing_status=processing_status)

    # Order by creation date
    images = images.order_by('-created_at')

    # Pagination
    paginator = Paginator(images, 12)  # 12 images per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form': form,
    }
    return render(request, 'filemanager/image_list.html', context)


@login_required
def image_detail(request, pk):
    """Image detail view"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)

    # Get galleries containing this image
    galleries = ImageGallery.objects.filter(images=image, created_by=request.user)

    context = {
        'image': image,
        'galleries': galleries,
    }
    return render(request, 'filemanager/image_detail.html', context)


@login_required
def image_upload(request):
    """Upload new image"""
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            image = form.save()
            messages.success(request, 'تصویر با موفقیت آپلود شد و در صف پردازش قرار گرفت.')
            logger.info(f'Image uploaded: {image.title} by {request.user.username}')
            return redirect('filemanager:image_detail', pk=image.pk)
        else:
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    else:
        form = ImageUploadForm(user=request.user)

    return render(request, 'filemanager/image_upload.html', {'form': form})


@login_required
def image_edit(request, pk):
    """Edit image"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)

    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES, instance=image, user=request.user)
        if form.is_valid():
            # Check if processing settings changed
            old_settings = {
                'minification_level': image.minification_level,
                'resize_option': image.resize_option,
                'convert_to_webp': image.convert_to_webp,
            }

            updated_image = form.save()

            new_settings = {
                'minification_level': updated_image.minification_level,
                'resize_option': updated_image.resize_option,
                'convert_to_webp': updated_image.convert_to_webp,
            }

            # If processing settings changed, trigger reprocessing
            if old_settings != new_settings:
                updated_image.processing_status = 'pending'
                updated_image.save(update_fields=['processing_status'])
                updated_image.process_image_async()
                messages.success(request, 'تصویر بروزرسانی شد و مجدداً پردازش خواهد شد.')
            else:
                messages.success(request, 'تصویر با موفقیت بروزرسانی شد.')

            logger.info(f'Image updated: {image.title} by {request.user.username}')
            return redirect('filemanager:image_detail', pk=image.pk)
        else:
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    else:
        form = ImageUploadForm(instance=image, user=request.user)

    return render(request, 'filemanager/image_edit.html', {'form': form, 'image': image})


@login_required
@require_POST
def image_delete(request, pk):
    """Delete image (soft delete)"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)
    image.is_active = False
    image.save(update_fields=['is_active'])
    messages.success(request, 'تصویر با موفقیت حذف شد.')
    logger.info(f'Image deleted: {image.title} by {request.user.username}')
    return redirect('filemanager:image_list')


@login_required
@require_POST
def image_reprocess(request, pk):
    """Reprocess image with current settings"""
    image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)

    if image.reprocess_image():
        messages.success(request, 'تصویر مجدداً پردازش شد.')
        logger.info(f'Image reprocessed: {image.title} by {request.user.username}')
    else:
        messages.error(request, 'خطا در پردازش مجدد تصویر.')
        logger.error(f'Failed to reprocess image: {image.title}')

    return redirect('filemanager:image_detail', pk=image.pk)


@login_required
def bulk_image_process(request):
    """Bulk process multiple images"""
    if request.method == 'POST':
        form = BulkImageProcessForm(request.POST, user=request.user)
        if form.is_valid():
            # Get images to process
            if form.cleaned_data['apply_to_all']:
                images = ImageUpload.objects.filter(uploaded_by=request.user, is_active=True)
            else:
                images = form.cleaned_data['selected_images']

            # Apply processing settings
            processed_count = 0
            for image in images:
                settings_changed = False

                if form.cleaned_data['minification_level']:
                    image.minification_level = form.cleaned_data['minification_level']
                    settings_changed = True

                if form.cleaned_data['resize_option']:
                    image.resize_option = form.cleaned_data['resize_option']
                    settings_changed = True

                if form.cleaned_data['convert_to_webp']:
                    image.convert_to_webp = True
                    settings_changed = True

                if form.cleaned_data['maintain_aspect_ratio'] is not None:
                    image.maintain_aspect_ratio = form.cleaned_data['maintain_aspect_ratio']
                    settings_changed = True

                if settings_changed:
                    image.processing_status = 'pending'
                    image.save()
                    image.process_image_async()
                    processed_count += 1

            messages.success(request, f'{processed_count} تصویر برای پردازش انتخاب شد.')
            logger.info(f'Bulk processing initiated for {processed_count} images by {request.user.username}')
            return redirect('filemanager:image_list')
        else:
            messages.error(request, 'لطفاً تنظیمات فرم را بررسی کنید.')
    else:
        form = BulkImageProcessForm(user=request.user)

    return render(request, 'filemanager/bulk_image_process.html', {'form': form})


# Gallery Views
@login_required
def gallery_list(request):
    """List all galleries"""
    galleries = ImageGallery.objects.filter(created_by=request.user).order_by('-created_at')

    # Pagination
    paginator = Paginator(galleries, 9)  # 9 galleries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'filemanager/gallery_list.html', context)


@login_required
def gallery_detail(request, pk):
    """Gallery detail view"""
    gallery = get_object_or_404(ImageGallery, pk=pk, created_by=request.user)
    images = gallery.images.filter(is_active=True).order_by('-created_at')

    # Pagination for gallery images
    paginator = Paginator(images, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'gallery': gallery,
        'page_obj': page_obj,
    }
    return render(request, 'filemanager/gallery_detail.html', context)


@login_required
def gallery_create(request):
    """Create new gallery"""
    if request.method == 'POST':
        form = ImageGalleryForm(request.POST, user=request.user)
        if form.is_valid():
            gallery = form.save(commit=False)
            gallery.created_by = request.user
            gallery.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, 'گالری با موفقیت ایجاد شد.')
            logger.info(f'Gallery created: {gallery.name} by {request.user.username}')
            return redirect('filemanager:gallery_detail', pk=gallery.pk)
        else:
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    else:
        form = ImageGalleryForm(user=request.user)

    return render(request, 'filemanager/gallery_create.html', {'form': form})


@login_required
def gallery_edit(request, pk):
    """Edit gallery"""
    gallery = get_object_or_404(ImageGallery, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = ImageGalleryForm(request.POST, instance=gallery, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'گالری با موفقیت بروزرسانی شد.')
            logger.info(f'Gallery updated: {gallery.name} by {request.user.username}')
            return redirect('filemanager:gallery_detail', pk=gallery.pk)
        else:
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    else:
        form = ImageGalleryForm(instance=gallery, user=request.user)

    return render(request, 'filemanager/gallery_edit.html', {'form': form, 'gallery': gallery})


@login_required
@require_POST
def gallery_delete(request, pk):
    """Delete gallery"""
    gallery = get_object_or_404(ImageGallery, pk=pk, created_by=request.user)
    gallery_name = gallery.name
    gallery.delete()
    messages.success(request, f'گالری "{gallery_name}" با موفقیت حذف شد.')
    logger.info(f'Gallery deleted: {gallery_name} by {request.user.username}')
    return redirect('filemanager:gallery_list')


# Document Views
@login_required
def document_list(request):
    """List all documents with search and filtering"""
    form = DocumentSearchForm(request.GET or None)
    documents = Document.objects.filter(uploaded_by=request.user, is_active=True)

    if form.is_valid():
        # Apply search filters
        search = form.cleaned_data.get('search')
        if search:
            documents = documents.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        file_type = form.cleaned_data.get('file_type')
        if file_type:
            documents = documents.filter(file_type=file_type)

    # Order by upload date
    documents = documents.order_by('-uploaded_at')

    # Pagination
    paginator = Paginator(documents, 10)  # 10 documents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form': form,
    }
    return render(request, 'filemanager/document_list.html', context)


@login_required
def document_detail(request, pk):
    """Document detail view"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    return render(request, 'filemanager/document_detail.html', {'document': document})


@login_required
def document_upload(request):
    """Upload new document"""
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            document = form.save()
            messages.success(request, 'فایل با موفقیت آپلود شد.')
            logger.info(f'Document uploaded: {document.name} by {request.user.username}')
            return redirect('filemanager:document_detail', pk=document.pk)
        else:
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    else:
        form = DocumentForm(user=request.user)

    return render(request, 'filemanager/document_upload.html', {'form': form})


@login_required
def document_edit(request, pk):
    """Edit document"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'فایل با موفقیت بروزرسانی شد.')
            logger.info(f'Document updated: {document.name} by {request.user.username}')
            return redirect('filemanager:document_detail', pk=document.pk)
        else:
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    else:
        form = DocumentForm(instance=document, user=request.user)

    return render(request, 'filemanager/document_edit.html', {'form': form, 'document': document})


@login_required
@require_POST
def document_delete(request, pk):
    """Delete document (soft delete)"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    document.is_active = False
    document.save(update_fields=['is_active'])
    messages.success(request, 'فایل با موفقیت حذف شد.')
    logger.info(f'Document deleted: {document.name} by {request.user.username}')
    return redirect('filemanager:document_list')


@login_required
def document_download(request, pk):
    """Download document"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)

    try:
        # Check if file exists
        if not document.file:
            raise Http404("فایل یافت نشد")

        # Increment download counter
        document.increment_download_count()

        # Get file path and name
        file_path = document.file.path
        original_name = document.name
        file_extension = os.path.splitext(document.file.name)[1]

        # Create safe filename
        safe_filename = f"{original_name}{file_extension}"

        # Create response with file
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response['Content-Length'] = os.path.getsize(file_path)

        logger.info(f'Document downloaded: {document.name} by {request.user.username}')
        return response

    except FileNotFoundError:
        logger.error(f'File not found for document {document.name}')
        messages.error(request, 'فایل در سرور یافت نشد.')
        return redirect('filemanager:document_detail', pk=document.pk)
    except Exception as e:
        logger.error(f'Error downloading document {document.name}: {str(e)}')
        messages.error(request, 'خطا در دانلود فایل.')
        return redirect('filemanager:document_detail', pk=document.pk)


# AJAX Views
@login_required
@require_POST
def image_delete_ajax(request, pk):
    """Delete image via AJAX"""
    try:
        image = get_object_or_404(ImageUpload, pk=pk, uploaded_by=request.user)
        image.is_active = False
        image.save(update_fields=['is_active'])
        logger.info(f'Image deleted via AJAX: {image.title} by {request.user.username}')
        return JsonResponse({'success': True, 'message': 'تصویر حذف شد'})
    except Exception as e:
        logger.error(f'Error deleting image via AJAX: {str(e)}')
        return JsonResponse({'success': False, 'message': 'خطا در حذف تصویر'})


@login_required
@require_POST
def document_delete_ajax(request, pk):
    """Delete document via AJAX"""
    try:
        document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
        document.is_active = False
        document.save(update_fields=['is_active'])
        logger.info(f'Document deleted via AJAX: {document.name} by {request.user.username}')
        return JsonResponse({'success': True, 'message': 'فایل حذف شد'})
    except Exception as e:
        logger.error(f'Error deleting document via AJAX: {str(e)}')
        return JsonResponse({'success': False, 'message': 'خطا در حذف فایل'})


# API Views
@login_required
def storage_stats_api(request):
    """API endpoint for storage statistics"""
    user_images = ImageUpload.objects.filter(uploaded_by=request.user, is_active=True)
    user_documents = Document.objects.filter(uploaded_by=request.user, is_active=True)

    image_storage = {
        'original': sum(img.original_size for img in user_images),
        'processed': sum(img.processed_size for img in user_images),
    }
    image_storage['saved'] = image_storage['original'] - image_storage['processed']

    document_storage = sum(doc.file_size or 0 for doc in user_documents)

    total_storage = image_storage['original'] + image_storage['processed'] + document_storage

    return JsonResponse({
        'image_original': image_storage['original'],
        'image_processed': image_storage['processed'],
        'image_saved': image_storage['saved'],
        'document_storage': document_storage,
        'total_storage': total_storage,
    })


@login_required
def compression_stats_api(request):
    """API endpoint for compression statistics"""
    user_images = ImageUpload.objects.filter(
        uploaded_by=request.user,
        is_active=True,
        compression_ratio__gt=0
    )

    if user_images.exists():
        total_original = sum(img.original_size for img in user_images)
        total_processed = sum(img.processed_size for img in user_images)
        total_saved = total_original - total_processed
        avg_compression = sum(img.compression_ratio for img in user_images) / len(user_images)

        return JsonResponse({
            'total_original': total_original,
            'total_processed': total_processed,
            'total_saved': total_saved,
            'average_compression': avg_compression,
            'processed_count': len(user_images),
        })
    else:
        return JsonResponse({
            'total_original': 0,
            'total_processed': 0,
            'total_saved': 0,
            'average_compression': 0,
            'processed_count': 0,
        })