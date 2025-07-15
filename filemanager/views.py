from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import Photo, Document
from .forms import PhotoForm, DocumentForm
import logging

logger = logging.getLogger('filemanager')


@login_required
def dashboard(request):
    """File management dashboard"""
    photos = Photo.objects.filter(uploaded_by=request.user, is_active=True)[:5]
    documents = Document.objects.filter(uploaded_by=request.user, is_active=True)[:5]

    context = {
        'photos': photos,
        'documents': documents,
        'total_photos': Photo.objects.filter(uploaded_by=request.user, is_active=True).count(),
        'total_documents': Document.objects.filter(uploaded_by=request.user, is_active=True).count(),
    }
    return render(request, 'filemanager/dashboard.html', context)


# Photo Views
@login_required
def photo_list(request):
    """List all photos"""
    photos = Photo.objects.filter(uploaded_by=request.user, is_active=True)

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        photos = photos.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(photos, 12)  # 12 photos per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'filemanager/photo_list.html', context)


@login_required
def photo_detail(request, pk):
    """Photo detail view"""
    photo = get_object_or_404(Photo, pk=pk, uploaded_by=request.user)
    return render(request, 'filemanager/photo_detail.html', {'photo': photo})


@login_required
def photo_upload(request):
    """Upload new photo"""
    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.uploaded_by = request.user
            photo.save()
            messages.success(request, 'تصویر با موفقیت آپلود شد.')
            logger.info(f'Photo uploaded: {photo.title} by {request.user.username}')
            return redirect('filemanager:photo_detail', pk=photo.pk)
    else:
        form = PhotoForm()

    return render(request, 'filemanager/photo_upload.html', {'form': form})


@login_required
def photo_edit(request, pk):
    """Edit photo"""
    photo = get_object_or_404(Photo, pk=pk, uploaded_by=request.user)

    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            form.save()
            messages.success(request, 'تصویر با موفقیت بروزرسانی شد.')
            logger.info(f'Photo updated: {photo.title} by {request.user.username}')
            return redirect('filemanager:photo_detail', pk=photo.pk)
    else:
        form = PhotoForm(instance=photo)

    return render(request, 'filemanager/photo_edit.html', {'form': form, 'photo': photo})


@login_required
@require_POST
def photo_delete(request, pk):
    """Delete photo"""
    photo = get_object_or_404(Photo, pk=pk, uploaded_by=request.user)
    photo.is_active = False  # Soft delete
    photo.save()
    messages.success(request, 'تصویر با موفقیت حذف شد.')
    logger.info(f'Photo deleted: {photo.title} by {request.user.username}')
    return redirect('filemanager:photo_list')


# Document Views
@login_required
def document_list(request):
    """List all documents"""
    documents = Document.objects.filter(uploaded_by=request.user, is_active=True)

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        documents = documents.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Filter by file type
    file_type = request.GET.get('type', '')
    if file_type:
        documents = documents.filter(file_type=file_type)

    # Pagination
    paginator = Paginator(documents, 10)  # 10 documents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'file_type': file_type,
        'file_types': Document.DOCUMENT_TYPES,
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
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'فایل با موفقیت آپلود شد.')
            logger.info(f'Document uploaded: {document.name} by {request.user.username}')
            return redirect('filemanager:document_detail', pk=document.pk)
    else:
        form = DocumentForm()

    return render(request, 'filemanager/document_upload.html', {'form': form})


@login_required
def document_edit(request, pk):
    """Edit document"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'فایل با موفقیت بروزرسانی شد.')
            logger.info(f'Document updated: {document.name} by {request.user.username}')
            return redirect('filemanager:document_detail', pk=document.pk)
    else:
        form = DocumentForm(instance=document)

    return render(request, 'filemanager/document_edit.html', {'form': form, 'document': document})


@login_required
@require_POST
def document_delete(request, pk):
    """Delete document"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    document.is_active = False  # Soft delete
    document.save()
    messages.success(request, 'فایل با موفقیت حذف شد.')
    logger.info(f'Document deleted: {document.name} by {request.user.username}')
    return redirect('filemanager:document_list')


@login_required
def document_download(request, pk):
    """Download document"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)

    try:
        # Increment download counter
        document.increment_download_count()

        # Create response with file
        response = HttpResponse(document.file.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{document.name}"'

        logger.info(f'Document downloaded: {document.name} by {request.user.username}')
        return response

    except Exception as e:
        logger.error(f'Error downloading document {document.name}: {str(e)}')
        messages.error(request, 'خطا در دانلود فایل.')
        return redirect('filemanager:document_detail', pk=document.pk)


# AJAX Views
@login_required
def photo_delete_ajax(request, pk):
    """Delete photo via AJAX"""
    if request.method == 'POST':
        try:
            photo = get_object_or_404(Photo, pk=pk, uploaded_by=request.user)
            photo.is_active = False
            photo.save()
            return JsonResponse({'success': True, 'message': 'تصویر حذف شد'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def document_delete_ajax(request, pk):
    """Delete document via AJAX"""
    if request.method == 'POST':
        try:
            document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
            document.is_active = False
            document.save()
            return JsonResponse({'success': True, 'message': 'فایل حذف شد'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


from django.shortcuts import render

