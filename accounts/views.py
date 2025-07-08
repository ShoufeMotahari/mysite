from django.shortcuts import render
from django.shortcuts import render, redirect
from .forms import SignupForm, LoginForm
from users.models import User, RegisterToken
from core.sms import send_verification_sms
import random
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
import logging
logger = logging.getLogger('accounts')

def my_view(request):
    logger.info('کاربر وارد صفحه‌ی لاگین شد')

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            user, created = User.objects.get_or_create(mobile=mobile, defaults={'username': mobile})

            code = str(random.randint(100000, 999999))

            RegisterToken.objects.update_or_create(user=user, defaults={'code': code})
            send_verification_sms(mobile, code)

            request.session['mobile'] = mobile
            return redirect('verify')
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


def verify_view(request):
    mobile = request.session.get('mobile')
    if not mobile:
        messages.error(request, "شماره‌ای یافت نشد.")
        return redirect('signup')

    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            user = User.objects.get(mobile=mobile)
            token = RegisterToken.objects.get(user=user)

            if token.code == code and token.is_valid():
                user.is_active = True
                user.save()
                token.delete()
                messages.success(request, "حساب شما با موفقیت فعال شد.")
                return redirect('home')  # بعداً مسیر داشبورد یا صفحه اصلی
            else:
                messages.error(request, "کد وارد شده اشتباه یا منقضی شده است.")
        except:
            messages.error(request, "مشکلی در بررسی کد وجود دارد.")

    return render(request, 'accounts/verify.html')


User = get_user_model()


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

                code = str(random.randint(100000, 999999))
                RegisterToken.objects.update_or_create(user=user, defaults={'code': code})
                request.session['login_id'] = user.id

                # ارسال کد تأیید
                from core.sms import send_verification_sms
                send_verification_sms(user.mobile, code)

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
                from django.contrib.auth import login
                login(request, user)
                token.delete()
                return redirect('dashboard')  # یا home یا profile
            else:
                messages.error(request, "کد وارد شده اشتباه یا منقضی شده است.")
        except:
            messages.error(request, "کاربر یا کد معتبر نیست.")
    return render(request, 'accounts/verify_login.html')

@login_required
def dashboard_view(request):
    user = request.user
    return render(request, 'accounts/dashboard.html', {'user': user})


from django.http import JsonResponse

def send_sms_view(request):
    phone = request.GET.get("phone")
    code = "1234"  # یا کد تولید شده دینامیک
    send_verification_sms(phone, code)
    return JsonResponse({"status": "sms sent"})