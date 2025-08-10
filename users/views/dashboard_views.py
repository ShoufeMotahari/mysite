import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from users.models import PasswordEntry, User

logger = logging.getLogger("users")
User = get_user_model()


@login_required
def dashboard_view(request):
    # if not request.session.get('second_auth'):
    #     return redirect('dashboard')
    return render(request, "users/dashboard.html", {"user": request.user})


@login_required
def dashboard(request):
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )
    logger.info(f"Dashboard accessed - User: {request.user.username}, IP: {client_ip}")

    try:
        password_entries = PasswordEntry.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        total_entries = password_entries.count()

        logger.info(
            f"Password entries retrieved - User: {request.user.username}, Count: {total_entries}"
        )

        # Pagination
        paginator = Paginator(password_entries, 10)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        logger.debug(
            f"Dashboard pagination - User: {request.user.username}, Page: {page_number}, Total pages: {paginator.num_pages}"
        )

        return render(request, "users/dashboard.html", {"page_obj": page_obj})

    except Exception as e:
        logger.error(
            f"Dashboard error - User: {request.user.username}, IP: {client_ip}, Error: {str(e)}"
        )
        messages.error(request, "An error occurred while loading the dashboard.")
        return render(request, "users/dashboard.html", {"page_obj": None})
