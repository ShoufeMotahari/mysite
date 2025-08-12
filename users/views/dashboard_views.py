import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone

from users.models import PasswordEntry, User, UserComment
from users.services.email_service import CommentEmailService

logger = logging.getLogger("users")
User = get_user_model()


@login_required
def dashboard_view(request):
    # if not request.session.get('second_auth'):
    #     return redirect('dashboard')
    return render(request, "users/dashboard.html", {"user": request.user})


@login_required
def dashboard(request):
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )
    logger.info(f"Dashboard accessed - User: {request.user.username}, IP: {client_ip}")

    # Handle AJAX requests for comments
    if request.method == 'POST':
        return handle_comment_actions(request)

    try:
        # Get password entries
        password_entries = PasswordEntry.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        total_entries = password_entries.count()

        logger.info(
            f"Password entries retrieved - User: {request.user.username}, Count: {total_entries}"
        )

        # Pagination for password entries
        paginator = Paginator(password_entries, 10)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Get user comments
        user_comments = UserComment.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-created_at')

        logger.debug(
            f"Dashboard pagination - User: {request.user.username}, Page: {page_number}, Total pages: {paginator.num_pages}"
        )
        logger.info(
            f"User comments retrieved - User: {request.user.username}, Count: {user_comments.count()}"
        )

        context = {
            'page_obj': page_obj,
            'user_comments': user_comments,
            'user': request.user
        }

        return render(request, "users/dashboard.html", context)

    except Exception as e:
        logger.error(
            f"Dashboard error - User: {request.user.username}, IP: {client_ip}, Error: {str(e)}"
        )
        messages.error(request, "An error occurred while loading the dashboard.")
        return render(request, "users/dashboard.html", {"page_obj": None, "user_comments": []})


def handle_comment_actions(request):
    """Handle AJAX requests for comment operations"""
    try:
        action = request.POST.get('action')

        if action == 'add_comment':
            return add_comment(request)
        elif action == 'delete_comment':
            return delete_comment(request)
        elif action == 'edit_comment':
            return edit_comment(request)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action'
            })

    except Exception as e:
        logger.error(f"Comment action error - User: {request.user.username}, Error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در انجام عملیات'
        })


def add_comment(request):
    """Add a new comment"""
    try:
        subject = request.POST.get('subject', '').strip()
        content = request.POST.get('content', '').strip()

        # Validation
        if not subject or not content:
            return JsonResponse({
                'success': False,
                'error': 'موضوع و محتوا الزامی است'
            })

        if len(subject) > 200:
            return JsonResponse({
                'success': False,
                'error': 'موضوع نباید بیش از 200 کاراکتر باشد'
            })

        if len(content) > 1000:
            return JsonResponse({
                'success': False,
                'error': 'محتوا نباید بیش از 1000 کاراکتر باشد'
            })

        # Create comment
        comment = UserComment.objects.create(
            user=request.user,
            subject=subject,
            content=content
        )

        logger.info(f"Comment added - User: {request.user.username}, Comment ID: {comment.id}")

        # Send email notification to admins
        try:
            client_ip = request.META.get(
                "HTTP_X_FORWARDED_FOR",
                request.META.get("REMOTE_ADDR", "Unknown")
            )

            email_sent = CommentEmailService.send_comment_notification(comment, client_ip)

            if email_sent:
                logger.info(f"Email notification sent for comment {comment.id}")
            else:
                logger.warning(f"Email notification failed for comment {comment.id}")

        except Exception as e:
            logger.error(f"Error sending email notification for comment {comment.id}: {str(e)}")
            # Don't fail the comment creation if email fails

        # Return comment data
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'subject': comment.subject,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y/%m/%d %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Add comment error - User: {request.user.username}, Error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در ثبت نظر'
        })


def delete_comment(request):
    """Delete a comment"""
    try:
        comment_id = request.POST.get('comment_id')

        if not comment_id:
            return JsonResponse({
                'success': False,
                'error': 'شناسه نظر مشخص نشده'
            })

        comment = get_object_or_404(
            UserComment,
            id=comment_id,
            user=request.user,
            is_active=True
        )

        # Soft delete
        comment.is_active = False
        comment.save()

        logger.info(f"Comment deleted - User: {request.user.username}, Comment ID: {comment.id}")

        return JsonResponse({
            'success': True,
            'message': 'نظر حذف شد'
        })

    except UserComment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'نظر یافت نشد'
        })
    except Exception as e:
        logger.error(f"Delete comment error - User: {request.user.username}, Error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در حذف نظر'
        })


