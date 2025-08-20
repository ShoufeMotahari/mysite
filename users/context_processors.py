# users/context_processors.py - Create this file if it doesn't exist

import logging
from django.db import IntegrityError, OperationalError

from users.models.comment import Comment

logger = logging.getLogger('users')


def admin_notifications(request):
    """
    Safe context processor that won't break if models don't exist
    """
    context = {
        'unread_comments_count': 0,
        'recent_comments': [],
        'admin_notifications': [],
    }

    try:
        # Only run for staff users to avoid unnecessary queries
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
            from users.models import comment

            # Get unread comments count (only approved ones)
            context['unread_comments_count'] = Comment.objects.filter(
                is_active=True,
                is_approved=False  # Count unapproved comments for admin
            ).count()

            # Get recent comments (last 5)
            context['recent_comments'] = Comment.objects.filter(is_active=True).select_related('user').order_by('-created_at')[:5]

    except (ImportError, OperationalError, IntegrityError) as e:
        # Handle cases where:
        # - Model doesn't exist (ImportError)
        # - Database table doesn't exist (OperationalError)
        # - Database integrity issues (IntegrityError)
        logger.warning(f"Context processor error (safe to ignore during migrations): {e}")

    except Exception as e:
        logger.error(f"Unexpected error in admin_notifications context processor: {e}")

    return context