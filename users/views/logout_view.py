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

logger = logging.getLogger('users')
User = get_user_model()


def logout_view(request):
    logout(request)
    logger.info(f"User {User.mobile} already exists")
    # Debug: Print to console what's happening
    print("Logout successful, redirecting...")
    # Try redirecting to a URL that definitely exists
    return redirect('/users/login/')  # This should always work
