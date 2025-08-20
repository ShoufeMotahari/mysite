# users/management/commands/create_message_admin_type.py
from django.core.management.base import BaseCommand

from users.models.user.user_type import UserType


class Command(BaseCommand):
    help = "Create message admin user type"

    def handle(self, *args, **options):
        # Create message admin user type
        message_admin_type, created = UserType.objects.get_or_create(
            slug="message_admin",
            defaults={
                "name": "ادمین پیام‌رسان",
                "description": "ادمین با دسترسی محدود به ارسال پیام",
                "can_create_content": False,
                "can_edit_content": False,
                "can_delete_content": False,
                "can_manage_users": False,
                "can_view_analytics": False,
                "can_access_admin": True,  # Limited admin access
                "max_posts_per_day": 0,
                "max_comments_per_day": 0,
                "max_file_upload_size_mb": 0,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created message admin user type: {message_admin_type.name}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Message admin user type already exists: {message_admin_type.name}"
                )
            )


# Alternative: Data migration approach
# Create this as a Django migration file:

# messaging/migrations/0002_create_message_admin_usertype.py
from django.db import migrations


def create_message_admin_usertype(apps, schema_editor):
    """Create message admin user type"""
    UserType = apps.get_model("users", "UserType")

    UserType.objects.get_or_create(
        slug="message_admin",
        defaults={
            "name": "ادمین پیام‌رسان",
            "description": "ادمین با دسترسی محدود به ارسال پیام",
            "can_create_content": False,
            "can_edit_content": False,
            "can_delete_content": False,
            "can_manage_users": False,
            "can_view_analytics": False,
            "can_access_admin": True,
            "max_posts_per_day": 0,
            "max_comments_per_day": 0,
            "max_file_upload_size_mb": 0,
            "is_active": True,
        },
    )


def reverse_create_message_admin_usertype(apps, schema_editor):
    """Remove message admin user type"""
    UserType = apps.get_model("users", "UserType")
    UserType.objects.filter(slug="message_admin").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0001_initial"),
        ("users", "0001_initial"),  # Adjust based on your users app migration
    ]

    operations = [
        migrations.RunPython(
            create_message_admin_usertype, reverse_create_message_admin_usertype
        ),
    ]
