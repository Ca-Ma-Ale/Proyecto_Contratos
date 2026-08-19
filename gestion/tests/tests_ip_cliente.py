"""CN-011: IP real del cliente detras de Caddy (axes y auditoria)."""
from django.conf import settings
from django.test import RequestFactory, SimpleTestCase

from gestion.utils_red import obtener_ip_cliente


class ObtenerIpClienteTest(SimpleTestCase):

    def setUp(self):
        self.rf = RequestFactory()

    def test_sin_proxy_usa_remote_addr(self):
        r = self.rf.get('/', REMOTE_ADDR='10.0.0.5')
        self.assertEqual(obtener_ip_cliente(r), '10.0.0.5')

    def test_con_proxy_toma_la_ultima_ip_de_x_forwarded_for(self):
        # El cliente intenta falsear con "1.1.1.1"; Caddy anade la real al final
        r = self.rf.get('/', REMOTE_ADDR='172.18.0.3', HTTP_X_FORWARDED_FOR='1.1.1.1, 190.24.10.7')
        self.assertEqual(obtener_ip_cliente(r), '190.24.10.7')

    def test_axes_usa_el_helper(self):
        self.assertEqual(settings.AXES_CLIENT_IP_CALLABLE, 'gestion.utils_red.obtener_ip_cliente')
