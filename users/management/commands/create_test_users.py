import random

from django.core.management.base import BaseCommand

from users.models import User


class Command(BaseCommand):
    help = "ایجاد ۱۰ کاربر تستی"

    def handle(self, *args, **kwargs):
        i = random.randint(1, 10000000)
        for i in range(i, i + 10):
            mobile = f"09900000{i:03}"
            email = f"user{i}@test.com"
            user, created = User.objects.get_or_create(
                mobile=mobile,
                defaults={
                    "username": f"testuser{i}",
                    "email": email,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ ایجاد شد: {user.username}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ قبلاً وجود دارد: {user.username}")
                )
