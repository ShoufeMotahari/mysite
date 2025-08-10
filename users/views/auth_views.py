# users/views/auth_views.py
import logging
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password, make_password
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from core.email import send_activation_email  # ADD THIS LINE
from core.sms import send_verification_sms
from users.forms.forms import (
    CustomUserCreationForm,
    ForgotPasswordForm,
    LoginForm,
    SignupForm,
    VerificationForm,
)
from users.models import User, VerificationToken

logger = logging.getLogger("users")

# Console logger for development
console_logger = logging.getLogger("console")
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("🔑 ACTIVATION INFO: %(message)s")
console_handler.setFormatter(formatter)
console_logger.addHandler(console_handler)
console_logger.setLevel(logging.INFO)


def signup_view(request):
    """Handle user registration with console logging for activation codes"""
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            mobile = form.cleaned_data["mobile"]
            email = form.cleaned_data.get("email")
            password = form.cleaned_data["password"]

            logger.info(
                f"Signup attempt - Username: {username}, Mobile: {mobile}, Email: {email}"
            )

            # Create or get existing user
            user, created = User.objects.get_or_create(
                mobile=mobile,
                defaults={
                    "username": username,
                    "mobile": mobile,
                    "email": email,
                    "password": make_password(password),
                    "is_active": False,
                    "is_phone_verified": False,
                    "is_email_verified": False,
                },
            )

            if created:
                logger.info(
                    f"New user created - Username: {username}, Mobile: {mobile}"
                )
            else:
                logger.warning(
                    f"Signup attempt for existing user - Mobile: {user.mobile}"
                )
                if user.is_active and user.is_phone_verified:
                    messages.error(request, "این کاربر قبلاً فعال شده است.")
                    return redirect("users:login")
                else:
                    # Update existing inactive user with new information
                    user.username = username
                    user.email = email
                    user.password = make_password(password)
                    user.save()

            # Generate SMS verification code
            sms_code = VerificationToken.generate_sms_token()

            # Delete any existing registration tokens for this user
            VerificationToken.objects.filter(
                user=user, token_type="registration"
            ).delete()

            verification_token = VerificationToken.objects.create(
                user=user, token=sms_code, token_type="registration"
            )

            # 🔑 CONSOLE LOGGING FOR ACTIVATION CODE
            console_logger.info(f"SMS Code for {mobile}: {sms_code}")

            logger.info(
                f"SMS verification code generated - Code: {sms_code} for Mobile: {mobile}"
            )

            # Send SMS
            try:
                send_verification_sms(mobile, sms_code)
                logger.info(f"SMS sent to {mobile}")
            except Exception as e:
                logger.error(f"Failed to send SMS to {mobile}: {e}")
                messages.error(request, "خطا در ارسال پیامک. لطفاً دوباره تلاش کنید.")
                return render(request, "users/signup.html", {"form": form})

            # Send activation email if email provided
            if email:
                try:
                    # FIXED: Use the proper email function instead of manual construction
                    email_token = str(verification_token.email_token)

                    # Use the proper email sending function
                    email_sent = send_activation_email(user, email_token, request)

                    if email_sent:
                        logger.info(f"Activation email sent successfully to {email}")

                        # 🔑 CONSOLE LOGGING FOR EMAIL ACTIVATION (for development)
                        activation_link = f"{settings.SITE_URL}{reverse('users:activate')}?token={email_token}"
                        console_logger.info(
                            f"Email activation link for {email}: {activation_link}"
                        )
                        console_logger.info(f"Email Token: {email_token}")
                    else:
                        logger.error(f"Failed to send activation email to {email}")

                except Exception as e:
                    logger.error(f"Failed to send activation email to {email}: {e}")

            # Store in session
            request.session["mobile"] = mobile
            request.session["signup_user_id"] = user.id

            if email:
                messages.success(
                    request,
                    "کد تایید به شماره موبایل و لینک فعال‌سازی به ایمیل شما ارسال شد.",
                )
            else:
                messages.success(request, "کد تایید به شماره موبایل شما ارسال شد.")

            logger.info(f"Redirecting to verify view - User ID: {user.id}")
            return redirect("users:verify")
        else:
            logger.warning("Signup form is invalid.")
            logger.debug(f"Form errors: {form.errors}")
    else:
        form = SignupForm()
        logger.info("Signup page accessed via GET")

    return render(request, "users/signup.html", {"form": form})


