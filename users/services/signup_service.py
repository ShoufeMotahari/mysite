from accounts_.factories.user_factory import UserFactory

def signup_user(mobile):
    return UserFactory.create_user_with_token(mobile)


# ✅ 3. accounts_/views.py (مربوط به ثبت‌نام)

from django.shortcuts import render, redirect
from accounts_.forms import SignupForm
from accounts_.services.signup_service import signup_user


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            signup_user(mobile)
            return redirect('verify')
    else:
        form = SignupForm()
    return render(request, 'accounts/../../templates/users/signup.html', {'form': form})