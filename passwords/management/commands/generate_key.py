from django.core.management.base import BaseCommand
from cryptography.fernet import Fernet
import os


class Command(BaseCommand):
    help = 'Generate encryption key for password manager'

    def handle(self, *args, **options):
        key = Fernet.generate_key()

        # Save key to environment file
        with open('.env', 'w') as f:
            f.write(f'ENCRYPTION_KEY={key.decode()}\n')

        self.stdout.write(
            self.style.SUCCESS(f'Encryption key generated and saved to .env file')
        )
        self.stdout.write(
            self.style.WARNING('Important: Keep this key secure and backup it safely!')
        )
        self.stdout.write(
            self.style.WARNING('If you lose this key, you will not be able to decrypt existing passwords!')
        )