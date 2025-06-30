from django.shortcuts import render
from django.shortcuts import render, redirect
from .forms import SignupForm
from users.models import User, RegisterToken
from core.sms import send_verification_sms
import random
from django.contrib import messages

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
                messages.success(request, "ثبت‌نام با موفقیت انجام شد!")
                return redirect('home')
            else:
                messages.error(request, "کد وارد شده اشتباه یا منقضی است.")
        except:
            messages.error(request, "کاربر یا کد پیدا نشد.")
    return render(request, 'accounts/verify.html')

