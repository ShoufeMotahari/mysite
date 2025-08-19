import logging
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from filemanager.forms.document_form import DocumentSearchForm, DocumentForm
from filemanager.models import Document

logger = logging.getLogger(__name__)


@login_required
def document_list(request):
    """List all documents with search and filtering"""
    form = DocumentSearchForm(request.GET or None)
    documents = Document.objects.filter(uploaded_by=request.user, is_active=True)

    if form.is_valid():
        # Apply search filters
        search = form.cleaned_data.get("search")
        if search:
            documents = documents.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        file_type = form.cleaned_data.get("file_type")
        if file_type:
            documents = documents.filter(file_type=file_type)

    # Order by upload date
    documents = documents.order_by("-uploaded_at")

    # Pagination
    paginator = Paginator(documents, 10)  # 10 documents per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "form": form,
    }
    return render(request, "filemanager/document_list.html", context)


@login_required
def document_detail(request, pk):
    """Document detail view"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    return render(request, "filemanager/document_detail.html", {"document": document})


@login_required
def document_upload(request):
    """Upload new document"""
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            document = form.save()
            messages.success(request, "فایل با موفقیت آپلود شد.")
            logger.info(
                f"Document uploaded: {document.name} by {request.user.username}"
            )
            return redirect("filemanager:document_detail", pk=document.pk)
        else:
            messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")
    else:
        form = DocumentForm(user=request.user)

    return render(request, "filemanager/document_upload.html", {"form": form})


@login_required
def document_edit(request, pk):
    """Edit document"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)

    if request.method == "POST":
        form = DocumentForm(
            request.POST, request.FILES, instance=document, user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "فایل با موفقیت بروزرسانی شد.")
            logger.info(f"Document updated: {document.name} by {request.user.username}")
            return redirect("filemanager:document_detail", pk=document.pk)
        else:
            messages.error(request, "لطفاً خطاهای فرم را بررسی کنید.")
    else:
        form = DocumentForm(instance=document, user=request.user)

    return render(
        request, "filemanager/document_edit.html", {"form": form, "document": document}
    )


@login_required
@require_POST
def document_delete(request, pk):
    """Delete document (soft delete)"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    document.is_active = False
    document.save(update_fields=["is_active"])
    messages.success(request, "فایل با موفقیت حذف شد.")
    logger.info(f"Document deleted: {document.name} by {request.user.username}")
    return redirect("filemanager:document_list")


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
        with open(file_path, "rb") as f:
            response = HttpResponse(f.read(), content_type="application/octet-stream")
            response["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
            response["Content-Length"] = os.path.getsize(file_path)

        logger.info(f"Document downloaded: {document.name} by {request.user.username}")
        return response

    except FileNotFoundError:
        logger.error(f"File not found for document {document.name}")
        messages.error(request, "فایل در سرور یافت نشد.")
        return redirect("filemanager:document_detail", pk=document.pk)
    except Exception as e:
        logger.error(f"Error downloading document {document.name}: {str(e)}")
        messages.error(request, "خطا در دانلود فایل.")
        return redirect("filemanager:document_detail", pk=document.pk)
