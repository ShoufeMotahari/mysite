import json
import logging
import secrets
import string

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.email import send_password_reset_email
from core.services.sms_service import send_verification_sms
from users.forms.forms import (
    ForgotPasswordForm,
    PasswordEntryForm,
    VerificationForm,
)
# Import our custom password functions
from users.utils.password_utils import make_password, check_password, get_password_strength

logger = logging.getLogger("users")

# Console logger for development
console_logger = logging.getLogger("console")
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("🔑 PASSWORD INFO: %(message)s")
console_handler.setFormatter(formatter)
console_logger.addHandler(console_handler)
console_logger.setLevel(logging.INFO)


# Password Reset and Recovery Views
def forgot_password_view(request):
    """Handle forgot password requests - send both SMS and Email"""
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["identifier"]

            logger.info(f"Forgot password request - Identifier: {identifier}")

            # Find user by mobile number (since we're using SMS for verification)
            user = None
            clean_mobile = identifier.replace(" ", "").replace("-", "")

            try:
                user = User.objects.get(mobile=clean_mobile)
            except User.DoesNotExist:
                # For security, don't reveal if user exists or not
                messages.success(
                    request,
                    "اگر شماره موبایل در سیستم موجود باشد، کد بازیابی ارسال خواهد شد.",
                )
                return render(request, "users/forgot_password.html", {"form": form})

            # Generate reset code
            reset_code = VerificationToken.generate_sms_token()

            # Delete existing password reset tokens for this user
            VerificationToken.objects.filter(
                user=user, token_type="password_reset"
            ).delete()

            # Create new verification token
            verification_token = VerificationToken.objects.create(
                user=user, token=reset_code, token_type="password_reset"
            )

            # 🔑 CONSOLE LOGGING FOR PASSWORD RESET
            console_logger.info(f"Password Reset Code for {user.mobile}: {reset_code}")

            # Send SMS
            try:
                send_verification_sms(user.mobile, reset_code)
                logger.info(f"Password reset SMS sent to {user.mobile}")
            except Exception as e:
                logger.error(f"Failed to send password reset SMS: {e}")

            # Send email if user has email
            if user.email:
                try:
                    print(f"\n🔧 ATTEMPTING TO SEND EMAIL TO: {user.email}")

                    # Generate email token
                    email_token = (
                        str(verification_token.email_token)
                        if hasattr(verification_token, "email_token")
                        else reset_code
                    )

                    # Send password reset email
                    email_sent = send_password_reset_email(user, email_token)

                    if email_sent:
                        console_logger.info(
                            f"Password reset email sent to {user.email}"
                        )
                        print(f"✅ EMAIL SENT SUCCESSFULLY TO: {user.email}")
                    else:
                        print(f"❌ EMAIL SENDING FAILED FOR: {user.email}")

                except Exception as e:
                    logger.error(f"Failed to send password reset email: {e}")
                    print(f"❌ EMAIL ERROR: {e}")

            # Store user ID in session for verification
            request.session["reset_user_id"] = user.id

            success_message = "کد بازیابی رمز عبور به شماره موبایل شما ارسال شد."
            if user.email:
                success_message += " همچنین لینک بازیابی به ایمیل شما ارسال شد."

            messages.success(request, success_message)
            return redirect("users:verify_reset_password")

    else:
        form = ForgotPasswordForm()

    return render(request, "users/forgot_password.html", {"form": form})


def verify_reset_password_view(request):
    """Handle SMS verification for password reset"""
    user_id = request.session.get("reset_user_id")

    if not user_id:
        messages.error(request, "جلسه منقضی شده است. لطفاً دوباره تلاش کنید.")
        return redirect("users:forgot_password")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "کاربر یافت نشد.")
        return redirect("users:forgot_password")

    if request.method == "POST":
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]

            try:
                token = VerificationToken.objects.get(
                    user=user, token=code, token_type="password_reset", is_used=False
                )

                if token.is_valid():
                    # Mark token as used and proceed to password reset
                    token.mark_as_used()

                    # Store verification success in session
                    request.session["password_reset_verified"] = True

                    console_logger.info(
                        f"Password reset code verified for user: {user.username}"
                    )
                    messages.success(
                        request, "کد تایید شد. لطفاً رمز عبور جدید خود را وارد کنید."
                    )
                    return redirect("users:reset_password")
                else:
                    messages.error(request, "کد وارد شده منقضی شده است.")
                    logger.warning(f"Expired reset code used - User: {user.username}")

            except VerificationToken.DoesNotExist:
                messages.error(request, "کد وارد شده صحیح نمی‌باشد.")
                logger.warning(f"Invalid reset code entered - User: {user.username}")

        else:
            logger.warning(f"Invalid verification form - Errors: {form.errors}")
    else:
        form = VerificationForm()

    # Display masked mobile number
    masked_mobile = user.mobile[:3] + "*****" + user.mobile[-3:] if user.mobile else ""

    return render(
        request,
        "users/verify_reset_password.html",
        {"form": form, "mobile": user.mobile, "masked_mobile": masked_mobile},
    )


