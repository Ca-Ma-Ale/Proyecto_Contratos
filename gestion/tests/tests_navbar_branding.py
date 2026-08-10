from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class NavbarBrandingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='navuser', password='testpass123')
        self.client.force_login(self.user)

    def test_navbar_muestra_logo_chip(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertContains(response, 'navbar-logo-chip')
        self.assertContains(response, 'avenida-chile-icono.svg')
