from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
import random
import uuid
import logging

from accounts.forms.forms import SignupForm, LoginForm, SecondPasswordForm, ChangeSecondPasswordForm, ForgotPasswordForm
from core.sms import send_verification_sms
from core.email import send_activation_email, send_password_reset_email
from users.models import User, RegisterToken, VerificationToken

logger = logging.getLogger('accounts')
User = get_user_model()


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

    return render(request, 'accounts/signup.html', {'form': form})


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

    return render(request, 'accounts/verify.html')


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
    return render(request, 'accounts/login.html', {'form': form})


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
    return render(request, 'accounts/verify_login.html')


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

    return render(request, 'accounts/forgot_password.html', {'form': form})


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
            return render(request, 'accounts/reset_password.html')

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

    return render(request, 'accounts/reset_password.html')


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

        return render(request, 'accounts/reset_password_email.html', {'token': token})

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
    return render(request, 'accounts/second_password.html', {'form': form})


@login_required
def dashboard_view(request):
    if not request.session.get('second_auth'):
        return redirect('second-password')
    return render(request, 'accounts/dashboard.html', {'user': request.user})


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

    return render(request, 'accounts/change_second_password.html', {'form': form})


def send_sms_view(request):
    phone = request.GET.get("phone")
    code = str(random.randint(100000, 999999))
    send_verification_sms(phone, code)
    return JsonResponse({"status": "sms sent", "code": code})  # Remove code in production