def reset_password_view(request):
    """Handle password reset after SMS verification with password strength checking"""
    user_id = request.session.get("reset_user_id")
    password_reset_verified = request.session.get("password_reset_verified")

    if not user_id or not password_reset_verified:
        messages.error(
            request,
            "دسترسی غیرمجاز. لطفاً فرآیند بازیابی رمز عبور را دوباره انجام دهید.",
        )
        return redirect("users:forgot_password")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "کاربر یافت نشد.")
        return redirect("users:forgot_password")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validation
        if not new_password or not confirm_password:
            messages.error(request, "لطفاً همه فیلدها را پر کنید.")
            return render(request, "users/reset_password.html")

        if len(new_password) < 8:
            messages.error(request, "رمز عبور باید حداقل 8 کاراکتر باشد.")
            return render(request, "users/reset_password.html")

        if new_password != confirm_password:
            messages.error(request, "رمزهای عبور مطابقت ندارند.")
            return render(request, "users/reset_password.html")

        # Check password strength
        password_strength = get_password_strength(new_password)
        if password_strength['score'] < 3:  # Require at least "Fair" strength
            messages.error(
                request,
                f"Password is too weak ({password_strength['strength']}). "
                f"Suggestions: {', '.join(password_strength['suggestions'])}"
            )
            return render(request, "users/reset_password.html")

        try:
            # Update password using our custom make_password
            user.password = make_password(new_password)
            user.save()

            # Clear session data
            request.session.pop("reset_user_id", None)
            request.session.pop("password_reset_verified", None)

            console_logger.info(f"Password reset completed for user: {user.username}")
            logger.info(f"Password reset successful - User: {user.username}, Strength: {password_strength['strength']}")

            # Automatically log in the user
            from django.contrib.auth import login
            login(request, user)
            messages.success(
                request, "رمز عبور شما با موفقیت تغییر یافت و وارد سیستم شدید."
            )
            return redirect("users:dashboard")

        except Exception as e:
            logger.error(
                f"Password reset error - User: {user.username}, Error: {str(e)}"
            )
            messages.error(request, "خطا در تغییر رمز عبور. لطفاً دوباره تلاش کنید.")

    return render(request, "users/reset_password.html")


def reset_password_email_view(request):
    """Handle password reset via email link"""
    token = request.GET.get("token")
    if not token:
        messages.error(request, "توکن وجود ندارد.")
        return redirect("users:login")

    try:
        # Updated to use VerificationToken instead of RegisterToken
        verification_token = VerificationToken.objects.get(
            email_token=token, token_type="password_reset", is_used=False
        )

        if not verification_token.is_valid():
            messages.error(request, "توکن منقضی شده است.")
            return redirect("users:forgot_password")

        user = verification_token.user

        if request.method == "POST":
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not new_password or not confirm_password:
                messages.error(request, "لطفاً همه فیلدها را پر کنید.")
                return render(
                    request, "users/reset_password_email.html", {"token": token}
                )

            if new_password != confirm_password:
                messages.error(request, "رمزهای عبور مطابقت ندارند.")
                return render(
                    request, "users/reset_password_email.html", {"token": token}
                )

            # Check password strength
            password_strength = get_password_strength(new_password)
            if password_strength['score'] < 3:
                messages.error(
                    request,
                    f"Password is too weak ({password_strength['strength']}). "
                    f"Suggestions: {', '.join(password_strength['suggestions'])}"
                )
                return render(
                    request, "users/reset_password_email.html", {"token": token}
                )

            user.password = make_password(new_password)
            user.save()
            verification_token.mark_as_used()

            console_logger.info(f"Password reset via email completed for user: {user.username}")
            logger.info(
                f"Email password reset successful - User: {user.username}, Strength: {password_strength['strength']}")

            messages.success(request, "رمز عبور شما با موفقیت تغییر یافت.")
            return redirect("users:login")

        return render(request, "users/reset_password_email.html", {"token": token})

    except VerificationToken.DoesNotExist:
        messages.error(request, "توکن معتبر نیست.")
        return redirect("users:forgot_password")