def login_view(request):
    """Simple login view with username/password authentication"""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["identifier"]
            password = form.cleaned_data["password"]

            logger.info(f"Login attempt - Identifier: {identifier}")

            # Find user by username, mobile or email
            user = None
            try:
                # Try to find by username first
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                # Then try email
                if "@" in identifier:
                    try:
                        user = User.objects.get(email=identifier)
                    except User.DoesNotExist:
                        pass
                else:
                    # Finally try mobile
                    clean_mobile = identifier.replace(" ", "").replace("-", "")
                    try:
                        user = User.objects.get(mobile=clean_mobile)
                    except User.DoesNotExist:
                        pass

            if not user:
                messages.error(request, "کاربر یافت نشد.")
                logger.warning(f"User not found - Identifier: {identifier}")
                return render(request, "users/login.html", {"form": form})

            # Check password
            if not check_password(password, user.password):
                messages.error(request, "رمز عبور اشتباه است.")
                logger.warning(f"Invalid password attempt - User: {user.username}")
                return render(request, "users/login.html", {"form": form})

            # Check if user is active
            if not user.is_active:
                messages.error(
                    request, "حساب شما فعال نیست. لطفاً با پشتیبانی تماس بگیرید."
                )
                logger.warning(f"Inactive user login attempt - User: {user.username}")
                return render(request, "users/login.html", {"form": form})

            # Successful login
            login(request, user)
            messages.success(request, f"خوش آمدید {user.username}!")
            logger.info(f"User logged in successfully - User: {user.username}")
            return redirect("users:dashboard")

    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def forgot_password_view(request):
    """Handle forgot password requests - send both SMS and Email"""
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["identifier"]

            logger.info(f"Forgot password request - Identifier: {identifier}")

            # === EMAIL TEST - Add this for debugging ===
            print("\n" + "=" * 50)
            print("🔧 TESTING EMAIL FUNCTIONALITY")
            print("=" * 50)

            from django.conf import settings
            from django.core.mail import send_mail

            try:
                send_mail(
                    subject="Test Email from Django",
                    message="This is a test email to verify console backend is working.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=["test@example.com"],
                    fail_silently=False,
                )
                print("✅ EMAIL TEST: Successfully sent test email")
            except Exception as e:
                print(f"❌ EMAIL TEST FAILED: {e}")

            print("=" * 50 + "\n")
            # === END EMAIL TEST ===

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

            # === NEW: SEND EMAIL IF USER HAS EMAIL ===
            if user.email:
                try:
                    print(f"\n🔧 ATTEMPTING TO SEND EMAIL TO: {user.email}")

                    # Import the email function
                    from core.email import send_password_reset_email

                    # Generate email token (you can use the same reset_code or create a different one)
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
            return redirect("usesr:verify_reset_password")

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
                    return redirect("reset_password")
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
    """Handle password reset after SMS verification"""
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

        try:
            # Update password
            user.set_password(new_password)
            user.save()

            # Clear session data
            request.session.pop("reset_user_id", None)
            request.session.pop("password_reset_verified", None)

            console_logger.info(f"Password reset completed for user: {user.username}")
            logger.info(f"Password reset successful - User: {user.username}")

            # Automatically log in the user
            login(request, user)
            messages.success(
                request, "رمز عبور شما با موفقیت تغییر یافت و وارد سیستم شدید."
            )
            return redirect("dashboard")

        except Exception as e:
            logger.error(
                f"Password reset error - User: {user.username}, Error: {str(e)}"
            )
            messages.error(request, "خطا در تغییر رمز عبور. لطفاً دوباره تلاش کنید.")

    return render(request, "users/reset_password.html")


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


def verify_view(request):
    """Handle SMS verification for registration with console logging"""
    mobile = request.session.get("mobile")
    user_id = request.session.get("signup_user_id")

    if not mobile or not user_id:
        messages.error(request, "جلسه منقضی شده است. لطفاً دوباره ثبت‌نام کنید.")
        return redirect("users:signup")

    try:
        user = User.objects.get(id=user_id, mobile=mobile)
    except User.DoesNotExist:
        messages.error(request, "کاربر یافت نشد.")
        return redirect("users:signup")

    if request.method == "POST":
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            try:
                token = VerificationToken.objects.get(
                    user=user, token=code, token_type="registration", is_used=False
                )

                if token.is_valid():
                    user.is_active = True
                    user.is_phone_verified = True
                    user.save()
                    token.mark_as_used()

                    # Automatic login
                    login(request, user)

                    # Clear session
                    request.session.pop("mobile", None)
                    request.session.pop("signup_user_id", None)

                    console_logger.info(
                        f"User successfully verified: {user.username} ({user.mobile})"
                    )
                    messages.success(
                        request, "حساب شما با موفقیت فعال شد و وارد سیستم شدید."
                    )
                    logger.info(
                        f"User successfully verified and logged in - User ID: {user.id}"
                    )
                    return redirect("users:dashboard")

                else:
                    messages.error(request, "کد وارد شده منقضی شده است.")
                    logger.warning(
                        f"Expired verification code used - User ID: {user.id}"
                    )

            except VerificationToken.DoesNotExist:
                messages.error(request, "کد وارد شده صحیح نمی‌باشد.")
                logger.warning(
                    f"Invalid verification code entered - User ID: {user.id}"
                )

        else:
            logger.warning(f"Invalid verification form - Errors: {form.errors}")
    else:
        form = VerificationForm()

    # Display mobile number on verification page
    masked_mobile = mobile[:3] + "*****" + mobile[-3:] if mobile else ""

    return render(
        request,
        "users/verify.html",
        {"form": form, "mobile": mobile, "masked_mobile": masked_mobile},
    )


