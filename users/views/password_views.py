import logging
from users.forms.forms import UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import get_user_model
from django.http import JsonResponse
import random
import uuid
from users.forms.forms import (SignupForm, LoginForm, ForgotPasswordForm)
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


def forgot_password_view(request):
    """New view for password recovery"""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']

            try:
                if '@' in identifier:
                    user = User.objects.get(email=identifier)
                else:
                    user = User.objects.get(mobile=identifier)

                # Generate tokens
                sms_code = str(random.randint(1, 9))
                email_token = str(uuid.uuid4())

                # Updated to match the new model structure
                RegisterToken.objects.update_or_create(
                    user=user,
                    defaults={'code': sms_code}
                )

                # Create verification token for email reset if needed
                if user.email:
                    VerificationToken.objects.update_or_create(
                        user=user,
                        token_type='password_reset',
                        defaults={
                            'token': sms_code,
                            'email_token': uuid.uuid4(),
                            'is_used': False
                        }
                    )

                # Send SMS code
                send_verification_sms(user.mobile, sms_code)

                # Send email if user has email
                if user.email:
                    verification_token = VerificationToken.objects.get(
                        user=user,
                        token_type='password_reset',
                        is_used=False
                    )
                    send_password_reset_email(user, str(verification_token.email_token))

                request.session['reset_user_id'] = user.id
                messages.success(request, "کد بازیابی به شماره موبایل و ایمیل شما ارسال شد.")
                return redirect('reset-password')

            except User.DoesNotExist:
                form.add_error('identifier', 'کاربری با این مشخصات یافت نشد.')
    else:
        form = ForgotPasswordForm()

    return render(request, 'users/forgot_password.html', {'form': form})


def reset_password_view(request):
    """New view for resetting password with SMS code"""
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('forgot-password')

    if request.method == 'POST':
        code = request.POST.get('code')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "رمزهای عبور مطابقت ندارند.")
            return render(request, 'users/reset_password.html')

        try:
            user = User.objects.get(id=user_id)
            token = RegisterToken.objects.get(user=user)

            if token.code == code and token.is_valid():
                user.set_password(new_password)
                user.save()
                token.delete()

                # Also mark verification token as used if exists
                try:
                    verification_token = VerificationToken.objects.get(
                        user=user,
                        token_type='password_reset',
                        is_used=False
                    )
                    verification_token.mark_as_used()
                except VerificationToken.DoesNotExist:
                    pass

                request.session.pop('reset_user_id', None)

                messages.success(request, "رمز عبور شما با موفقیت تغییر یافت.")
                return redirect('login')
            else:
                messages.error(request, "کد وارد شده اشتباه یا منقضی شده است.")
        except (User.DoesNotExist, RegisterToken.DoesNotExist):
            messages.error(request, "کاربر یا کد معتبر نیست.")

    return render(request, 'users/reset_password.html')


def reset_password_email_view(request):
    """New view for resetting password via email link"""
    token = request.GET.get('token')
    if not token:
        messages.error(request, "توکن وجود ندارد.")
        return redirect('login')

    try:
        # Updated to use VerificationToken instead of RegisterToken
        verification_token = VerificationToken.objects.get(
            email_token=token,
            token_type='password_reset',
            is_used=False
        )

        if not verification_token.is_valid():
            messages.error(request, "توکن منقضی شده است.")
            return redirect('forgot-password')

        user = verification_token.user

        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                messages.error(request, "رمزهای عبور مطابقت ندارند.")
                return render(request, 'users/reset_password_email.html', {'token': token})

            user.set_password(new_password)
            user.save()
            verification_token.mark_as_used()

            messages.success(request, "رمز عبور شما با موفقیت تغییر یافت.")
            return redirect('login')

        return render(request, 'users/reset_password_email.html', {'token': token})

    except VerificationToken.DoesNotExist:
        messages.error(request, "توکن معتبر نیست.")
        return redirect('forgot-password')


