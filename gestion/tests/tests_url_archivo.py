"""Regresion CN-009: url_archivo no debe aceptar esquemas ejecutables (javascript:, data:, vbscript:)."""
from django.test import SimpleTestCase

from gestion.forms import URLFlexibleField


class URLFlexibleFieldTest(SimpleTestCase):

    def test_acepta_urls_de_intranet_y_alfresco(self):
        campo = URLFlexibleField()
        for url in [
            'https://ejemplo.com/doc.pdf',
            'http://documentos:8080/share/page/site/rm/document-details?nodeRef=workspace://SpacesStore/59f05cb3',
            'workspace://SpacesStore/59f05cb3-ec05-47b3-b3d3-ab7500d4df13',
            'file://servidor/carpeta/contrato.pdf',
            'documentos:8080/share#seccion',
            '',
        ]:
            self.assertEqual(campo.clean(url), url, url)

    def test_rechaza_esquemas_ejecutables(self):
        campo = URLFlexibleField()
        for url in [
            'javascript:alert(document.cookie)',
            'JavaScript:alert(1)',
            '  javascript:alert(1)',
            'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',
            'vbscript:msgbox(1)',
        ]:
            with self.assertRaises(Exception, msg=url):
                campo.clean(url)
