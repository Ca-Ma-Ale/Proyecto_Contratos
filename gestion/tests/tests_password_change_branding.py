from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class PasswordChangeFormBrandingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pwuser', password='testpass123')
        self.client.force_login(self.user)

    def test_password_change_form_muestra_logo_por_defecto_sin_configuracion(self):
        response = self.client.get(reverse('password_change'))
        self.assertContains(response, 'logo-chip')
        self.assertContains(response, 'avenida-chile-icono.svg')


class PasswordChangeDoneBrandingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pwuser2', password='testpass123')
        self.client.force_login(self.user)

    def test_password_change_done_muestra_logo_por_defecto_sin_configuracion(self):
        response = self.client.get(reverse('password_change_done'))
        self.assertContains(response, 'logo-chip')
        self.assertContains(response, 'avenida-chile-icono.svg')
