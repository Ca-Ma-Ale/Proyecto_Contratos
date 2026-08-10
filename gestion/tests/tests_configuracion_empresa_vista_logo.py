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


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ConfiguracionEmpresaVistaLogoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_config', password='testpass123', is_staff=True
        )
        self.client.force_login(self.user)

    def test_formulario_tiene_enctype_multipart(self):
        response = self.client.get(reverse('gestion:configuracion_empresa'))
        self.assertContains(response, 'multipart/form-data')

    def test_subir_logo_desde_panel_configuracion(self):
        logo_file = SimpleUploadedFile('logo.png', PNG_1PX, content_type='image/png')
        response = self.client.post(reverse('gestion:configuracion_empresa'), {
            'nombre_empresa': 'Empresa Test',
            'nit_empresa': '900123456-1',
            'representante_legal': 'Juana Ejemplo',
            'telefono': '',
            'email': '',
            'direccion': '',
            'activo': 'on',
            'logo': logo_file,
        })
        self.assertEqual(response.status_code, 302)
        config = ConfiguracionEmpresa.objects.filter(activo=True).first()
        self.assertIsNotNone(config)
        self.assertTrue(config.logo)
