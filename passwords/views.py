from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import Http404
from .forms import CustomUserCreationForm, PasswordEntryForm
from .models import PasswordEntry
import logging

logger = logging.getLogger(__name__)


def register(request):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

    logger.info(f"Registration page accessed - IP: {client_ip}, User-Agent: {user_agent}")

    if request.method == 'POST':
        logger.info(f"Registration form submitted - IP: {client_ip}")
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            try:
                user = form.save()
                logger.info(
                    f"User created successfully - Username: {user.username}, Email: {user.email}, IP: {client_ip}")

                login(request, user)
                logger.info(f"User logged in after registration - Username: {user.username}, IP: {client_ip}")

                messages.success(request, 'Registration successful!')
                return redirect('dashboard')

            except Exception as e:
                logger.error(f"Registration failed - IP: {client_ip}, Error: {str(e)}")
                messages.error(request, 'An error occurred during registration.')
        else:
            logger.warning(f"Invalid registration form - IP: {client_ip}, Errors: {form.errors}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'passwords/registration/register.html', {'form': form})


@login_required
def dashboard(request):
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    logger.info(f"Dashboard accessed - User: {request.user.username}, IP: {client_ip}")

    try:
        password_entries = PasswordEntry.objects.filter(user=request.user).order_by('-created_at')
        total_entries = password_entries.count()

        logger.info(f"Password entries retrieved - User: {request.user.username}, Count: {total_entries}")

        # Pagination
        paginator = Paginator(password_entries, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        logger.debug(
            f"Dashboard pagination - User: {request.user.username}, Page: {page_number}, Total pages: {paginator.num_pages}")

        return render(request, 'passwords/dashboard.html', {'page_obj': page_obj})

    except Exception as e:
        logger.error(f"Dashboard error - User: {request.user.username}, IP: {client_ip}, Error: {str(e)}")
        messages.error(request, 'An error occurred while loading the dashboard.')
        return render(request, 'passwords/dashboard.html', {'page_obj': None})


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

    return render(request, 'passwords/add_password.html', {'form': form})


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

        return render(request, 'passwords/view_password.html', {
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

    return render(request, 'passwords/edit_password.html', {'form': form, 'password_entry': password_entry})


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

    return render(request, 'passwords/delete_password.html', {'password_entry': password_entry})
