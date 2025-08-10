import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from users.forms.forms import (
    ProfileUpdateForm,
    UserUpdateForm,
)
from users.models import User

logger = logging.getLogger("users")
User = get_user_model()


@login_required
def profile_edit(request):
    user = request.user
    profile = getattr(user, "profile", None)

    if request.method == "POST":
        u_form = UserUpdateForm(request.POST, instance=user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect("profile_edit")
    else:
        u_form = UserUpdateForm(instance=user)
        p_form = ProfileUpdateForm(instance=profile)

    return render(
        request, "users/profile_edit.html", {"u_form": u_form, "p_form": p_form}
    )


def user_profile(request, slug):
    """Display user profile by slug"""
    user = get_object_or_404(User, slug=slug)
    profile = getattr(user, "profile", None)

    return render(
        request, "users/user_profile.html", {"profile_user": user, "profile": profile}
    )
