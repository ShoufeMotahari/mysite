from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailBroadcast, EmailLog
import logging

User = get_user_model()
logger = logging.getLogger('emails')


def send_broadcast_email(broadcast_id):
    """
    Send broadcast email to all active users.
    This function can be called directly or wrapped in a Celery task for async processing.
    """
    logger.info(f"Starting email broadcast process for ID: {broadcast_id}")

    try:
        broadcast = EmailBroadcast.objects.get(id=broadcast_id)
        logger.info(f"Email broadcast found: '{broadcast.subject}' created by {broadcast.created_by.username}")

        # Get all active users with email addresses
        recipients = User.objects.filter(
            is_active=True,
            email__isnull=False
        ).exclude(email='')

        logger.info(f"Found {recipients.count()} active users with email addresses")

        successful_sends = 0
        failed_sends = 0

        for user in recipients:
            try:
                logger.debug(f"Sending email to {user.email} for broadcast {broadcast_id}")

                # Send individual email
                send_mail(
                    subject=broadcast.subject,
                    message='',  # Plain text version (empty since we're using HTML)
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=broadcast.content,
                    fail_silently=False
                )

                # Log successful send
                EmailLog.objects.create(
                    broadcast=broadcast,
                    recipient=user,
                    status='sent'
                )
                successful_sends += 1
                logger.debug(f"Successfully sent email to {user.email}")

            except Exception as e:
                # Log failed send
                EmailLog.objects.create(
                    broadcast=broadcast,
                    recipient=user,
                    status='failed',
                    error_message=str(e)
                )
                failed_sends += 1
                logger.error(f"Failed to send email to {user.email}: {str(e)}")

        # Update broadcast status
        broadcast.successful_sends = successful_sends
        broadcast.failed_sends = failed_sends
        broadcast.status = 'sent' if failed_sends == 0 else 'failed'
        broadcast.sent_at = timezone.now()
        broadcast.save()

        logger.info(f"Broadcast {broadcast.id} completed: {successful_sends} successful, {failed_sends} failed")

        if failed_sends > 0:
            logger.warning(
                f"Broadcast {broadcast.id} had {failed_sends} failed deliveries out of {successful_sends + failed_sends} total attempts")

    except EmailBroadcast.DoesNotExist:
        logger.error(f"EmailBroadcast with id {broadcast_id} does not exist")
        raise
    except Exception as e:
        logger.error(f"Critical error sending broadcast {broadcast_id}: {str(e)}")
        # Update broadcast status to failed
        try:
            broadcast = EmailBroadcast.objects.get(id=broadcast_id)
            broadcast.status = 'failed'
            broadcast.save()
            logger.info(f"Broadcast {broadcast_id} status updated to 'failed' due to critical error")
        except:
            logger.error(f"Could not update broadcast {broadcast_id} status to failed")
        raise


# Optional: Celery task wrapper for async processing
# Uncomment if you're using Celery
"""
from celery import shared_task

@shared_task
def send_broadcast_email_async(broadcast_id):
    return send_broadcast_email(broadcast_id)
"""