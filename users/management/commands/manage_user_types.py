# users/management/commands/manage_user_types.py
"""
Management command for user type operations
Usage:
    python manage.py manage_user_types --create-defaults
    python manage.py manage_user_types --list
    python manage.py manage_user_types --assign-type subscriber --to-users user1,user2
    python manage.py manage_user_types --bulk-assign subscriber --filter is_active=True
    python manage.py manage_user_types --stats
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q

from users.models import UserType

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "Manage user types and assignments"

    def add_arguments(self, parser):
        # Actions
        parser.add_argument(
            "--create-defaults", action="store_true", help="Create default user types"
        )

        parser.add_argument("--list", action="store_true", help="List all user types")

        parser.add_argument(
            "--stats", action="store_true", help="Show user type statistics"
        )

        # Assignment operations
        parser.add_argument(
            "--assign-type",
            type=str,
            help="Assign user type to specific users (use with --to-users)",
        )

        parser.add_argument(
            "--to-users", type=str, help="Comma-separated list of usernames/emails"
        )

        parser.add_argument(
            "--bulk-assign",
            type=str,
            help="Bulk assign user type to users matching filter (use with --filter)",
        )

        parser.add_argument(
            "--filter",
            type=str,
            help='Filter for bulk operations (e.g., "is_active=True,is_staff=False")',
        )

        # Utility operations
        parser.add_argument(
            "--set-default", type=str, help="Set a user type as default"
        )

        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Assign default type to users without type",
        )

    def handle(self, *args, **options):
        try:
            if options["create_defaults"]:
                self.create_default_types()
            elif options["list"]:
                self.list_user_types()
            elif options["stats"]:
                self.show_stats()
            elif options["assign_type"] and options["to_users"]:
                self.assign_type_to_users(options["assign_type"], options["to_users"])
            elif options["bulk_assign"] and options["filter"]:
                self.bulk_assign_type(options["bulk_assign"], options["filter"])
            elif options["set_default"]:
                self.set_default_type(options["set_default"])
            elif options["cleanup"]:
                self.cleanup_users_without_type()
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "Please specify an action. Use --help for available options."
                    )
                )
        except Exception as e:
            logger.error(f"Management command error: {str(e)}")
            raise CommandError(f"Operation failed: {str(e)}")

    def create_default_types(self):
        """Create default user types"""
        self.stdout.write("Creating default user types...")

        default_types = [
            {
                "name": "مشترک",
                "slug": "subscriber",
                "description": "کاربر عادی سیستم",
                "can_create_content": False,
                "can_edit_content": False,
                "can_delete_content": False,
                "can_manage_users": False,
                "can_view_analytics": False,
                "can_access_admin": False,
                "max_posts_per_day": 0,
                "max_comments_per_day": 10,
                "max_file_upload_size_mb": 5,
                "is_active": True,
                "is_default": True,
            },
            {
                "name": "نویسنده",
                "slug": "author",
                "description": "ایجاد و ویرایش محتوای شخصی",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": False,
                "can_manage_users": False,
                "can_view_analytics": False,
                "can_access_admin": False,
                "max_posts_per_day": 10,
                "max_comments_per_day": 30,
                "max_file_upload_size_mb": 15,
                "is_active": True,
                "is_default": False,
            },
            {
                "name": "ویرایشگر",
                "slug": "editor",
                "description": "ویرایش و مدیریت محتوا",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": False,
                "can_manage_users": False,
                "can_view_analytics": True,
                "can_access_admin": True,
                "max_posts_per_day": 30,
                "max_comments_per_day": 50,
                "max_file_upload_size_mb": 25,
                "is_active": True,
                "is_default": False,
            },
            {
                "name": "مدیر محتوا",
                "slug": "manager",
                "description": "مدیریت محتوا و کاربران",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": True,
                "can_manage_users": True,
                "can_view_analytics": True,
                "can_access_admin": True,
                "max_posts_per_day": 50,
                "max_comments_per_day": 100,
                "max_file_upload_size_mb": 50,
                "is_active": True,
                "is_default": False,
            },
            {
                "name": "مدیر سیستم",
                "slug": "admin",
                "description": "دسترسی کامل به سیستم",
                "can_create_content": True,
                "can_edit_content": True,
                "can_delete_content": True,
                "can_manage_users": True,
                "can_view_analytics": True,
                "can_access_admin": True,
                "max_posts_per_day": None,
                "max_comments_per_day": None,
                "max_file_upload_size_mb": 100,
                "is_active": True,
                "is_default": False,
            },
        ]

        created_count = 0
        for type_data in default_types:
            user_type, created = UserType.objects.get_or_create(
                slug=type_data["slug"], defaults=type_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created user type: {user_type.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"- User type already exists: {user_type.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nCompleted! {created_count} new user types created.")
        )

    def list_user_types(self):
        """List all user types"""
        user_types = UserType.objects.annotate(users_count=Count("user")).order_by(
            "name"
        )

        if not user_types.exists():
            self.stdout.write(self.style.WARNING("No user types found."))
            return

        self.stdout.write("\nUser Types:")
        self.stdout.write("=" * 80)

        for user_type in user_types:
            status_indicators = []
            if user_type.is_default:
                status_indicators.append("DEFAULT")
            if not user_type.is_active:
                status_indicators.append("INACTIVE")

            status = f" [{', '.join(status_indicators)}]" if status_indicators else ""

            self.stdout.write(f"\n{user_type.name}{status}")
            self.stdout.write(f"  Slug: {user_type.slug}")
            self.stdout.write(f"  Users: {user_type.users_count}")
            self.stdout.write(f'  Description: {user_type.description or "N/A"}')

            # Permissions
            permissions = []
            if user_type.can_create_content:
                permissions.append("Create")
            if user_type.can_edit_content:
                permissions.append("Edit")
            if user_type.can_delete_content:
                permissions.append("Delete")
            if user_type.can_manage_users:
                permissions.append("Manage Users")
            if user_type.can_view_analytics:
                permissions.append("Analytics")
            if user_type.can_access_admin:
                permissions.append("Admin Access")

            self.stdout.write(f'  Permissions: {", ".join(permissions) or "None"}')

            # Limits
            limits = []
            if user_type.max_posts_per_day:
                limits.append(f"{user_type.max_posts_per_day} posts/day")
            if user_type.max_comments_per_day:
                limits.append(f"{user_type.max_comments_per_day} comments/day")
            if user_type.max_file_upload_size_mb:
                limits.append(f"{user_type.max_file_upload_size_mb}MB upload")

            self.stdout.write(f'  Limits: {", ".join(limits) or "None"}')

    def show_stats(self):
        """Show user type statistics"""
        total_users = User.objects.count()
        users_with_type = User.objects.filter(user_type__isnull=False).count()
        users_without_type = total_users - users_with_type

        self.stdout.write("\nUser Type Statistics:")
        self.stdout.write("=" * 40)
        self.stdout.write(f"Total Users: {total_users}")
        self.stdout.write(f"Users with Type: {users_with_type}")
        self.stdout.write(f"Users without Type: {users_without_type}")

        if users_without_type > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠ {users_without_type} users have no type assigned!"
                )
            )

        # Type distribution
        type_stats = (
            UserType.objects.annotate(users_count=Count("user"))
            .filter(users_count__gt=0)
            .order_by("-users_count")
        )

        if type_stats.exists():
            self.stdout.write("\nDistribution by Type:")
            self.stdout.write("-" * 30)
            for stat in type_stats:
                percentage = (stat.users_count / total_users) * 100
                self.stdout.write(
                    f"{stat.name}: {stat.users_count} ({percentage:.1f}%)"
                )

    def assign_type_to_users(self, type_slug, users_list):
        """Assign user type to specific users"""
        try:
            user_type = UserType.objects.get(slug=type_slug, is_active=True)
        except UserType.DoesNotExist:
            raise CommandError(f'User type "{type_slug}" not found or inactive.')

        user_identifiers = [u.strip() for u in users_list.split(",")]
        users = User.objects.filter(
            Q(username__in=user_identifiers)
            | Q(email__in=user_identifiers)
            | Q(mobile__in=user_identifiers)
        )

        if not users.exists():
            raise CommandError("No users found with provided identifiers.")

        updated_count = 0
        for user in users:
            old_type = user.user_type
            user.user_type = user_type

            # Auto-update staff status
            if user_type.can_access_admin:
                user.is_staff = True
            elif (
                old_type
                and old_type.can_access_admin
                and not user_type.can_access_admin
            ):
                user.is_staff = False

            user.save()
            updated_count += 1

            old_type_name = old_type.name if old_type else "None"
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {user.get_display_name()}: {old_type_name} → {user_type.name}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"\nCompleted! {updated_count} users updated.")
        )

    def bulk_assign_type(self, type_slug, filter_str):
        """Bulk assign user type based on filter"""
        try:
            user_type = UserType.objects.get(slug=type_slug, is_active=True)
        except UserType.DoesNotExist:
            raise CommandError(f'User type "{type_slug}" not found or inactive.')

        # Parse filter
        filter_dict = {}
        for filter_item in filter_str.split(","):
            if "=" in filter_item:
                key, value = filter_item.strip().split("=", 1)
                # Convert string boolean values
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                filter_dict[key] = value

        if not filter_dict:
            raise CommandError("Invalid filter format. Use key=value,key2=value2")

        users = User.objects.filter(**filter_dict)
        user_count = users.count()

        if user_count == 0:
            self.stdout.write(self.style.WARNING("No users match the filter criteria."))
            return

        # Confirm bulk operation
        self.stdout.write(f'This will assign "{user_type.name}" to {user_count} users.')
        self.stdout.write(f"Filter: {filter_dict}")

        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() != "yes":
            self.stdout.write("Operation cancelled.")
            return

        updated_count = 0
        for user in users:
            old_type = user.user_type
            user.user_type = user_type

            # Auto-update staff status
            if user_type.can_access_admin:
                user.is_staff = True
            elif (
                old_type
                and old_type.can_access_admin
                and not user_type.can_access_admin
            ):
                user.is_staff = False

            user.save()
            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'✓ Updated {updated_count} users to "{user_type.name}"')
        )

    def set_default_type(self, type_slug):
        """Set a user type as default"""
        try:
            user_type = UserType.objects.get(slug=type_slug, is_active=True)
        except UserType.DoesNotExist:
            raise CommandError(f'User type "{type_slug}" not found or inactive.')

        # Remove default from other types
        UserType.objects.filter(is_default=True).update(is_default=False)

        # Set new default
        user_type.is_default = True
        user_type.save()

        self.stdout.write(
            self.style.SUCCESS(f'✓ "{user_type.name}" set as default user type.')
        )

    def cleanup_users_without_type(self):
        """Assign default type to users without type"""
        try:
            default_type = UserType.get_default_type()
        except Exception as e:
            raise CommandError(f"No default user type found: {str(e)}")

        users_without_type = User.objects.filter(user_type__isnull=True)
        count = users_without_type.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("All users already have a type assigned.")
            )
            return

        self.stdout.write(f"Found {count} users without type.")
        confirm = input(f'Assign "{default_type.name}" to all of them? (yes/no): ')

        if confirm.lower() != "yes":
            self.stdout.write("Operation cancelled.")
            return

        updated = users_without_type.update(user_type=default_type)

        self.stdout.write(
            self.style.SUCCESS(f'✓ Assigned "{default_type.name}" to {updated} users.')
        )

    def get_user_type_by_slug_or_name(self, identifier):
        """Get user type by slug or name"""
        try:
            return UserType.objects.get(
                Q(slug=identifier) | Q(name=identifier), is_active=True
            )
        except UserType.DoesNotExist:
            available_types = UserType.objects.filter(is_active=True).values_list(
                "slug", "name"
            )
            available_list = [f"{slug} ({name})" for slug, name in available_types]
            raise CommandError(
                f'User type "{identifier}" not found. Available types: {", ".join(available_list)}'
            )