def resend_reset_code_view(request):
    """Resend SMS code for password reset"""
    user_id = request.session.get("reset_user_id")

    if not user_id:
        return JsonResponse({"success": False, "message": "جلسه منقضی شده است."})

    try:
        user = User.objects.get(id=user_id)

        # Generate new code
        reset_code = VerificationToken.generate_sms_token()

        # Delete old tokens
        VerificationToken.objects.filter(
            user=user, token_type="password_reset"
        ).delete()

        # Create new token
        VerificationToken.objects.create(
            user=user, token=reset_code, token_type="password_reset"
        )

        # 🔑 CONSOLE LOGGING FOR RESENT CODE
        console_logger.info(
            f"Resent Password Reset Code for {user.mobile}: {reset_code}"
        )

        # Send SMS
        send_verification_sms(user.mobile, reset_code)
        logger.info(f"Password reset code resent to {user.mobile}")

        return JsonResponse({"success": True, "message": "کد جدید ارسال شد."})

    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "کاربر یافت نشد."})
    except Exception as e:
        logger.error(f"Failed to resend reset code: {e}")
        return JsonResponse({"success": False, "message": "خطا در ارسال کد."})


# Password Management for Logged-in Users
@login_required
def change_password_view(request):
    """Allow authenticated users to change their password"""
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # Validate current password
        if not check_password(current_password, request.user.password):
            messages.error(request, "رمز عبور فعلی صحیح نمی‌باشد.")
            return render(request, "users/password/change_password.html")

        # Validate new password
        if not new_password or len(new_password) < 8:
            messages.error(request, "رمز عبور جدید باید حداقل 8 کاراکتر باشد.")
            return render(request, "users/password/change_password.html")

        if new_password != confirm_password:
            messages.error(request, "رمزهای عبور جدید مطابقت ندارند.")
            return render(request, "users/password/change_password.html")

        # Check password strength
        password_strength = get_password_strength(new_password)
        if password_strength['score'] < 3:
            messages.error(
                request,
                f"رمز عبور جدید ضعیف است ({password_strength['strength']}). "
                f"پیشنهادات: {', '.join(password_strength['suggestions'])}"
            )
            return render(request, "users/password/change_password.html")

        # Don't allow same password
        if check_password(new_password, request.user.password):
            messages.error(request, "رمز عبور جدید نمی‌تواند مانند رمز عبور فعلی باشد.")
            return render(request, "users/password/change_password.html")

        try:
            # Update password and keep user logged in
            request.user.password = make_password(new_password)
            request.user.save()

            # Update session to prevent logout
            update_session_auth_hash(request, request.user)

            logger.info(
                f"Password changed successfully - User: {request.user.username}, "
                f"Strength: {password_strength['strength']}"
            )

            console_logger.info(f"Password changed for user: {request.user.username}")
            messages.success(request, "رمز عبور شما با موفقیت تغییر یافت.")
            return redirect("users:dashboard")

        except Exception as e:
            logger.error(f"Password change error - User: {request.user.username}, Error: {str(e)}")
            messages.error(request, "خطا در تغییر رمز عبور. لطفاً دوباره تلاش کنید.")

    return render(request, "users/password/change_password.html")


@login_required
def password_history_view(request):
    """Show password change history (for security auditing)"""
    # Mock data - implement actual PasswordHistory model if needed
    password_changes = [
        {
            'date': '۱۴۰۳/۰۵/۲۰ - ۱۴:۳۰',
            'strength': 'قوی',
            'status': 'فعلی',
            'ip_address': request.META.get('REMOTE_ADDR', ''),
            'user_agent': 'Chrome - Windows',
            'duration_days': 45
        },
        {
            'date': '۱۴۰۳/۰۳/۰۵ - ۱۰:۱۵',
            'strength': 'خوب',
            'status': 'منقضی',
            'ip_address': '192.168.1.100',
            'user_agent': 'Firefox - Windows',
            'duration_days': 75
        },
        {
            'date': '۱۴۰۲/۱۲/۲۰ - ۰۹:۴۵',
            'strength': 'متوسط',
            'status': 'منقضی',
            'ip_address': '192.168.1.101',
            'user_agent': 'Chrome - Mobile',
            'duration_days': 90
        }
    ]

    context = {
        "password_changes": password_changes,
        "stats": {
            "total_changes": len(password_changes),
            "days_since_last_change": 45,
            "current_strength": "قوی",
            "average_duration": 120
        }
    }

    return render(request, "users/password/password_history.html", context)


