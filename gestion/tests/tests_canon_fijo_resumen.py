"""
Regresion: contratos CLIENTE con modalidad "Fijo" no mostraban valores
economicos en el resumen del contrato ni en la exportacion.

El formulario de contrato solo captura `canon_minimo_garantizado` (el campo
`valor_canon_fijo` nunca se diligencia), pero varias lecturas asumian que un
contrato CLIENTE guarda su canon en `valor_canon_fijo`.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from openpyxl import load_workbook

from gestion.models import Contrato, Local, Tercero
from gestion.views.utils import obtener_canon_vigente, obtener_canon_vigente_con_fuente


@override_settings(
    ALLOWED_HOSTS=['*'],
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class CanonFijoClienteTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='canon', password='testpass123')
        self.client.force_login(self.user)
        self.local = Local.objects.create(nombre_comercial_stand='Local 1', total_area_m2=100)
        tercero = Tercero.objects.create(
            nit='900111222-3', razon_social='Estacionamiento Prueba',
            tipo='ARRENDATARIO', nombre_rep_legal='Representante',
        )
        # Reproduce el contrato 2025-107: CLIENTE, Fijo, sin otrosi ni IPC,
        # valor_canon_fijo vacio y el canon en canon_minimo_garantizado.
        self.contrato = Contrato.objects.create(
            num_contrato='2025-107-PRUEBA',
            tipo_contrato_cliente_proveedor='CLIENTE',
            objeto_destinacion='Concesion cupos de estacionamiento',
            nit_concedente='800', rep_legal_concedente='Legal',
            fecha_firma=date(2025, 10, 15),
            fecha_inicial_contrato=date(2025, 11, 15),
            fecha_final_inicial=date(2026, 11, 14),
            fecha_final_actualizada=date(2026, 11, 14),
            duracion_inicial_meses=12,
            modalidad_pago='Fijo',
            valor_canon_fijo=None,
            canon_minimo_garantizado=Decimal('442017.00'),
            arrendatario=tercero, local=self.local, vigente=True,
        )

    def test_canon_vigente_cae_a_canon_minimo_cuando_no_hay_canon_fijo(self):
        self.assertEqual(obtener_canon_vigente(self.contrato, date(2026, 6, 1)), Decimal('442017.00'))
        info = obtener_canon_vigente_con_fuente(self.contrato, date(2026, 6, 1))
        self.assertEqual(info['tipo'], 'contrato')

    def test_detalle_muestra_canon_fijo(self):
        # Django 5.0 + Python 3.14: copy(Context) falla dentro del cliente de
        # pruebas al capturar plantillas; no afecta la vista real.
        with patch('django.test.client.copy', lambda ctx: ctx):
            response = self.client.get(f'/contratos/{self.contrato.pk}/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        inicio = html.index('Valores Econ')
        seccion = html[inicio:inicio + 6000]
        self.assertIn('Canon Fijo', seccion)
        self.assertIn('442017', seccion)

    def test_exportacion_incluye_canon_vigente_y_base(self):
        response = self.client.post('/exportaciones/contratos/', {'estado': '', 'tipo_contrato_cliente_proveedor': ''})
        self.assertEqual(response.status_code, 200, getattr(response, 'url', ''))
        wb = load_workbook(BytesIO(response.content))
        hoja = wb['Clientes']
        encabezados = [c.value for c in hoja[1]]
        fila = [c.value for c in hoja[2]]
        datos = dict(zip(encabezados, fila))
        self.assertEqual(datos['Número Contrato'], '2025-107-PRUEBA')
        self.assertEqual(datos['Canon Vigente'], 442017.0)
        self.assertEqual(datos['Canon Base'], 442017.0)
