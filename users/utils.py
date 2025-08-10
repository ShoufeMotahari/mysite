# from django.core.mail import EmailMultiAlternatives
# from django.template.loader import render_to_string
# from django.conf import settings
#
# def send_verification_email(user, code):
#     subject = 'کد تأیید شما'
#     from_email = settings.DEFAULT_FROM_EMAIL
#     recipient_list = [user.email]
#
#     text_content = f'کد تایید شما: {code}'
#     html_content = render_to_string('emails/verification_email.html', {'user': user, 'code': code})
#
#     msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
#     msg.attach_alternative(html_content, "text/html")
#     msg.send()

from io import BytesIO

from PIL import Image


class ImageMinifier:
    """Utility class for image minification"""

    @staticmethod
    def minify_image(image_file, quality=85, max_width=1920, max_height=1080):
        """
        Minify an image file

        Args:
            image_file: Django ImageField file
            quality: JPEG quality (1-100)
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels

        Returns:
            tuple: (minified_file_content, original_size, new_size)
        """
        # Open image
        image = Image.open(image_file)
        original_size = (
            image_file.size if hasattr(image_file, "size") else len(image_file.read())
        )
        image_file.seek(0)  # Reset file pointer

        # Convert RGBA to RGB if necessary
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(
                image, mask=image.split()[-1] if image.mode == "RGBA" else None
            )
            image = background

        # Resize if needed
        if image.size[0] > max_width or image.size[1] > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Save to BytesIO
        output = BytesIO()
        format_type = (
            "JPEG" if image_file.name.lower().endswith((".jpg", ".jpeg")) else "PNG"
        )

        if format_type == "JPEG":
            image.save(output, format=format_type, quality=quality, optimize=True)
        else:
            image.save(output, format=format_type, optimize=True)

        output.seek(0)
        new_size = len(output.getvalue())

        return output.getvalue(), original_size, new_size
