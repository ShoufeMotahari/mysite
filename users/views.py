import logging
from users.forms.forms import UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import get_user_model
from django.http import JsonResponse
import random
import uuid
from users.forms.forms import SignupForm, LoginForm, SecondPasswordForm, ChangeSecondPasswordForm, ForgotPasswordForm
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
from .models import PasswordEntry

logger = logging.getLogger('users')
User = get_user_model()


def my_view(request):
    logger.info('یوزر')


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
def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            email = form.cleaned_data.get('email')

            # Create user
            user, created = User.objects.get_or_create(
                mobile=mobile,
                defaults={
                    'mobile': mobile,
                    'email': email,
                    'username': mobile,
                    'is_active': False,
                    'is_phone_verified': False,
                    'is_email_verified': False
                }
            )

            if not created:
                logger.info(f"User {user.mobile} already exists")
                if user.is_active and user.is_phone_verified:
                    messages.error(request, "این کاربر قبلاً فعال شده است.")
                    return redirect('login')

            # Create SMS verification token
            sms_code = VerificationToken.generate_sms_token()

            # Create verification token
            verification_token = VerificationToken.objects.create(
                user=user,
                token=sms_code,
                token_type='registration'
            )

            logger.info(f"Generated SMS code: {sms_code} for {mobile}")

            # Send SMS verification
            send_verification_sms(mobile, sms_code)

            # Send email verification if email provided
            if email:
                send_activation_email(user, str(verification_token.email_token))
                logger.info(f"Activation email sent to {email}")

            request.session['mobile'] = mobile
            request.session['signup_user_id'] = user.id

            if email:
                messages.success(request, "کد تایید به شماره موبایل و لینک فعال‌سازی به ایمیل شما ارسال شد.")
            else:
                messages.success(request, "کد تایید به شماره موبایل شما ارسال شد.")

            return redirect('verify')
    else:
        form = SignupForm()

    return render(request, 'users/signup.html', {'form': form})


def verify_view(request):
    mobile = request.session.get('mobile')
    user_id = request.session.get('signup_user_id')

    if not mobile or not user_id:
        messages.error(request, "شماره‌ای یافت نشد.")
        return redirect('signup')

    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            user = User.objects.get(id=user_id, mobile=mobile)
            token = VerificationToken.objects.get(
                user=user,
                token=code,
                token_type='registration'
            )

            if token.is_valid():
                user.is_active = True
                user.is_phone_verified = True
                user.save()
                token.mark_as_used()

                # Clear session
                request.session.pop('mobile', None)
                request.session.pop('signup_user_id', None)

                messages.success(request, "حساب شما با موفقیت فعال شد.")
                return redirect('login')
            else:
                messages.error(request, "کد وارد شده اشتباه یا منقضی شده است.")
        except (User.DoesNotExist, VerificationToken.DoesNotExist):
            messages.error(request, "مشکلی در بررسی کد وجود دارد.")

    return render(request, 'users/verify.html')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']

            try:
                if '@' in identifier:
                    user = User.objects.get(email=identifier)
                else:
                    user = User.objects.get(mobile=identifier)

                if not user.is_active:
                    messages.error(request, "حساب شما فعال نشده است. لطفاً ابتدا حساب خود را فعال کنید.")
                    return redirect('signup')

                # Generate login verification code
                sms_code = VerificationToken.generate_sms_token()

                # Create verification token for login
                VerificationToken.objects.filter(
                    user=user,
                    token_type='registration'
                ).delete()  # Remove old tokens

                VerificationToken.objects.create(
                    user=user,
                    token=sms_code,
                    token_type='registration'
                )

                request.session['login_id'] = user.id

                # Send verification code
                send_verification_sms(user.mobile, sms_code)
                logger.info(f"Login verification code sent to {user.mobile}")

                return redirect('verify-login')

            except User.DoesNotExist:
                form.add_error('identifier', 'کاربری با این مشخصات یافت نشد.')
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})


