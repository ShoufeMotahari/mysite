import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from users.forms.forms import (
    ProfileUpdateForm,
    UserUpdateForm, CommentForm, SignupForm,
)
from users.models import User

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

    return render(request, 'registration/signup.html', {'form': form})


# Separate view for comments
def submit_comment_view(request):
    """Separate view for handling comments"""
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.save()

            # Send notification email
            try:
                from users.services.email_service import CommentEmailService
                CommentEmailService.send_comment_notification(comment)
            except Exception as e:
                logger.error(f"Failed to send comment notification: {e}")

            messages.success(request, 'نظر شما با موفقیت ثبت شد.')
            return redirect('comments_list')  # or wherever
    else:
        form = CommentForm()

    return render(request, 'comments/submit.html', {'form': form})