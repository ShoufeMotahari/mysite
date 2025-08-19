import logging
from typing import Dict
from django.conf import settings

from .email_base import EmailService
from .email_utils import get_admin_emails
from .email_templates import (
    render_email_templates,
    generate_fallback_comment_notification_content
)

logger = logging.getLogger(__name__)


class CommentEmailService:
    """Service for sending comment-related email notifications"""

    def __init__(self, email_service: EmailService = None):
        self.email_service = email_service or EmailService()

    def _prepare_email_context(self, comment, user_ip: str = None) -> Dict:
        """Prepare context for email templates"""
        return {
            'comment': comment,
            'user': comment.user,
            'user_ip': user_ip,
            'site_name': getattr(settings, 'SITE_NAME', 'Website'),
            'domain': getattr(settings, 'SITE_DOMAIN', 'example.com'),
        }

    def _get_email_subject(self, comment) -> str:
        """Generate email subject with safe handling"""
        prefix = getattr(settings, 'COMMENT_NOTIFICATION_SUBJECT_PREFIX', '[Site] ')
        user = comment.user

        # Safe handling of optional subject field
        if hasattr(comment, 'subject') and comment.subject and comment.subject.strip():
            subject_text = comment.subject.strip()[:50]
            if len(comment.subject) > 50:
                subject_text += "..."
        else:
            # Use first part of content if no subject
            subject_text = comment.content[:50] + "..." if len(comment.content) > 50 else comment.content

        subject = f"{prefix}New comment from {user.username} - {subject_text}"
        return subject

    def send_comment_notification(self, comment, user_ip: str = None) -> bool:
        """Send email notification to admins when a new comment is posted"""
        try:
            # Check if notifications are enabled
            if not getattr(settings, 'COMMENT_NOTIFICATION_ENABLED', True):
                logger.info(f"Comment notifications disabled - skipping for comment {comment.id}")
                return False

            # Get admin emails
            admin_emails = get_admin_emails()
            if not admin_emails:
                logger.warning("No admin emails configured for comment notifications")
                return False

            # Prepare email context
            context = self._prepare_email_context(comment, user_ip)

            # Generate subject
            subject = self._get_email_subject(comment)

            # Try to render templates, fallback to simple content
            try:
                html_content, text_content = render_email_templates('comment_notification', context)
            except Exception as template_error:
                logger.warning(f"Template rendering failed, using fallback: {template_error}")
                html_content, text_content = generate_fallback_comment_notification_content(comment, context)

            # Send email to each admin
            success_count = 0
            for admin_email in admin_emails:
                success, message = self.email_service.send_single_email(
                    recipient_email=admin_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                if success:
                    success_count += 1

            if success_count > 0:
                logger.info(
                    f"Comment notification sent to {success_count}/{len(admin_emails)} admins - Comment ID: {comment.id}")
                return True
            else:
                logger.error(f"Failed to send comment notification to any admin - Comment ID: {comment.id}")
                return False

        except Exception as e:
            logger.error(f"Error sending comment notification - Comment ID: {comment.id}, Error: {str(e)}")
            return False
