# core/views.py
import logging
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib import messages

from core.services.email_service.email_service import EmailTestService, get_email_service
from .managers.email_manager import get_email_manager, create_send_email_command
from .models import EmailTemplate

logger = logging.getLogger("core")


def home_view(request):
    """Main home view"""
    return HttpResponse("<h1>من بالاخره اجرا شدم :)✅</h1>")


def test_email_view(request):
    """Basic email test view"""
    try:
        logger.warning(f"📧 Trying to send email from: {settings.DEFAULT_FROM_EMAIL}")

        send_mail(
            subject="test1",
            message="test2.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["your_email@example.com"],  # آدرس ایمیل خودت رو بذار اینجا
            fail_silently=False,
        )

        return HttpResponse("✅ersal shod")
    except Exception as e:
        logger.error(f"❌ error {e}")
        return HttpResponse(f"❌eroor{e}")


@staff_member_required
@require_http_methods(["GET"])
def test_email_configuration_view(request):
    """Advanced email configuration test view"""
    try:
        result = EmailTestService.test_email_configuration()

        if result['success']:
            logger.info(f"✅ Email configuration test passed: {result['message']}")
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'details': result['details']
            })
        else:
            logger.warning(f"⚠️ Email configuration test failed: {result['message']}")
            return JsonResponse({
                'status': 'error',
                'message': result['message'],
                'details': result['details']
            }, status=400)

    except Exception as e:
        logger.error(f"❌ Email configuration test error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'Test failed with exception: {str(e)}'
        }, status=500)


@staff_member_required
def email_templates_view(request):
    """View to display email templates"""
    templates = EmailTemplate.objects.filter(is_active=True).order_by('-created_jalali')

    context = {
        'templates': templates,
        'total_templates': templates.count(),
    }

    return render(request, 'core/email_templates.html', context)


@staff_member_required
@require_http_methods(["POST"])
def send_bulk_email_view(request):
    """View to send bulk emails using email manager"""
    try:
        # Get form data
        template_id = request.POST.get('template_id')
        user_ids = request.POST.getlist('user_ids')  # List of user IDs
        custom_subject = request.POST.get('custom_subject', '').strip()
        custom_content = request.POST.get('custom_content', '').strip()

        # Validate inputs
        if not template_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Template ID is required'
            }, status=400)

        if not user_ids:
            return JsonResponse({
                'status': 'error',
                'message': 'At least one user must be selected'
            }, status=400)

        # Convert user_ids to integers
        try:
            user_ids = [int(uid) for uid in user_ids]
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid user IDs provided'
            }, status=400)

        # Validate template exists
        try:
            template = EmailTemplate.objects.get(id=template_id, is_active=True)
        except EmailTemplate.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Email template with ID {template_id} not found or inactive'
            }, status=404)

        # Create email manager and command
        email_manager = get_email_manager()

        command = create_send_email_command(
            template_id=template_id,
            user_ids=user_ids,
            sender=request.user,
            custom_subject=custom_subject or None,
            custom_content=custom_content or None
        )

        email_manager.add_command(command)

        # Execute commands
        results = email_manager.execute_commands()

        # Process results
        if results and len(results) > 0:
            success, message, details = results[0]  # We only have one command

            if success:
                logger.info(f"✅ Bulk email sent successfully by {request.user.username}")
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'details': {
                        'template_name': template.name,
                        'total_users': details.get('total_users', 0),
                        'sent_to': details.get('valid_users', 0),
                        'skipped': details.get('invalid_users', 0)
                    }
                })
            else:
                logger.error(f"❌ Bulk email failed for user {request.user.username}: {message}")
                return JsonResponse({
                    'status': 'error',
                    'message': message,
                    'details': details
                }, status=400)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No results returned from email manager'
            }, status=500)

    except Exception as e:
        logger.error(f"❌ Bulk email view error: {e}")
        logger.exception("Full exception details:")
        return JsonResponse({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=500)


@staff_member_required
def email_service_test_view(request):
    """View to test email service directly"""
    if request.method == 'GET':
        # Show test form
        User = get_user_model()
        active_users = User.objects.filter(is_active=True, email__isnull=False).exclude(email='')[:10]

        context = {
            'active_users': active_users,
            'test_users_count': active_users.count()
        }
        return render(request, 'core/email_service_test.html', context)

    elif request.method == 'POST':
        try:
            # Get form data
            subject = request.POST.get('subject', 'Test Email').strip()
            content = request.POST.get('content', 'This is a test email.').strip()
            user_ids = request.POST.getlist('user_ids')

            if not user_ids:
                messages.error(request, 'Please select at least one user')
                return redirect('email-service-test')

            # Get users
            User = get_user_model()
            users = User.objects.filter(id__in=user_ids)

            if not users.exists():
                messages.error(request, 'No valid users found')
                return redirect('email-service-test')

            # Send email using email service
            email_service = get_email_service()
            sender_info = f"{request.user.username} ({request.user.email})"

            success, message, details = email_service.send_email(
                recipients=users,
                subject=subject,
                content=content,
                sender_info=sender_info
            )

            if success:
                messages.success(request, f"✅ {message}")
                logger.info(f"Email service test successful: {details}")
            else:
                messages.error(request, f"❌ {message}")
                logger.error(f"Email service test failed: {message}")

            return redirect('email-service-test')

        except Exception as e:
            logger.error(f"Email service test error: {e}")
            messages.error(request, f"Error: {str(e)}")
            return redirect('email-service-test')


@staff_member_required
@require_http_methods(["GET"])
def email_stats_view(request):
    """View to show email statistics"""
    try:
        # Get basic stats
        User = get_user_model()
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        users_with_email = User.objects.filter(is_active=True, email__isnull=False).exclude(email='').count()

        # Email template stats
        total_templates = EmailTemplate.objects.count()
        active_templates = EmailTemplate.objects.filter(is_active=True).count()

        # Template types
        template_types = EmailTemplate.objects.filter(is_active=True).values('email_type').distinct()

        stats = {
            'users': {
                'total': total_users,
                'active': active_users,
                'with_email': users_with_email,
                'email_percentage': round((users_with_email / active_users * 100) if active_users > 0 else 0, 1)
            },
            'templates': {
                'total': total_templates,
                'active': active_templates,
                'types': [t['email_type'] for t in template_types]
            },
            'email_config': {
                'backend': getattr(settings, 'EMAIL_BACKEND', 'Not configured'),
                'host': getattr(settings, 'EMAIL_HOST', 'Not configured'),
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not configured')
            }
        }

        return JsonResponse({
            'status': 'success',
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Email stats error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)