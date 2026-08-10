import base64
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from gestion.models import ConfiguracionEmpresa

PNG_1PX = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


class NavbarBrandingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='navuser', password='testpass123')
        self.client.force_login(self.user)

    def test_navbar_muestra_logo_chip(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertContains(response, 'navbar-logo-chip')
        self.assertContains(response, 'avenida-chile-icono.svg')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class NavbarBrandingConLogoPersonalizadoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='navuser2', password='testpass123')
        self.client.force_login(self.user)

    def test_navbar_usa_logo_subido_cuando_existe(self):
        logo_file = SimpleUploadedFile('logo.png', PNG_1PX, content_type='image/png')
        ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa Con Logo',
            nit_empresa='900123456-3',
            representante_legal='Juana Ejemplo',
            activo=True,
            logo=logo_file,
        )
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertContains(response, 'empresa/logos/logo')
