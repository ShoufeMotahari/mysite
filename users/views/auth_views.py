# users/views/auth_views.py
import logging
import random

from django.contrib import messages
from django.contrib.auth import login
from django.http import JsonResponse
from django.shortcuts import render, redirect

from core.email import send_activation_email
from core.sms import send_verification_sms
from users.forms.forms import CustomUserCreationForm
from users.forms.forms import SignupForm, LoginForm
from users.models import User, RegisterToken, VerificationToken
from core.sms import send_verification_sms
from core.email import  send_activation_email
from core.views import home_view
logger = logging.getLogger('users')

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            email = form.cleaned_data.get('email')
            logger.info(mobile)
            logger.info(email)
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
            logger.info(created)

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
    user_id = request.session.get('login_user_id')

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

                # **ورود خودکار**
                login(request, user)

                # پاک کردن سشن
                request.session.pop('mobile', None)
                request.session.pop('signup_user_id', None)

                messages.success(request, "حساب شما فعال و وارد سیستم شدید.")
                return redirect('dashboard')  # به جای صفحه لاگین مستقیماً به داشبورد می‌رود

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
                # جستجوی کاربر با ایمیل یا موبایل
                if '@' in identifier:
                    user = User.objects.get(email=identifier)
                else:
                    user = User.objects.get(mobile=identifier)

                if not user.is_active:
                    messages.error(request, "حساب شما فعال نشده است. لطفاً ابتدا حساب خود را فعال کنید.")
                    return redirect('signup')

                # تولید کد تایید SMS
                sms_code = VerificationToken.generate_sms_token()

                # پاک‌سازی کدهای قبلی از نوع login
                VerificationToken.objects.filter(user=user, token_type='login').delete()

                # ذخیره کد جدید
                verification_token = VerificationToken.objects.create(
                    user=user,
                    token=sms_code,
                    token_type='login'
                )

                # Add debugging in login_view after creating token
                logger.info(f"Created verification token: {sms_code} for user {user.id}")
                token_count = VerificationToken.objects.filter(user=user, token_type='login').count()
                logger.info(f"Total login tokens for user: {token_count}")

                # ذخیره user_id برای مرحله بعدی
                request.session['login_user_id'] = user.id

                # ارسال SMS
                try:
                    sms_result = send_verification_sms(user.mobile, sms_code)
                    if sms_result:
                        logger.info(f"Login verification code sent successfully to {user.mobile}")
                        messages.success(request, "کد تایید به شماره موبایل شما ارسال شد.")
                    else:
                        logger.error(f"Failed to send SMS to {user.mobile}")
                        messages.error(request, "خطا در ارسال پیامک. لطفاً دوباره تلاش کنید.")
                        return render(request, 'users/login.html', {'form': form})
                except Exception as e:
                    logger.error(f"SMS sending exception: {e}")
                    messages.error(request, "خطا در ارسال پیامک. لطفاً دوباره تلاش کنید.")
                    return render(request, 'users/login.html', {'form': form})

                return redirect('verify-login')

            except User.DoesNotExist:
                logger.warning(f"Login attempted with non-existent identifier: {identifier}")
                form.add_error('identifier', 'کاربری با این مشخصات یافت نشد.')
            except Exception as e:
                logger.error(f"Unexpected error in login_view: {e}")
                messages.error(request, "خطای سیستمی رخ داده است. لطفاً دوباره تلاش کنید.")

    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})

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
def send_sms_view(request):
    phone = request.GET.get("phone")
    code = str(random.randint(1, 9)) #TODO
    send_verification_sms(phone, code)
    return JsonResponse({"status": "sms sent", "code": code})  # Remove code in production
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


def verify_login_view(request):
    user_id = request.session.get('login_user_id')  # ✅ Fixed session key
    if not user_id:
        messages.error(request, "جلسه منقضی شده است.")
        return redirect('login')

    if request.method == 'POST':
        code = request.POST.get('code')
        if not code:
            messages.error(request, "لطفاً کد را وارد کنید.")
            return render(request, 'users/verify_login.html')

        try:
            user = User.objects.get(id=user_id)
            token = VerificationToken.objects.get(  # ✅ Fixed model
                user=user,
                token=code,
                token_type='login'
            )

            if token.is_valid():
                login(request, user)
                token.mark_as_used()  # ✅ Mark as used instead of delete
                request.session.pop('login_user_id', None)  # ✅ Fixed session key
                messages.success(request, "با موفقیت وارد شدید.")
                return redirect('dashboard')
            else:
                messages.error(request, "کد وارد شده اشتباه یا منقضی شده است.")

        except User.DoesNotExist:
            messages.error(request, "کاربر یافت نشد.")
            return redirect('login')
        except VerificationToken.DoesNotExist:
            messages.error(request, "کد وارد شده اشتباه است.")

    return render(request, 'users/verify_login.html')