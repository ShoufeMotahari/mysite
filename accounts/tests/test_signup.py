from django.test import TestCase
from users.models import User, RegisterToken
from accounts.factories.user_factory import UserFactory

class SignupTest(TestCase):
    def test_user_created_with_token(self):
        user = UserFactory.create_user_with_token("09123456789")
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.registertoken)