# users/context_processors.py
from users.models import AdminMessage


def admin_notifications(request):
    """Add admin message notifications to all admin pages"""
    context = {}

    # Only add notifications for admin users
    if request.user.is_authenticated and request.user.is_staff:
        try:
            unread_messages = AdminMessage.objects.filter(status='unread').order_by('-created_at')[:5]
            context.update({
                'unread_admin_messages': unread_messages,
                'unread_messages_count': unread_messages.count(),
            })
        except Exception:
            context.update({
                'unread_admin_messages': [],
                'unread_messages_count': 0,
            })

    return context