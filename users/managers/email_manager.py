# managers/email_manager.py
import logging
from abc import ABC, abstractmethod


from users.models import EmailTemplate
from users.services.email_service import EmailServiceFactory

logger = logging.getLogger("email_manager")


class Command(ABC):
    @abstractmethod
    def execute(self):
        pass


class SendEmailCommand(Command):
    def __init__(
        self, template_id, user_ids, sender, custom_subject=None, custom_content=None
    ):
        self.template_id = template_id
        self.user_ids = user_ids
        self.sender = sender
        self.custom_subject = custom_subject
        self.custom_content = custom_content
        self.logger = logging.getLogger("email_manager")

    def execute(self):
        try:
            self.logger.info(
                f"🚀 Executing email command - Template ID: {self.template_id}"
            )
            self.logger.info(f"📊 Processing {len(self.user_ids)} users")

            # Get template
            template = EmailTemplate.objects.get(id=self.template_id)
            self.logger.info(f"📝 Using email template: '{template.name}'")

            # Prepare email data
            subject = self.custom_subject or template.subject
            content = self.custom_content or template.content

            # Get recipients
            from django.contrib.auth import get_user_model

            User = get_user_model()
            users = User.objects.filter(id__in=self.user_ids)

            if not users.exists():
                error_msg = "No users found with provided IDs"
                self.logger.error(f"❌ {error_msg}")
                return False, error_msg, {}

            self.logger.info(f"📧 Email details:")
            self.logger.info(f"  📋 Subject: '{subject}'")
            self.logger.info(f"  👥 Found {users.count()} users in database")

            # Log all users being processed
            self.logger.info(f"👤 Users to process:")
            for user in users:
                status = "✅ Active" if user.is_active else "❌ Inactive"
                email_status = "✅ Valid" if user.email else "❌ No email"
                self.logger.info(
                    f"  - {user.username} (ID: {user.id}): {status}, Email: '{user.email}' ({email_status})"
                )

            # Send email
            sender_info = f"{self.sender.username} ({self.sender.email})"
            email_service = EmailServiceFactory.create_email_service()
            success, message, details = email_service.send_email(
                users, subject, content, sender_info
            )

            # Log detailed results
            self.logger.info(f"📈 Command execution results:")
            self.logger.info(f"  🎯 Success: {success}")
            self.logger.info(
                f"  📊 Total users processed: {details.get('total_users', 0)}"
            )
            self.logger.info(
                f"  ✅ Valid users (sent): {details.get('valid_users', 0)}"
            )
            self.logger.info(
                f"  ❌ Invalid users (skipped): {details.get('invalid_users', 0)}"
            )

            if success:
                self.logger.info(f"✅ Email command completed successfully: {message}")
                self.logger.info(f"🎉 Command execution summary:")
                self.logger.info(f"  📝 Template: '{template.name}'")
                self.logger.info(f"  👤 Sender: {sender_info}")
                self.logger.info(
                    f"  📊 Results: {details.get('valid_users', 0)}/{details.get('total_users', 0)} users"
                )
            else:
                self.logger.error(f"❌ Email command failed: {message}")

                # Log invalid users details if any
                if details.get("invalid_details"):
                    self.logger.error(f"💥 Invalid users breakdown:")
                    for invalid_user in details["invalid_details"]:
                        user = invalid_user["user"]
                        issues = invalid_user["issues"]
                        self.logger.error(f"  - {user.username}: {', '.join(issues)}")

            return success, message, details

        except EmailTemplate.DoesNotExist:
            error_msg = f"Email template with ID {self.template_id} not found"
            self.logger.error(f"❌ {error_msg}")
            return False, error_msg, {}
        except Exception as e:
            error_msg = f"Error executing email command: {str(e)}"
            self.logger.error(f"❌ {error_msg}")
            self.logger.exception("Full exception details:")
            return False, error_msg, {}


class EmailManager:
    def __init__(self):
        self.commands = []
        self.logger = logging.getLogger("email_manager")

    def add_command(self, command: Command):
        self.commands.append(command)
        self.logger.info(
            f"➕ Command added to email manager. Total commands: {len(self.commands)}"
        )

    def execute_commands(self):
        self.logger.info(f"🎯 Executing {len(self.commands)} email commands")
        results = []

        for i, command in enumerate(self.commands, 1):
            self.logger.info(f"⚡ Executing command {i}/{len(self.commands)}")
            result = command.execute()
            results.append(result)

            success, message, details = result
            if success:
                self.logger.info(f"✅ Command {i} completed successfully")
                self.logger.info(f"  📊 Sent to {details.get('valid_users', 0)} users")
                if details.get("invalid_users", 0) > 0:
                    self.logger.info(
                        f"  ⚠️ Skipped {details.get('invalid_users', 0)} invalid users"
                    )
            else:
                self.logger.error(f"❌ Command {i} failed: {message}")

        # Summary
        successful_commands = sum(1 for r in results if r[0])
        failed_commands = sum(1 for r in results if not r[0])

        self.logger.info(f"📊 Email manager execution complete:")
        self.logger.info(f"  ✅ Successful commands: {successful_commands}")
        self.logger.info(f"  ❌ Failed commands: {failed_commands}")

        # Calculate total users processed
        total_sent = sum(r[2].get("valid_users", 0) for r in results if r[0])
        total_skipped = sum(r[2].get("invalid_users", 0) for r in results if r[0])

        if total_sent > 0:
            self.logger.info(f"  📧 Total emails sent: {total_sent}")
        if total_skipped > 0:
            self.logger.info(f"  ⚠️ Total users skipped: {total_skipped}")

        self.commands.clear()
        return results
