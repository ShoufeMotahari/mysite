from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from urllib.parse import urlencode
import requests
from django.contrib.auth import login
from django.contrib.auth.models import User

def google_login(request):
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return redirect(url)


def google_callback(request):
    code = request.GET.get("code")
    if not code:
        return HttpResponse("Error: No code provided", status=400)

    # درخواست توکن
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_resp = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    token_json = token_resp.json()
    id_token = token_json.get("id_token")

    if not id_token:
        return HttpResponse("Error: No id_token received", status=400)

    # Decode id_token (بدون تایید امضا برای سادگی)
    from jose import jwt
    user_info = jwt.get_unverified_claims(id_token)

    email = user_info.get("email")
    name = user_info.get("name")

    if not email:
        return HttpResponse("Error: Email not found", status=400)

    # بررسی کاربر
    user, created = User.objects.get_or_create(username=email, defaults={"first_name": name or ""})

    # ورود کاربر
    login(request, user)

    return redirect("/")  # مسیر دلخواه بعد از ورود
