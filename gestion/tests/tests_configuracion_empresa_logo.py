import base64
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from gestion.models import ConfiguracionEmpresa

# PNG transparente de 1x1 pixel, válido para Pillow/ImageField
PNG_1PX = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ConfiguracionEmpresaLogoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_guarda_logo_en_configuracion_empresa(self):
        logo_file = SimpleUploadedFile('logo.png', PNG_1PX, content_type='image/png')
        config = ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa Test',
            nit_empresa='900123456-1',
            representante_legal='Juana Ejemplo',
            logo=logo_file,
        )
        config.refresh_from_db()
        self.assertTrue(config.logo.name.startswith('empresa/logos/logo'))

    def test_logo_es_opcional(self):
        config = ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa Sin Logo',
            nit_empresa='900123456-2',
            representante_legal='Juana Ejemplo',
        )
        self.assertFalse(config.logo)
