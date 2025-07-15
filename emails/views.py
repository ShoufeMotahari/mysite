# Add this to your emails/views.py

import os
import logging
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import EmailBroadcast, EmailLog
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('emails')


@staff_member_required
def email_statistics(request):
    """
    View to display email statistics and recent logs
    """
    logger.info(f"Email statistics accessed by {request.user.username}")

    # Get statistics
    total_broadcasts = EmailBroadcast.objects.count()
    sent_broadcasts = EmailBroadcast.objects.filter(status='sent').count()
    failed_broadcasts = EmailBroadcast.objects.filter(status='failed').count()
    draft_broadcasts = EmailBroadcast.objects.filter(status='draft').count()

    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_broadcasts = EmailBroadcast.objects.filter(
        created_at__gte=thirty_days_ago
    ).order_by('-created_at')[:10]

    # Success rate
    total_sent = EmailLog.objects.filter(status='sent').count()
    total_failed = EmailLog.objects.filter(status='failed').count()
    total_attempts = total_sent + total_failed
    success_rate = (total_sent / total_attempts * 100) if total_attempts > 0 else 0

    context = {
        'total_broadcasts': total_broadcasts,
        'sent_broadcasts': sent_broadcasts,
        'failed_broadcasts': failed_broadcasts,
        'draft_broadcasts': draft_broadcasts,
        'recent_broadcasts': recent_broadcasts,
        'success_rate': round(success_rate, 2),
        'total_sent': total_sent,
        'total_failed': total_failed,
    }

    return render(request, 'emails/statistics.html', context)


@staff_member_required
def email_logs(request):
    """
    View to display detailed email logs with pagination
    """
    logger.info(f"Email logs accessed by {request.user.username}")

    # Get all logs with related data
    logs = EmailLog.objects.select_related('broadcast', 'recipient').order_by('-sent_at')

    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        logs = logs.filter(status=status_filter)
        logger.debug(f"Email logs filtered by status: {status_filter}")

    # Filter by broadcast if requested
    broadcast_filter = request.GET.get('broadcast')
    if broadcast_filter:
        logs = logs.filter(broadcast_id=broadcast_filter)
        logger.debug(f"Email logs filtered by broadcast: {broadcast_filter}")

    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get available broadcasts for filter dropdown
    broadcasts = EmailBroadcast.objects.all().order_by('-created_at')

    context = {
        'page_obj': page_obj,
        'broadcasts': broadcasts,
        'current_status': status_filter,
        'current_broadcast': broadcast_filter,
    }

    return render(request, 'emails/logs.html', context)


@staff_member_required
def view_log_file(request):
    """
    View to display the email log file content
    """
    logger.info(f"Email log file accessed by {request.user.username}")

    log_file_path = os.path.join(settings.LOG_DIR, 'emails.log')

    if not os.path.exists(log_file_path):
        logger.warning(f"Email log file not found: {log_file_path}")
        return JsonResponse({'error': 'Log file not found'}, status=404)

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Get last 1000 lines for performance
            lines = f.readlines()[-1000:]
            log_content = ''.join(lines)

        return render(request, 'emails/log_file.html', {
            'log_content': log_content,
            'log_file_path': log_file_path,
        })

    except Exception as e:
        logger.error(f"Error reading log file: {str(e)}")
        return JsonResponse({'error': f'Error reading log file: {str(e)}'}, status=500)


def test_email_logging(request):
    """
    Test function to generate sample log entries
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    logger.debug("This is a DEBUG message for email testing")
    logger.info("This is an INFO message for email testing")
    logger.warning("This is a WARNING message for email testing")
    logger.error("This is an ERROR message for email testing")

    return JsonResponse({'message': 'Test log entries created successfully'})


# Add this to your emails/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('statistics/', views.email_statistics, name='email_statistics'),
    path('logs/', views.email_logs, name='email_logs'),
    path('log-file/', views.view_log_file, name='view_log_file'),
    path('test-logging/', views.test_email_logging, name='test_email_logging'),
]