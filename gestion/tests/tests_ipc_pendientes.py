from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from gestion.models import CalculoIPC, Contrato, IPCHistorico, Local, Tercero
from gestion.utils_ipc import (
    obtener_contratos_pendientes_ajuste_ipc,
    requiere_revision_configuracion_ajuste,
)


class ContratosPendientesIPCTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ipc-pendientes', password='testpass123'
        )
        self.client.force_login(self.user)
        self.local = Local.objects.create(
            nombre_comercial_stand='Local IPC',
            total_area_m2=100,
        )
        self.ipc = IPCHistorico.objects.create(
            año=2025,
            valor_ipc=Decimal('9.28'),
        )

    def crear_contrato(self, numero, fecha_aumento, tipo_condicion_ipc='IPC'):
        tercero = Tercero.objects.create(
            nit=f'902{numero}',
            razon_social=f'Cliente IPC {numero}',
            tipo='ARRENDATARIO',
            nombre_rep_legal='Representante',
        )
        return Contrato.objects.create(
            num_contrato=f'IPC-{numero}',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2025, 1, 1),
            fecha_inicial_contrato=fecha_aumento,
            fecha_final_inicial=date(2028, 12, 31),
            modalidad_pago='Fijo',
            tipo_condicion_ipc=tipo_condicion_ipc,
            periodicidad_ipc='ANUAL',
            fecha_aumento_ipc=fecha_aumento,
            puntos_adicionales_ipc=Decimal('0.00'),
            arrendatario=tercero,
            local=self.local,
        )

    def test_incluye_contratos_vencidos_sin_calculo_aplicado(self):
        contrato = self.crear_contrato(1, date(2025, 1, 1))

        pendientes = obtener_contratos_pendientes_ajuste_ipc(date(2026, 4, 26))

        self.assertIn(contrato, pendientes)

    def test_marca_revision_si_hay_calculo_aplicado_con_configuracion_incompleta(self):
        contrato = self.crear_contrato(4, date(2025, 1, 1), tipo_condicion_ipc=None)
        calculo = CalculoIPC.objects.create(
            contrato=contrato,
            año_aplicacion=2026,
            fecha_aplicacion=date(2026, 1, 1),
            ipc_historico=self.ipc,
            canon_anterior=Decimal('1000000'),
            puntos_adicionales=Decimal('0.00'),
            porcentaje_total_aplicar=Decimal('9.28'),
            valor_incremento=Decimal('92800'),
            nuevo_canon=Decimal('1092800'),
            estado='APLICADO',
        )

        requiere_revision = requiere_revision_configuracion_ajuste(
            calculo,
            tipo_condicion_ipc=contrato.tipo_condicion_ipc,
            periodicidad_ipc=contrato.periodicidad_ipc,
            fecha_aumento_ipc=contrato.fecha_aumento_ipc,
        )

        self.assertTrue(requiere_revision)

    def test_lista_principal_muestra_badge_revision_para_configuracion_incompleta(self):
        contrato = self.crear_contrato(5, date(2025, 1, 1), tipo_condicion_ipc=None)
        CalculoIPC.objects.create(
            contrato=contrato,
            año_aplicacion=2026,
            fecha_aplicacion=date(2026, 1, 1),
            ipc_historico=self.ipc,
            canon_anterior=Decimal('1000000'),
            puntos_adicionales=Decimal('0.00'),
            porcentaje_total_aplicar=Decimal('9.28'),
            valor_incremento=Decimal('92800'),
            nuevo_canon=Decimal('1092800'),
            estado='APLICADO',
        )

        response = self.client.get(
            reverse('gestion:lista_ipc_historico'),
            {'estado_filtro': 'APLICADO', 'mostrar_al_dia': '1'},
        )

        self.assertContains(response, contrato.num_contrato)
        self.assertContains(response, 'Revisar contrato / Otro Si')

    def test_excluye_contratos_con_calculo_aplicado_en_el_anio_actual(self):
        contrato = self.crear_contrato(2, date(2025, 1, 1))
        CalculoIPC.objects.create(
            contrato=contrato,
            año_aplicacion=2026,
            fecha_aplicacion=date(2026, 1, 1),
            ipc_historico=self.ipc,
            canon_anterior=Decimal('1000000'),
            puntos_adicionales=Decimal('0.00'),
            porcentaje_total_aplicar=Decimal('9.28'),
            valor_incremento=Decimal('92800'),
            nuevo_canon=Decimal('1092800'),
            periodicidad_contrato='ANUAL',
            fecha_aumento_contrato=date(2025, 1, 1),
            estado='APLICADO',
        )

        pendientes = obtener_contratos_pendientes_ajuste_ipc(date(2026, 4, 26))

        self.assertNotIn(contrato, pendientes)

    def test_usa_el_mismo_alcance_de_contratos_activos_de_la_lista_principal(self):
        contrato = self.crear_contrato(3, date(2025, 1, 1), tipo_condicion_ipc=None)

        pendientes = obtener_contratos_pendientes_ajuste_ipc(date(2026, 4, 26))

        self.assertIn(contrato, pendientes)
