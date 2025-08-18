# users/views/messaging_views.py
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from users.forms.messaging_forms import AdminMessageForm
from users.models import adminMessage

logger = logging.getLogger(__name__)
User = get_user_model()


def is_message_admin(user):
    """Check if user is a message admin (staff but not superuser)"""
    return (
            user.is_authenticated
            and user.is_staff
            and not user.is_superuser
            and user.user_type
            and user.user_type.slug == "message_admin"
    )


def is_superuser_admin(user):
    """Check if user is a superuser admin"""
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(is_message_admin)
def message_admin_dashboard(request):
    """Dashboard for message admins - restricted interface"""

    # Get user's sent messages
    sent_messages = AdminMessage.objects.filter(sender=request.user).order_by(
        "-created_at"
    )

    # Get recent messages for display
    recent_messages = sent_messages[:10]

    # Statistics
    stats = {
        "total_sent": sent_messages.count(),
        "unread_messages": sent_messages.filter(status="unread").count(),
        "read_messages": sent_messages.filter(status="read").count(),
        "archived_messages": sent_messages.filter(status="archived").count(),
    }

    context = {
        "recent_messages": recent_messages,
        "stats": stats,
        "user": request.user,
        "title": "پنل پیام‌رسانی ادمین",
    }

    logger.info(
        f"Message admin dashboard accessed by {request.user.get_display_name()}"
    )

    return render(request, "admin/messaging/message_admin_dashboard.html", context)


@login_required
@user_passes_test(is_message_admin)
def send_message_view(request):
    """View for message admins to send messages"""

    if request.method == "POST":
        form = AdminMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()

            logger.info(
                f"New admin message sent by {request.user.get_display_name()}: "
                f"'{message.subject}' with priority {message.priority}"
            )

            messages.success(request, f'پیام "{message.subject}" با موفقیت ارسال شد.')
            return redirect("users:message_admin_dashboard")
        else:
            messages.error(request, "لطفاً خطاهای فرم را برطرف کنید.")
    else:
        form = AdminMessageForm()

    context = {
        "form": form,
        "title": "ارسال پیام جدید",
    }

    return render(request, "admin/messaging/send_message.html", context)


@login_required
@user_passes_test(is_message_admin)
def my_messages_view(request):
    """View for message admins to see their sent messages"""

    # Get search query
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    # Base queryset
    messages_qs = AdminMessage.objects.filter(sender=request.user)

    # Apply filters
    if search_query:
        messages_qs = messages_qs.filter(
            Q(subject__icontains=search_query) | Q(message__icontains=search_query)
        )

    if status_filter:
        messages_qs = messages_qs.filter(status=status_filter)

    messages_qs = messages_qs.order_by("-created_at")

    # Pagination
    paginator = Paginator(messages_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "title": "پیام‌های ارسالی من",
        "status_choices": AdminMessage.STATUS_CHOICES,
    }

    return render(request, "admin/messaging/my_messages.html", context)


@login_required
@user_passes_test(is_message_admin)
def message_detail_view(request, message_id):
    """View for message admins to see details of their messages"""

    message = get_object_or_404(AdminMessage, id=message_id, sender=request.user)

    # Get replies
    replies = message.replies.all().order_by("created_at")

    context = {
        "message": message,
        "replies": replies,
        "title": f"جزئیات پیام: {message.subject}",
    }

    return render(request, "admin/messaging/message_detail.html", context)


@login_required
@user_passes_test(is_superuser_admin)
def admin_notifications_api(request):
    """API endpoint for getting unread message notifications"""

    unread_count = AdminMessage.get_unread_count()
    recent_messages = AdminMessage.get_recent_messages()

    notifications = []
    for msg in recent_messages:
        notifications.append(
            {
                "id": msg.id,
                "subject": msg.subject,
                "sender": msg.sender.get_display_name(),
                "priority": msg.priority,
                "priority_icon": msg.get_priority_icon(),
                "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M"),
                "url": f"/admin/users/adminmessage/{msg.id}/change/",
            }
        )

    return JsonResponse({"unread_count": unread_count, "notifications": notifications})


@login_required
@user_passes_test(is_superuser_admin)
def mark_message_read_api(request, message_id):
    """API endpoint for marking a message as read"""

    if request.method == "POST":
        try:
            message = get_object_or_404(AdminMessage, id=message_id)
            message.mark_as_read(request.user)

            return JsonResponse(
                {"success": True, "message": "پیام به عنوان خوانده شده علامت‌گذاری شد."}
            )
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
            return JsonResponse({"success": False, "error": "خطا در علامت‌گذاری پیام"})

    return JsonResponse({"success": False, "error": "روش نامعتبر"})
