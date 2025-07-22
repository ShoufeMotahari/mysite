import logging
from users.forms.forms import UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import get_user_model
from django.http import JsonResponse
import random
import uuid
from users.forms.forms import SignupForm, LoginForm, ForgotPasswordForm
from core.sms import send_verification_sms
from core.email import send_activation_email, send_password_reset_email
from users.models import User, RegisterToken, VerificationToken
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import Http404
from users.forms.forms import CustomUserCreationForm, PasswordEntryForm
from users.models import PasswordEntry
from core.views import home_view

logger = logging.getLogger('users')
User = get_user_model()

@login_required
def profile_edit(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('profile_edit')
    else:
        u_form = UserUpdateForm(instance=user)
        p_form = ProfileUpdateForm(instance=profile)

    return render(request, 'users/profile_edit.html', {
        'u_form': u_form,
        'p_form': p_form
    })


def user_profile(request, slug):
    """Display user profile by slug"""
    user = get_object_or_404(User, slug=slug)
    profile = getattr(user, 'profile', None)

    return render(request, 'users/user_profile.html', {
        'profile_user': user,
        'profile': profile
    })
