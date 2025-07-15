# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.core.mail import send_mail
# from django.contrib.auth import get_user_model
# from django.conf import settings
# from comments.models import Comment
#
# @receiver(post_save, sender=Comment)
# def notify_admins_on_new_comment(sender, instance, created, **kwargs):
#     if created:
#         User = get_user_model()
#         admins = User.objects.filter(is_superuser=True, email__isnull=False)
#
#         subject = '📩 نظر جدید ثبت شد'
#         message = f'یک کامنت جدید توسط {instance.user} ثبت شد:\n\n{instance.content}'
#
#         for admin in admins:
#             send_mail(
#                 subject,
#                 message,
#                 settings.DEFAULT_FROM_EMAIL,
#                 [admin.email],
#                 fail_silently=True
#             )
