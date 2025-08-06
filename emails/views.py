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
    sending_broadcasts = EmailBroadcast.objects.filter(status='sending').count()

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

    # Daily statistics for the last 7 days
    daily_stats = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        sent_count = EmailLog.objects.filter(
            sent_at__date=date,
            status='sent'
        ).count()
        failed_count = EmailLog.objects.filter(
            sent_at__date=date,
            status='failed'
        ).count()
        daily_stats.append({
            'date': date,
            'sent': sent_count,
            'failed': failed_count,
            'total': sent_count + failed_count
        })

    context = {
        'total_broadcasts': total_broadcasts,
        'sent_broadcasts': sent_broadcasts,
        'failed_broadcasts': failed_broadcasts,
        'draft_broadcasts': draft_broadcasts,
        'sending_broadcasts': sending_broadcasts,
        'recent_broadcasts': recent_broadcasts,
        'success_rate': round(success_rate, 2),
        'total_sent': total_sent,
        'total_failed': total_failed,
        'daily_stats': daily_stats,
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
    if status_filter and status_filter != 'all':
        logs = logs.filter(status=status_filter)
        logger.debug(f"Email logs filtered by status: {status_filter}")

    # Filter by broadcast if requested
    broadcast_filter = request.GET.get('broadcast')
    if broadcast_filter and broadcast_filter != 'all':
        try:
            broadcast_id = int(broadcast_filter)
            logs = logs.filter(broadcast_id=broadcast_id)
            logger.debug(f"Email logs filtered by broadcast: {broadcast_id}")
        except ValueError:
            logger.warning(f"Invalid broadcast filter value: {broadcast_filter}")

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        logs = logs.filter(
            Q(recipient__email__icontains=search_query) |
            Q(broadcast__subject__icontains=search_query) |
            Q(error_message__icontains=search_query)
        )
        logger.debug(f"Email logs searched for: {search_query}")

    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get available broadcasts for filter dropdown
    broadcasts = EmailBroadcast.objects.all().order_by('-created_at')[:100]  # Limit for performance

    context = {
        'page_obj': page_obj,
        'broadcasts': broadcasts,
        'current_status': status_filter,
        'current_broadcast': broadcast_filter,
        'search_query': search_query,
        'total_logs': logs.count(),
    }

    return render(request, 'emails/logs.html', context)


@staff_member_required
def view_log_file(request):
    """
    View to display the email log file content
    """
    logger.info(f"Email log file accessed by {request.user.username}")

    # Try different possible log file locations
    possible_log_paths = [
        os.path.join(settings.BASE_DIR, 'logs', 'email_tasks.log'),
        os.path.join(settings.BASE_DIR, 'logs', 'emails.log'),
        'logs/email_tasks.log',
        'logs/emails.log',
    ]

    # Check if LOG_DIR is defined in settings
    if hasattr(settings, 'LOG_DIR'):
        possible_log_paths.insert(0, os.path.join(settings.LOG_DIR, 'email_tasks.log'))
        possible_log_paths.insert(1, os.path.join(settings.LOG_DIR, 'emails.log'))

    log_file_path = None
    for path in possible_log_paths:
        if os.path.exists(path):
            log_file_path = path
            break

    if not log_file_path:
        logger.warning(f"Email log file not found in any of these locations: {possible_log_paths}")
        return render(request, 'emails/log_file.html', {
            'error': 'Log file not found',
            'searched_paths': possible_log_paths,
        })

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Get last 1000 lines for performance
            lines = f.readlines()[-1000:]
            log_content = ''.join(lines)

        return render(request, 'emails/log_file.html', {
            'log_content': log_content,
            'log_file_path': log_file_path,
            'line_count': len(lines),
        })

    except Exception as e:
        logger.error(f"Error reading log file {log_file_path}: {str(e)}")
        return render(request, 'emails/log_file.html', {
            'error': f'Error reading log file: {str(e)}',
            'log_file_path': log_file_path,
        })


@staff_member_required
def broadcast_detail(request, broadcast_id):
    """
    View to display detailed information about a specific broadcast
    """
    logger.info(f"Broadcast detail accessed by {request.user.username} for broadcast {broadcast_id}")

    try:
        broadcast = EmailBroadcast.objects.get(id=broadcast_id)
    except EmailBroadcast.DoesNotExist:
        logger.warning(f"Broadcast {broadcast_id} not found")
        return render(request, 'emails/broadcast_not_found.html', {'broadcast_id': broadcast_id})

    # Get logs for this broadcast
    logs = EmailLog.objects.filter(broadcast=broadcast).select_related('recipient').order_by('-sent_at')

    # Statistics for this broadcast
    total_logs = logs.count()
    sent_logs = logs.filter(status='sent').count()
    failed_logs = logs.filter(status='failed').count()

    # Pagination for logs
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'broadcast': broadcast,
        'page_obj': page_obj,
        'total_logs': total_logs,
        'sent_logs': sent_logs,
        'failed_logs': failed_logs,
        'success_rate': round((sent_logs / total_logs * 100) if total_logs > 0 else 0, 2),
    }

    return render(request, 'emails/broadcast_detail.html', context)


@staff_member_required
def test_email_logging(request):
    """
    Test function to generate sample log entries (for development only)
    """
    if not settings.DEBUG:
        return JsonResponse({'error': 'This endpoint is only available in DEBUG mode'}, status=403)

    logger.debug("This is a DEBUG message for email testing")
    logger.info("This is an INFO message for email testing")
    logger.warning("This is a WARNING message for email testing")
    logger.error("This is an ERROR message for email testing")

    return JsonResponse({
        'message': 'Test log entries created successfully',
        'timestamp': timezone.now().isoformat(),
        'user': request.user.username
    })


@staff_member_required
def email_dashboard(request):
    """
    Main dashboard view with quick stats and recent activity
    """
    logger.info(f"Email dashboard accessed by {request.user.username}")

    # Quick statistics
    total_broadcasts = EmailBroadcast.objects.count()
    active_broadcasts = EmailBroadcast.objects.filter(status='sending').count()

    # Recent broadcasts (last 5)
    recent_broadcasts = EmailBroadcast.objects.order_by('-created_at')[:5]

    # Recent failed emails (last 10)
    recent_failures = EmailLog.objects.filter(
        status='failed'
    ).select_related('broadcast', 'recipient').order_by('-sent_at')[:10]

    # Today's statistics
    today = timezone.now().date()
    today_sent = EmailLog.objects.filter(sent_at__date=today, status='sent').count()
    today_failed = EmailLog.objects.filter(sent_at__date=today, status='failed').count()

    context = {
        'total_broadcasts': total_broadcasts,
        'active_broadcasts': active_broadcasts,
        'recent_broadcasts': recent_broadcasts,
        'recent_failures': recent_failures,
        'today_sent': today_sent,
        'today_failed': today_failed,
    }

    return render(request, 'emails/dashboard.html', context)