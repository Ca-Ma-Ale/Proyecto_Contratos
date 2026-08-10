import base64
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from gestion.models import ConfiguracionEmpresa

PNG_1PX = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


class LoginBrandingTest(TestCase):
    def test_login_muestra_logo_por_defecto_sin_configuracion(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'logo-chip')
        self.assertContains(response, 'avenida-chile-icono.svg')

    def test_login_muestra_figuras_decorativas_de_fondo(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'bg-shape')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class LoginBrandingConLogoPersonalizadoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_login_usa_logo_subido_cuando_existe(self):
        logo_file = SimpleUploadedFile('logo.png', PNG_1PX, content_type='image/png')
        ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa Con Logo',
            nit_empresa='900123456-3',
            representante_legal='Juana Ejemplo',
            activo=True,
            logo=logo_file,
        )
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'empresa/logos/logo')
