# from django.shortcuts import render, redirect
# from .forms import CommentForm
# from django.contrib.auth.decorators import login_required
# from django.core.mail import send_mail
# from django.contrib.auth import get_user_model
# from .models import Comment
# import logging
#
# logger = logging.getLogger('comments')
#
# @login_required
# def submit_comment(request):
#     if request.method == 'POST':
#         form = CommentForm(request.POST)
#         if form.is_valid():
#             comment = form.save(commit=False)
#             comment.user = request.user
#             comment.save()
#
#             # ارسال ایمیل برای همه ادمین‌ها
#             User = get_user_model()
#             admins = User.objects.filter(is_superuser=True)
#             subject = 'کامنت جدید ثبت شد'
#             message = f"کاربر {request.user} یک کامنت جدید ثبت کرده:\n\n{comment.content}"
#             from_email = 'no-reply@example.com'
#             recipient_list = [admin.email for admin in admins if admin.email]
#
#             for email in recipient_list:
#                 try:
#                     send_mail(subject, message, from_email, [email])
#                     logger.info("✅ one maile sent %s", email)
#                 except Exception as e:
#                     logger.error("❌ sending email with wrong  %s: %s", email, str(e))
#
#             return redirect('comment-success')
#     else:
#         form = CommentForm()
#
#     return render(request, 'comments/submit_comment.html', {'form': form})
#
