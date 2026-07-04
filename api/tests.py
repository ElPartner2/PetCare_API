from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class JWTAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            email='admin@example.com',
            password='securepass123',
            phone='123456789',
        )

    def test_login_with_email_and_password_returns_tokens(self):
        client = APIClient()
        response = client.post(
            '/api/token/',
            {'username': 'admin', 'password': 'securepass123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