@login_required
def security_settings_view(request):
    """Security settings page with password options"""
    context = {
        "user": request.user,
        "password_info": {
            "last_changed": getattr(request.user, "date_joined", "نامشخص"),
            "strength": "قوی",  # You could calculate this
            "days_since_change": 45,
        },
        "security_settings": {
            "two_factor_enabled": False,  # Implement 2FA if needed
            "security_notifications": True,
            "password_expiry_days": 90,
        }
    }

    return render(request, "users/password/security_settings.html", context)


# Password Entry Management (for stored passwords)
@login_required
def add_password(request):
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )
    logger.info(
        f"Add password page accessed - User: {request.user.username}, IP: {client_ip}"
    )

    if request.method == "POST":
        logger.info(
            f"Add password form submitted - User: {request.user.username}, IP: {client_ip}"
        )
        form = PasswordEntryForm(request.POST)

        if form.is_valid():
            try:
                password_entry = form.save(commit=False)
                password_entry.user = request.user

                logger.info(
                    f"Creating password entry - User: {request.user.username}, Service: {password_entry.service_name}, Username: {password_entry.username}"
                )

                # Encrypt the password before saving
                password_entry.encrypt_password(form.cleaned_data["password"])
                password_entry.save()

                messages.success(request, "Password added successfully!")
                logger.info(
                    f"Password entry added successfully - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_entry.pk}"
                )
                return redirect("users:dashboard")

            except IntegrityError:
                logger.warning(
                    f"Duplicate password entry attempted - User: {request.user.username}, Service: {form.cleaned_data.get('service_name')}, Username: {form.cleaned_data.get('username')}"
                )
                messages.error(
                    request, "A password for this service and username already exists."
                )
            except Exception as e:
                logger.error(
                    f"Add password error - User: {request.user.username}, Error: {str(e)}"
                )
                messages.error(request, "An error occurred while adding the password.")
        else:
            logger.warning(
                f"Invalid add password form - User: {request.user.username}, Errors: {form.errors}"
            )
    else:
        form = PasswordEntryForm()

    return render(request, "users/add_password.html", {"form": form})


@login_required
def view_password(request, password_id):
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )
    logger.info(
        f"Password view requested - User: {request.user.username}, Password ID: {password_id}, IP: {client_ip}"
    )

    try:
        password_entry = get_object_or_404(
            PasswordEntry, id=password_id, user=request.user
        )
        logger.info(
            f"Password entry retrieved - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}"
        )

        decrypted_password = password_entry.decrypt_password()
        logger.info(
            f"Password decrypted and viewed - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}"
        )

        return render(
            request,
            "users/view_password.html",
            {
                "password_entry": password_entry,
                "decrypted_password": decrypted_password,
            },
        )

    except Http404:
        logger.warning(
            f"Password not found or access denied - User: {request.user.username}, Password ID: {password_id}"
        )
        messages.error(request, "Password not found or access denied.")
        return redirect("users:dashboard")
    except Exception as e:
        logger.error(
            f"View password error - User: {request.user.username}, Password ID: {password_id}, Error: {str(e)}"
        )
        messages.error(request, "An error occurred while retrieving the password.")
        return redirect("users:dashboard")


@login_required
def edit_password(request, password_id):
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )
    logger.info(
        f"Edit password page accessed - User: {request.user.username}, Password ID: {password_id}, IP: {client_ip}"
    )

    try:
        password_entry = get_object_or_404(
            PasswordEntry, id=password_id, user=request.user
        )
        logger.info(
            f"Password entry retrieved for editing - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}"
        )

    except Http404:
        logger.warning(
            f"Password not found for editing - User: {request.user.username}, Password ID: {password_id}"
        )
        messages.error(request, "Password not found or access denied.")
        return redirect("users:dashboard")

    if request.method == "POST":
        logger.info(
            f"Edit password form submitted - User: {request.user.username}, Password ID: {password_id}"
        )
        form = PasswordEntryForm(request.POST, instance=password_entry)

        if form.is_valid():
            try:
                password_entry = form.save(commit=False)
                password_entry.encrypt_password(form.cleaned_data["password"])
                password_entry.save()

                messages.success(request, "Password updated successfully!")
                logger.info(
                    f"Password entry updated successfully - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}"
                )
                return redirect("users:dashboard")

            except Exception as e:
                logger.error(
                    f"Edit password error - User: {request.user.username}, Password ID: {password_id}, Error: {str(e)}"
                )
                messages.error(
                    request, "An error occurred while updating the password."
                )
        else:
            logger.warning(
                f"Invalid edit password form - User: {request.user.username}, Password ID: {password_id}, Errors: {form.errors}"
            )
    else:
        # Pre-populate form with current data (except password)
        form = PasswordEntryForm(instance=password_entry)
        form.fields["password"].initial = ""

    return render(
        request,
        "users/edit_password.html",
        {"form": form, "password_entry": password_entry},
    )


