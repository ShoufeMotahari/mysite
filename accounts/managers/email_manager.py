# managers/email_manager.py
from abc import ABC, abstractmethod
import logging
import json
from django.utils import timezone

from accounts.services.email_service import EmailServiceFactory
from core.models import EmailTemplate

logger = logging.getLogger('email_manager')


class Command(ABC):
    @abstractmethod
    def execute(self):
        pass


class SendEmailCommand(Command):
    def __init__(self, template_id, user_ids, sender, custom_subject=None, custom_content=None):
        self.template_id = template_id
        self.user_ids = user_ids
        self.sender = sender
        self.custom_subject = custom_subject
        self.custom_content = custom_content
        self.logger = logging.getLogger('email_manager')

    def execute(self):
        try:
            self.logger.info(
                f"🚀 Executing email command - Template ID: {self.template_id}, Users: {len(self.user_ids)}")

            # Get template
            template = EmailTemplate.objects.get(id=self.template_id)
            self.logger.info(f"Using email template: '{template.name}'")

            # Prepare email data
            subject = self.custom_subject or template.subject
            content = self.custom_content or template.content

            # Get recipients
            from django.contrib.auth import get_user_model
            User = get_user_model()
            users = User.objects.filter(id__in=self.user_ids)

            self.logger.info(f"Email details - Subject: '{subject}', Recipients: {users.count()}")

            # Log recipient details
            recipient_info = []
            for user in users:
                recipient_info.append({
                    'username': user.username,
                    'email': user.email,
                    'id': user.id
                })

            self.logger.debug(f"Recipient details: {json.dumps(recipient_info, indent=2)}")

            # Send email
            sender_info = f"{self.sender.username} ({self.sender.email})"
            email_service = EmailServiceFactory.create_email_service()
            success, message = email_service.send_email(users, subject, content, sender_info)

            if success:
                self.logger.info(f"✅ Email command completed successfully: {message}")
                self.logger.info(
                    f"Command execution summary: Template='{template.name}', Recipients={users.count()}, Sender={sender_info}")
            else:
                self.logger.error(f"❌ Email command failed: {message}")

            return success, message

        except EmailTemplate.DoesNotExist:
            error_msg = f"Email template with ID {self.template_id} not found"
            self.logger.error(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Error executing email command: {str(e)}"
            self.logger.error(f"❌ {error_msg}")
            self.logger.exception("Full exception details:")
            return False, error_msg


class EmailManager:
    def __init__(self):
        self.commands = []
        self.logger = logging.getLogger('email_manager')

    def add_command(self, command: Command):
        self.commands.append(command)
        self.logger.info(f"Command added to email manager. Total commands: {len(self.commands)}")

    def execute_commands(self):
        self.logger.info(f"🎯 Executing {len(self.commands)} email commands")
        results = []

        for i, command in enumerate(self.commands, 1):
            self.logger.info(f"Executing command {i}/{len(self.commands)}")
            result = command.execute()
            results.append(result)

            if result[0]:
                self.logger.info(f"✅ Command {i} completed successfully")
            else:
                self.logger.error(f"❌ Command {i} failed: {result[1]}")

        self.logger.info(
            f"📊 Email manager execution complete. Success: {sum(1 for r in results if r[0])}, Failed: {sum(1 for r in results if not r[0])}")
        self.commands.clear()
        return results