def verify_login_view(request):
    user_id = request.session.get('login_id')
    if not user_id:
        return redirect('login')

    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            user = User.objects.get(id=user_id)
            token = RegisterToken.objects.get(user=user)

            if token.code == code and token.is_valid():
                login(request, user)
                token.delete()
                request.session.pop('login_id', None)
                return redirect('dashboard')
            else:
                messages.error(request, "کد وارد شده اشتباه یا منقضی شده است.")
        except (User.DoesNotExist, RegisterToken.DoesNotExist):
            messages.error(request, "کاربر یا کد معتبر نیست.")
    return render(request, 'users/verify_login.html')


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
                sms_code = str(random.randint(100000, 999999))
                email_token = str(uuid.uuid4())

                RegisterToken.objects.update_or_create(
                    user=user,
                    defaults={'code': sms_code, 'email_token': email_token}
                )

                # Send SMS code
                send_verification_sms(user.mobile, sms_code)

                # Send email if user has email
                if user.email:
                    send_password_reset_email(user, email_token)

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
        register_token = RegisterToken.objects.get(email_token=token)
        if not register_token.is_valid():
            messages.error(request, "توکن منقضی شده است.")
            return redirect('forgot-password')

        user = register_token.user

        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                messages.error(request, "رمزهای عبور مطابقت ندارند.")
                return render(request, 'accounts/reset_password_email.html', {'token': token})

            user.set_password(new_password)
            user.save()
            register_token.delete()

            messages.success(request, "رمز عبور شما با موفقیت تغییر یافت.")
            return redirect('login')

        return render(request, 'users/reset_password_email.html', {'token': token})

    except RegisterToken.DoesNotExist:
        messages.error(request, "توکن معتبر نیست.")
        return redirect('forgot-password')


def activate_account_view(request):
    token = request.GET.get('token')
    if not token:
        messages.error(request, "توکن وجود ندارد.")
        return redirect('signup')

    try:
        register_token = VerificationToken.objects.get(email_token=token)
        if not register_token.is_valid():
            messages.error(request, "توکن منقضی شده است.")
            return redirect('signup')

        user = register_token.user
        user.is_active = True
        user.save()
        register_token.delete()
        messages.success(request, "حساب شما با موفقیت فعال شد.")
        return redirect('login')
    except RegisterToken.DoesNotExist:
        messages.error(request, "توکن معتبر نیست یا قبلاً استفاده شده.")
        return redirect('signup')


@login_required
def second_password_view(request):
    if request.method == 'POST':
        form = SecondPasswordForm(request.POST)
        if form.is_valid():
            second_password = form.cleaned_data['second_password']
            if request.user.second_password == second_password:
                request.session['second_auth'] = True
                return redirect('dashboard')
            else:
                messages.error(request, "رمز دوم اشتباه است.")
    else:
        form = SecondPasswordForm()
    return render(request, 'users/second_password.html', {'form': form})


@login_required
def dashboard_view(request):
    if not request.session.get('second_auth'):
        return redirect('second-password')
    return render(request, 'users/dashboard.html', {'user': request.user})


@login_required
def change_second_password_view(request):
    if request.method == 'POST':
        form = ChangeSecondPasswordForm(request.POST)
        if form.is_valid():
            current = form.cleaned_data['current_password']
            new = form.cleaned_data['new_password']
            user = request.user

            if user.second_password == current:
                user.second_password = new
                user.save()
                messages.success(request, "رمز دوم با موفقیت تغییر یافت.")
                return redirect('dashboard')
            else:
                form.add_error('current_password', "رمز دوم فعلی اشتباه است.")
    else:
        form = ChangeSecondPasswordForm()

    return render(request, 'users/change_second_password.html', {'form': form})


def send_sms_view(request):
    phone = request.GET.get("phone")
    code = str(random.randint(100000, 999999))
    send_verification_sms(phone, code)
    return JsonResponse({"status": "sms sent", "code": code})  # Remove code in production




def logout_view(request):


    logout(request)

    # Debug: Print to console what's happening
    print("Logout successful, redirecting...")

    # Try redirecting to a URL that definitely exists
    return redirect('/admin/')  # This should always work
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

    return render(request, 'users/registration/register.html', {'form': form})


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

        return render(request, 'users/dashboard.html', {'page_obj': page_obj})

    except Exception as e:
        logger.error(f"Dashboard error - User: {request.user.username}, IP: {client_ip}, Error: {str(e)}")
        messages.error(request, 'An error occurred while loading the dashboard.')
        return render(request, 'users/dashboard.html', {'page_obj': None})


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
