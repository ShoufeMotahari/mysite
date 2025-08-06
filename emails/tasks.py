from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import EmailBroadcast, EmailLog
import logging
import time

User = get_user_model()
logger = logging.getLogger('emails')


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_broadcast_email(self, broadcast_id):
    """
    Send broadcast email to all active users
    """
    try:
        broadcast = EmailBroadcast.objects.get(id=broadcast_id)
        logger.info(f"Starting email broadcast task for broadcast ID: {broadcast_id}")

        # Get all active users with valid email addresses
        recipients = User.objects.filter(
            is_active=True,
            email__isnull=False
        ).exclude(email='')

        total_recipients = recipients.count()
        successful_sends = 0
        failed_sends = 0

        # Update broadcast status and counts
        broadcast.total_recipients = total_recipients
        broadcast.status = 'sending'
        broadcast.save()

        logger.info(f"Broadcast {broadcast_id}: Sending to {total_recipients} recipients")

        # Send emails to each recipient
        for i, recipient in enumerate(recipients, 1):
            try:
                # Update task progress
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i,
                        'total': total_recipients,
                        'status': f'Sending to {recipient.email}...'
                    }
                )

                # Send individual email
                send_mail(
                    subject=broadcast.subject,
                    message='',  # Plain text version (empty since we're using HTML)
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    html_message=broadcast.content,
                    fail_silently=False
                )

                # Log successful send
                EmailLog.objects.create(
                    broadcast=broadcast,
                    recipient=recipient,
                    status='sent'
                )

                successful_sends += 1
                logger.debug(f"Email sent successfully to {recipient.email}")

                # Small delay to prevent overwhelming email server
                time.sleep(0.1)

            except Exception as e:
                # Log failed send
                EmailLog.objects.create(
                    broadcast=broadcast,
                    recipient=recipient,
                    status='failed',
                    error_message=str(e)
                )

                failed_sends += 1
                logger.error(f"Failed to send email to {recipient.email}: {str(e)}")

        # Update broadcast with final results
        broadcast.successful_sends = successful_sends
        broadcast.failed_sends = failed_sends
        broadcast.status = 'sent' if failed_sends == 0 else 'failed'
        broadcast.sent_at = timezone.now()
        broadcast.save()

        logger.info(
            f"Broadcast {broadcast_id} completed: "
            f"{successful_sends} successful, {failed_sends} failed"
        )

        return {
            'broadcast_id': broadcast_id,
            'total_recipients': total_recipients,
            'successful_sends': successful_sends,
            'failed_sends': failed_sends,
            'status': 'completed'
        }

    except EmailBroadcast.DoesNotExist:
        logger.error(f"EmailBroadcast with ID {broadcast_id} does not exist")
        raise
    except Exception as e:
        logger.error(f"Error in send_broadcast_email task: {str(e)}")
        # Update broadcast status to failed
        try:
            broadcast = EmailBroadcast.objects.get(id=broadcast_id)
            broadcast.status = 'failed'
            broadcast.save()
        except:
            pass
        raise


@shared_task
def send_single_email(recipient_email, subject, content, from_email=None):
    """
    Send a single email (utility task)
    """
    try:
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL

        send_mail(
            subject=subject,
            message='',
            from_email=from_email,
            recipient_list=[recipient_email],
            html_message=content,
            fail_silently=False
        )

        logger.info(f"Single email sent successfully to {recipient_email}")
        return {'status': 'sent', 'recipient': recipient_email}

    except Exception as e:
        logger.error(f"Failed to send single email to {recipient_email}: {str(e)}")
        raise


@shared_task
def cleanup_old_email_logs():
    """
    Clean up old email logs (optional maintenance task)
    """
    from datetime import timedelta

    try:
        # Delete logs older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = EmailLog.objects.filter(sent_at__lt=cutoff_date).delete()[0]

        logger.info(f"Cleaned up {deleted_count} old email logs")
        return {'deleted_count': deleted_count}

    except Exception as e:
        logger.error(f"Error in cleanup_old_email_logs task: {str(e)}")
        raise