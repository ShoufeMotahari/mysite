import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from users.forms.forms import (
    ProfileUpdateForm,
    UserUpdateForm, CommentForm, SignupForm,
)
from users.models import User
from users.managers.email_manager import EmailManager, SendEmailCommand

logger = logging.getLogger("users")
User = get_user_model()


@login_required
def profile_edit(request):
    user = request.user
    profile = getattr(user, "profile", None)

    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect("profile_edit")
    else:
        u_form = UserUpdateForm(instance=user)
        p_form = ProfileUpdateForm(instance=profile)

    return render(
        request, "users/profile_edit.html", {"u_form": u_form, "p_form": p_form}
    )


def user_profile(request, slug):
    """Display user profile by slug"""
    user = get_object_or_404(User, slug=slug)
    profile = getattr(user, "profile", None)

    return render(
        request, "users/user_profile.html", {"profile_user": user, "profile": profile}
    )


def register_view(request):
    """User registration view - only handles user registration"""
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                # Create user
                user = form.save(commit=False)
                user.is_active = False  # Require verification
                user.save()

                # Send verification SMS/Email
                # ... your verification logic

                messages.success(request, 'ثبت نام با موفقیت انجام شد. کد تایید برای شما ارسال شد.')
                return redirect('verification_view')  # or wherever you want

            except Exception as e:
                logger.error(f"Registration error: {e}")
                messages.error(request, 'خطایی در ثبت نام رخ داد. لطفا دوباره تلاش کنید.')
        else:
            # Form has validation errors
            logger.warning(f"Registration form validation failed: {form.errors}")
    else:
        form = SignupForm()

    return render(request, 'users/signup.html', {'form': form})


@csrf_protect
def submit_comment_view(request):
    """Handle comment submission with better error handling"""
    if not request.user.is_authenticated:
        messages.error(request, 'برای ثبت نظر باید وارد شوید.')
        return redirect('login')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            try:
                # Use transaction to ensure data integrity
                with transaction.atomic():
                    comment = form.save(commit=False)
                    comment.user = request.user
                    comment.save()

                    logger.info(f"Comment saved successfully - ID: {comment.id}, User: {request.user.username}")

                    # Get user's IP address for email notification
                    user_ip = get_client_ip(request)

                    # Send notification email in a separate try-catch
                    try:
                        from users.services.email_service import CommentEmailService
                        email_sent = CommentEmailService.send_comment_notification(comment, user_ip)

                        if email_sent:
                            logger.info(f"Email notification sent for comment {comment.id}")
                        else:
                            logger.warning(f"Email notification failed for comment {comment.id}")

                    except Exception as email_error:
                        logger.error(f"Email notification error for comment {comment.id}: {email_error}")
                        # Don't fail the comment submission if email fails

                    messages.success(request, 'نظر شما با موفقیت ثبت شد.')

                    # Redirect to prevent form resubmission
                    return redirect('comments_list')

            except Exception as e:
                logger.error(f"Comment submission error: {e}")
                messages.error(request, 'خطایی در ثبت نظر رخ داد. لطفا دوباره تلاش کنید.')
        else:
            logger.warning(f"Comment form validation failed: {form.errors}")
            messages.error(request, 'لطفا اطلاعات را به درستی وارد کنید.')
    else:
        form = CommentForm()

    return render(request, 'users/submit.html', {'form': form})


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