@login_required
def delete_password(request, password_id):
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )
    logger.info(
        f"Delete password page accessed - User: {request.user.username}, Password ID: {password_id}, IP: {client_ip}"
    )

    try:
        password_entry = get_object_or_404(
            PasswordEntry, id=password_id, user=request.user
        )
        logger.info(
            f"Password entry retrieved for deletion - User: {request.user.username}, Service: {password_entry.service_name}, ID: {password_id}"
        )

    except Http404:
        logger.warning(
            f"Password not found for deletion - User: {request.user.username}, Password ID: {password_id}"
        )
        messages.error(request, "Password not found or access denied.")
        return redirect("users:dashboard")

    if request.method == "POST":
        try:
            service_name = password_entry.service_name
            username = password_entry.username
            logger.info(
                f"Deleting password entry - User: {request.user.username}, Service: {service_name}, Username: {username}, ID: {password_id}"
            )

            password_entry.delete()
            messages.success(request, "Password deleted successfully!")
            logger.info(
                f"Password entry deleted successfully - User: {request.user.username}, Service: {service_name}, ID: {password_id}"
            )
            return redirect("users:dashboard")

        except Exception as e:
            logger.error(
                f"Delete password error - User: {request.user.username}, Password ID: {password_id}, Error: {str(e)}"
            )
            messages.error(request, "An error occurred while deleting the password.")

    return render(
        request, "users/delete_password.html", {"password_entry": password_entry}
    )


# API Endpoints for Password Utilities
@require_POST
@csrf_exempt
def generate_password_view(request):
    """API endpoint to generate secure passwords"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        # Get parameters from request
        length = int(request.POST.get('length', 12))
        include_symbols = request.POST.get('include_symbols', 'true').lower() == 'true'
        include_numbers = request.POST.get('include_numbers', 'true').lower() == 'true'
        include_uppercase = request.POST.get('include_uppercase', 'true').lower() == 'true'
        include_lowercase = request.POST.get('include_lowercase', 'true').lower() == 'true'

        # Validate length
        if length < 6 or length > 50:
            return JsonResponse({"error": "طول رمز عبور باید بین 6 تا 50 کاراکتر باشد"}, status=400)

        # Build character set
        chars = ""
        if include_lowercase:
            chars += string.ascii_lowercase
        if include_uppercase:
            chars += string.ascii_uppercase
        if include_numbers:
            chars += string.digits
        if include_symbols:
            chars += "!@#$%^&*()_+-="

        if not chars:
            return JsonResponse({"error": "حداقل یک نوع کاراکتر را انتخاب کنید"}, status=400)

        # Generate secure password
        password = ''.join(secrets.choice(chars) for _ in range(length))

        # Calculate strength
        strength = get_password_strength(password)

        return JsonResponse({
            "password": password,
            "strength": strength,
            "length": len(password)
        })

    except Exception as e:
        logger.error(f"Password generation error: {str(e)}")
        return JsonResponse({"error": "خطا در تولید رمز عبور"}, status=500)


@require_POST
@csrf_exempt
def check_password_strength_view(request):
    """API endpoint to check password strength"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        password = data.get('password', '')

        strength = get_password_strength(password)

        return JsonResponse({
            "strength": strength,
            "valid": strength['score'] >= 3  # Require at least "good" strength
        })

    except Exception as e:
        logger.error(f"Password strength check error: {str(e)}")
        return JsonResponse({"error": "خطا در بررسی قدرت رمز عبور"}, status=500)


# Dashboard view if not exists elsewhere
@login_required
def dashboard_view(request):
    """Simple dashboard view - redirect to actual dashboard if exists"""
    try:
        # Try to import and use existing dashboard view
        from .dashboard_views import dashboard_view as existing_dashboard
        return existing_dashboard(request)
    except ImportError:
        # Fallback simple dashboard
        context = {
            'user': request.user,
            'recent_activity': [],
            'notifications': [],
        }
        return render(request, 'users/dashboard.html', context)