def verify_login_view(request):
    """Handle SMS verification for login with console logging"""
    user_id = request.session.get("login_user_id")
    if not user_id:
        messages.error(request, "جلسه منقضی شده است.")
        return redirect("users:login")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "کاربر یافت نشد.")
        return redirect("users:login")

    if request.method == "POST":
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            try:
                token = VerificationToken.objects.get(
                    user=user, token=code, token_type="login", is_used=False
                )

                if token.is_valid():
                    login(request, user)
                    token.mark_as_used()
                    request.session.pop("login_user_id", None)

                    console_logger.info(
                        f"User login verified: {user.username} ({user.mobile})"
                    )
                    messages.success(request, "با موفقیت وارد شدید.")
                    return redirect("dashboard")
                else:
                    messages.error(request, "کد وارد شده منقضی شده است.")

            except VerificationToken.DoesNotExist:
                messages.error(request, "کد وارد شده صحیح نمی‌باشد.")
        else:
            logger.warning(f"Invalid verification form - Errors: {form.errors}")
    else:
        form = VerificationForm()

    # Display mobile number on verification page
    masked_mobile = user.mobile[:3] + "*****" + user.mobile[-3:] if user.mobile else ""

    return render(
        request,
        "users/verify_login.html",
        {"form": form, "mobile": user.mobile, "masked_mobile": masked_mobile},
    )


def activate_account_view(request):
    """Handle email activation and redirect to dashboard"""
    token = request.GET.get("token")

    if not token:
        messages.error(request, "لینک فعال‌سازی نامعتبر است.")
        return redirect("users:login")

    try:
        # Find the verification token
        verification_token = VerificationToken.objects.get(
            email_token=token, token_type="registration"
        )

        user = verification_token.user

        # Check if token is still valid (not expired)
        if verification_token.is_expired():
            messages.error(request, "لینک فعال‌سازی منقضی شده است.")
            verification_token.delete()
            return redirect("users:signup")

        # Activate the user
        user.is_active = True
        user.is_email_verified = True
        user.save()

        # Delete the used token
        verification_token.delete()

        logger.info(f"User {user.email} activated successfully via email")

        # Log the user in automatically
        from django.contrib.auth import login

        login(request, user)

        messages.success(request, "حساب شما با موفقیت فعال شد!")

        # Redirect to dashboard
        return redirect("users:dashboard")

    except VerificationToken.DoesNotExist:
        logger.warning(f"Invalid activation token attempted: {token}")
        messages.error(request, "لینک فعال‌سازی نامعتبر است.")
        return redirect("users:login")

    except Exception as e:
        logger.error(f"Activation error: {str(e)}")
        messages.error(request, "خطا در فعال‌سازی حساب.")
        return redirect("users:login")


def send_sms_view(request):
    """Development helper for testing SMS"""
    phone = request.GET.get("phone")
    code = str(random.randint(100000, 999999))

    console_logger.info(f"Test SMS Code for {phone}: {code}")

    try:
        send_verification_sms(phone, code)
        return JsonResponse({"status": "sms sent", "code": code})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


def register(request):
    """Alternative registration view"""
    client_ip = request.META.get(
        "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR")
    )
    user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")

    logger.info(
        f"Registration page accessed - IP: {client_ip}, User-Agent: {user_agent}"
    )

    if request.method == "POST":
        logger.info(f"Registration form submitted - IP: {client_ip}")
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            try:
                user = form.save()
                logger.info(
                    f"User created successfully - Username: {user.username}, Email: {user.email}, IP: {client_ip}"
                )

                console_logger.info(
                    f"New user registered: {user.username} ({user.email})"
                )

                login(request, user)
                logger.info(
                    f"User logged in after registration - Username: {user.username}, IP: {client_ip}"
                )

                messages.success(request, "Registration successful!")
                return redirect("dashboard")

            except Exception as e:
                logger.error(f"Registration failed - IP: {client_ip}, Error: {str(e)}")
                messages.error(request, "An error occurred during registration.")
        else:
            logger.warning(
                f"Invalid registration form - IP: {client_ip}, Errors: {form.errors}"
            )
    else:
        form = CustomUserCreationForm()

    return render(request, "users/registration/register.html", {"form": form})