@login_required
def add_password(request):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    logger.info(f"Add password page accessed - User: {request.user.username}, IP: {client_ip}")

    if request.method == 'POST':
        logger.info(f"Add password form submitted - User: {request.user.username}, IP: {client_ip}")
        form = PasswordEntryForm(request.POST)

        if form.is_valid():
            try:
                password_entry = form.save(commit=False)
                password_entry.user = request.user

                logger.info(
                    f"Creating password entry - User: {request.user.username}, Service: {password_entry.service_name}, Username: {password_entry.username}")

                # Encrypt the password before saving
                password_entry.encrypt_password(form.cleaned_data['password'])
                password_entry.save()

                messages.success(request, 'Password added successfully!')
                logger.info(
                    f"Password entry added successfully - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_entry.pk}")
                return redirect('dashboard')

            except IntegrityError:
                logger.warning(
                    f"Duplicate password entry attempted - User: {request.user.username}, Service: {form.cleaned_data.get('service_name')}, Username: {form.cleaned_data.get('username')}")
                messages.error(request, 'A password for this service and username already exists.')
            except Exception as e:
                logger.error(f"Add password error - User: {request.user.username}, Error: {str(e)}")
                messages.error(request, 'An error occurred while adding the password.')
        else:
            logger.warning(f"Invalid add password form - User: {request.user.username}, Errors: {form.errors}")
    else:
        form = PasswordEntryForm()

    return render(request, 'users/add_password.html', {'form': form})


@login_required
def view_password(request, password_id):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    logger.info(f"Password view requested - User: {request.user.username}, Password ID: {password_id}, IP: {client_ip}")

    try:
        password_entry = get_object_or_404(PasswordEntry, id=password_id, user=request.user)
        logger.info(
            f"Password entry retrieved - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}")

        decrypted_password = password_entry.decrypt_password()
        logger.info(
            f"Password decrypted and viewed - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}")

        return render(request, 'users/view_password.html', {
            'password_entry': password_entry,
            'decrypted_password': decrypted_password
        })

    except Http404:
        logger.warning(
            f"Password not found or access denied - User: {request.user.username}, Password ID: {password_id}")
        messages.error(request, 'Password not found or access denied.')
        return redirect('dashboard')
    except Exception as e:
        logger.error(
            f"View password error - User: {request.user.username}, Password ID: {password_id}, Error: {str(e)}")
        messages.error(request, 'An error occurred while retrieving the password.')
        return redirect('dashboard')


@login_required
def edit_password(request, password_id):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    logger.info(
        f"Edit password page accessed - User: {request.user.username}, Password ID: {password_id}, IP: {client_ip}")

    try:
        password_entry = get_object_or_404(PasswordEntry, id=password_id, user=request.user)
        logger.info(
            f"Password entry retrieved for editing - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}")

    except Http404:
        logger.warning(f"Password not found for editing - User: {request.user.username}, Password ID: {password_id}")
        messages.error(request, 'Password not found or access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        logger.info(f"Edit password form submitted - User: {request.user.username}, Password ID: {password_id}")
        form = PasswordEntryForm(request.POST, instance=password_entry)

        if form.is_valid():
            try:
                old_service = password_entry.service_name
                password_entry = form.save(commit=False)
                password_entry.encrypt_password(form.cleaned_data['password'])
                password_entry.save()

                messages.success(request, 'Password updated successfully!')
                logger.info(
                    f"Password entry updated successfully - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}")
                return redirect('dashboard')

            except Exception as e:
                logger.error(
                    f"Edit password error - User: {request.user.username}, Password ID: {password_id}, Error: {str(e)}")
                messages.error(request, 'An error occurred while updating the password.')
        else:
            logger.warning(
                f"Invalid edit password form - User: {request.user.username}, Password ID: {password_id}, Errors: {form.errors}")
    else:
        # Pre-populate form with current data (except password)
        form = PasswordEntryForm(instance=password_entry)
        form.fields['password'].initial = ''

    return render(request, 'users/edit_password.html', {'form': form, 'password_entry': password_entry})


@login_required
def delete_password(request, password_id):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    logger.info(
        f"Delete password page accessed - User: {request.user.username}, Password ID: {password_id}, IP: {client_ip}")

    try:
        password_entry = get_object_or_404(PasswordEntry, id=password_id, user=request.user)
        logger.info(
            f"Password entry retrieved for deletion - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}")

    except Http404:
        logger.warning(f"Password not found for deletion - User: {request.user.username}, Password ID: {password_id}")
        messages.error(request, 'Password not found or access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            service_name = password_entry.service_name
            username = password_entry.username
            logger.info(
                f"Deleting password entry - User: {request.user.username}, Service: {service_name}, Username: {username}, ID: {password_id}")

            password_entry.delete()
            messages.success(request, 'Password deleted successfully!')
            logger.info(
                f"Password entry deleted successfully - User: {request.user.username}, Service: {service_name}, ID: {password_id}")
            return redirect('dashboard')

        except Exception as e:
            logger.error(
                f"Delete password error - User: {request.user.username}, Password ID: {password_id}, Error: {str(e)}")
            messages.error(request, 'An error occurred while deleting the password.')

    return render(request, 'users/delete_password.html', {'password_entry': password_entry})