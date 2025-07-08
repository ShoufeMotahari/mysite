import logging

logger = logging.getLogger('users')


def my_view(request):
    logger.info('یوزر')


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm

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
