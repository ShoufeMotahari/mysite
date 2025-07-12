from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_verification_email(user, code):
    subject = 'کد تأیید شما'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    text_content = f'کد تایید شما: {code}'
    html_content = render_to_string('emails/verification_email.html', {'user': user, 'code': code})

    msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    msg.attach_alternative(html_content, "text/html")
    msg.send()