def edit_comment(request):
    """Edit a comment"""
    try:
        comment_id = request.POST.get('comment_id')
        subject = request.POST.get('subject', '').strip()
        content = request.POST.get('content', '').strip()

        if not comment_id:
            return JsonResponse({
                'success': False,
                'error': 'شناسه نظر مشخص نشده'
            })

        if not subject or not content:
            return JsonResponse({
                'success': False,
                'error': 'موضوع و محتوا الزامی است'
            })

        comment = get_object_or_404(
            UserComment,
            id=comment_id,
            user=request.user,
            is_active=True
        )

        # Validation
        if len(subject) > 200:
            return JsonResponse({
                'success': False,
                'error': 'موضوع نباید بیش از 200 کاراکتر باشد'
            })

        if len(content) > 1000:
            return JsonResponse({
                'success': False,
                'error': 'محتوا نباید بیش از 1000 کاراکتر باشد'
            })

        # Update comment
        comment.subject = subject
        comment.content = content
        comment.updated_at = timezone.now()
        comment.save()

        logger.info(f"Comment edited - User: {request.user.username}, Comment ID: {comment.id}")

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'subject': comment.subject,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y/%m/%d %H:%M'),
                'updated_at': comment.updated_at.strftime('%Y/%m/%d %H:%M')
            }
        })

    except UserComment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'نظر یافت نشد'
        })
    except Exception as e:
        logger.error(f"Edit comment error - User: {request.user.username}, Error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در ویرایش نظر'
        })


@login_required
def user_comments(request):
    """Separate view for managing user comments"""
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )

    logger.info(f"Comments page accessed - User: {request.user.username}, IP: {client_ip}")

    try:
        # Get user comments with pagination
        comments = UserComment.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-created_at')

        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            comments = comments.filter(
                subject__icontains=search_query
            ) | comments.filter(
                content__icontains=search_query
            )

        # Pagination
        paginator = Paginator(comments, 5)  # 5 comments per page
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'search_query': search_query,
            'total_comments': UserComment.objects.filter(user=request.user, is_active=True).count()
        }

        return render(request, 'users/comments.html', context)

    except Exception as e:
        logger.error(f"Comments page error - User: {request.user.username}, Error: {str(e)}")
        messages.error(request, "خطا در بارگذاری نظرات")
        return render(request, 'users/comments.html', {'page_obj': None})


@login_required
@require_POST
def bulk_delete_comments(request):
    """Bulk delete comments"""
    try:
        comment_ids = request.POST.getlist('comment_ids[]')

        if not comment_ids:
            return JsonResponse({
                'success': False,
                'error': 'هیچ نظری انتخاب نشده'
            })

        # Update selected comments
        deleted_count = UserComment.objects.filter(
            id__in=comment_ids,
            user=request.user,
            is_active=True
        ).update(is_active=False)

        logger.info(f"Bulk delete comments - User: {request.user.username}, Count: {deleted_count}")

        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} نظر حذف شد',
            'deleted_count': deleted_count
        })

    except Exception as e:
        logger.error(f"Bulk delete error - User: {request.user.username}, Error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در حذف نظرات'
        })


@login_required
def comment_statistics(request):
    """Get comment statistics for dashboard"""
    try:
        stats = {
            'total_comments': UserComment.objects.filter(user=request.user, is_active=True).count(),
            'comments_this_month': UserComment.objects.filter(
                user=request.user,
                is_active=True,
                created_at__month=timezone.now().month,
                created_at__year=timezone.now().year
            ).count(),
            'latest_comment': None
        }

        latest = UserComment.objects.filter(user=request.user, is_active=True).first()
        if latest:
            stats['latest_comment'] = {
                'subject': latest.subject,
                'created_at': latest.created_at.strftime('%Y/%m/%d %H:%M')
            }

        return JsonResponse({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Comment stats error - User: {request.user.username}, Error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'خطا در دریافت آمار'
        })