import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class DashboardLivianoTest(TestCase):
    """El dashboard solo hace 2 queries COUNT — no ejecuta cálculos de alertas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client.force_login(self.user)

    def test_dashboard_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_carga_correctamente(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_solo_tiene_conteos_basicos(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertIn('total_contratos', response.context)
        self.assertIn('total_polizas', response.context)
        # NO debe tener alertas en el contexto — esas vienen por AJAX
        self.assertNotIn('contratos_por_vencer', response.context)
        self.assertNotIn('alertas_ipc', response.context)
        self.assertNotIn('polizas_criticas', response.context)

    def test_dashboard_usa_template_correcto(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertTemplateUsed(response, 'gestion/dashboard/index.html')


class CentroAlertasTest(TestCase):
    """La vista centro_alertas renderiza el contenedor sin calcular alertas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser2', password='testpass123'
        )
        self.client.force_login(self.user)

    def test_centro_alertas_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:centro_alertas'))
        self.assertNotEqual(response.status_code, 200)

    def test_centro_alertas_carga_correctamente(self):
        response = self.client.get(reverse('gestion:centro_alertas'))
        self.assertEqual(response.status_code, 200)

    def test_centro_alertas_usa_template_correcto(self):
        response = self.client.get(reverse('gestion:centro_alertas'))
        self.assertTemplateUsed(response, 'gestion/alertas/index.html')

    def test_centro_alertas_acepta_tipo_filtro(self):
        response = self.client.get(
            reverse('gestion:centro_alertas') + '?tipo_alerta=CLIENTE'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['tipo_filtro'], 'CLIENTE')


class ApiConteosAlertasTest(TestCase):
    """El endpoint AJAX devuelve JSON con conteos y estadísticas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser3', password='testpass123'
        )
        self.client.force_login(self.user)

    def test_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:api_conteos_alertas'))
        self.assertEqual(response.status_code, 403)

    def test_devuelve_json(self):
        response = self.client.get(reverse('gestion:api_conteos_alertas'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_estructura_json_correcta(self):
        response = self.client.get(reverse('gestion:api_conteos_alertas'))
        data = json.loads(response.content)
        self.assertIn('contratos_vigentes', data)
        self.assertIn('contratos_vencidos', data)
        self.assertIn('total_polizas', data)
        self.assertIn('contratos_fijos', data)
        self.assertIn('contratos_variables', data)
        self.assertIn('contratos_hibridos', data)
        self.assertIn('alertas', data)
        alertas = data['alertas']
        for key in ['vencimiento', 'polizas_criticas', 'preaviso', 'ipc',
                    'salario_minimo', 'polizas_requeridas', 'terminacion',
                    'renovacion_automatica']:
            self.assertIn(key, alertas)
            self.assertIsInstance(alertas[key], int)


class ApiDetalleAlertasTest(TestCase):
    """El endpoint AJAX devuelve HTML pre-renderizado con todas las alertas."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser4', password='testpass123'
        )
        self.client.force_login(self.user)

    def test_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse('gestion:api_detalle_alertas'))
        self.assertEqual(response.status_code, 403)

    def test_devuelve_json(self):
        response = self.client.get(reverse('gestion:api_detalle_alertas'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_estructura_json_correcta(self):
        response = self.client.get(reverse('gestion:api_detalle_alertas'))
        data = json.loads(response.content)
        self.assertIn('html', data)
        self.assertIn('totales', data)
        self.assertIsInstance(data['html'], str)
        self.assertGreater(len(data['html']), 0)

    def test_acepta_filtro_tipo_alerta(self):
        response = self.client.get(
            reverse('gestion:api_detalle_alertas') + '?tipo_alerta=CLIENTE'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('html', data)
