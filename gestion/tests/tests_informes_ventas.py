from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gestion.forms import CalculoFacturacionVentasForm
from gestion.models import CalculoIPC, Contrato, IPCHistorico, Local, OtroSi, RenovacionAutomatica, Tercero
from gestion.utils_otrosi import obtener_valores_vigentes_facturacion_ventas
from gestion.utils_ventas import contratos_con_configuracion_ventas_queryset


class ListaInformesVentasPerformanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='informes', password='testpass123'
        )
        self.client.force_login(self.user)
        self.local = Local.objects.create(
            nombre_comercial_stand='Local Ventas',
            total_area_m2=100,
        )

    def crear_contrato(self, numero):
        tercero = Tercero.objects.create(
            nit=f'901{numero}',
            razon_social=f'Cliente Ventas {numero}',
            tipo='ARRENDATARIO',
            nombre_rep_legal='Representante',
        )
        return Contrato.objects.create(
            num_contrato=f'V-{numero}',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2025, 1, 1),
            fecha_inicial_contrato=date(2025, 1, 1),
            fecha_final_inicial=date(2028, 12, 31),
            modalidad_pago='Variable Puro',
            porcentaje_ventas=5,
            reporta_ventas=True,
            arrendatario=tercero,
            local=self.local,
        )

    def agregar_eventos(self, contrato, numero):
        fecha_aprobacion = timezone.make_aware(
            timezone.datetime(2025, 1, numero, 9, 0)
        )
        OtroSi.objects.create(
            contrato=contrato,
            numero_otrosi=f'OSV-{numero}',
            estado='APROBADO',
            fecha_otrosi=date(2025, 1, numero),
            effective_from=date(2025, 1, numero),
            nueva_modalidad_pago='Variable Puro',
            nuevo_porcentaje_ventas=6,
            nueva_fecha_final_actualizada=date(2028, 12, 31),
            descripcion='Ventas',
            fecha_aprobacion=fecha_aprobacion,
        )
        RenovacionAutomatica.objects.create(
            contrato=contrato,
            numero_renovacion=f'RAV-{numero}',
            estado='APROBADO',
            fecha_renovacion=date(2025, 2, numero),
            effective_from=date(2025, 2, numero),
            fecha_inicio_nueva_vigencia=date(2026, 1, 1),
            nueva_fecha_final_actualizada=date(2029, 12, 31),
            meses_renovacion=12,
            fecha_final_anterior=date(2028, 12, 31),
            fecha_aprobacion=fecha_aprobacion,
        )

    def test_lista_informes_ventas_prefetches_events_without_query_per_contract(self):
        for numero in range(1, 6):
            contrato = self.crear_contrato(numero)
            self.agregar_eventos(contrato, numero)

        # 14 originales + 2 prefetch (calculos_ipc, calculos_salario_minimo) que
        # usa obtener_canon_vigente_con_fuente; el total no depende del numero
        # de contratos.
        with self.assertNumQueries(16):
            response = self.client.get(reverse('gestion:lista_informes_ventas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'V-1')
        self.assertContains(response, 'V-5')
        self.assertContains(response, 'OSV-5')


class ContratosVentasPorOtrosiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ventas-otrosi', password='testpass123'
        )
        self.client.force_login(self.user)
        self.local = Local.objects.create(
            nombre_comercial_stand='Local Pops',
            total_area_m2=80,
        )
        self.arrendatario = Tercero.objects.create(
            nit='900999',
            razon_social='Popsy',
            tipo='ARRENDATARIO',
            nombre_rep_legal='Representante',
        )
        self.contrato = Contrato.objects.create(
            num_contrato='POPSY-CTO-01',
            tipo_contrato_cliente_proveedor='CLIENTE',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2014, 1, 23),
            fecha_inicial_contrato=date(2014, 1, 23),
            fecha_final_inicial=date(2030, 1, 22),
            modalidad_pago='Hibrido (Min Garantizado)',
            porcentaje_ventas=None,
            canon_minimo_garantizado=Decimal('10000000'),
            reporta_ventas=False,
            arrendatario=self.arrendatario,
            local=self.local,
        )
        OtroSi.objects.create(
            contrato=self.contrato,
            numero_otrosi='OS-8',
            estado='APROBADO',
            fecha_otrosi=date(2023, 1, 5),
            effective_from=date(2023, 1, 1),
            nueva_modalidad_pago='Hibrido (Min Garantizado)',
            nuevo_porcentaje_ventas=Decimal('12'),
            nuevo_canon_minimo_garantizado=Decimal('5000000'),
            descripcion='Ventas por otrosi',
            fecha_aprobacion=timezone.make_aware(timezone.datetime(2023, 1, 5, 9, 0)),
        )

    def test_consulta_incluye_contrato_que_reporta_ventas_por_otrosi(self):
        contratos = contratos_con_configuracion_ventas_queryset()

        self.assertIn(self.contrato, contratos)

    def test_formulario_calculo_permite_contrato_que_reporta_ventas_por_otrosi(self):
        form = CalculoFacturacionVentasForm(data={
            'contrato': self.contrato.id,
            'mes': '7',
            'año': 2026,
            'ventas_totales': '100000000',
            'devoluciones': '0',
            'observaciones': '',
        })

        self.assertTrue(form.is_valid(), form.errors)


class ObtenerValoresVigentesFacturacionVentasIPCTest(TestCase):
    """El cálculo de % de ventas debe usar el canon mínimo garantizado ya
    ajustado por IPC, no el valor original del contrato/Otro Sí."""

    def setUp(self):
        self.local = Local.objects.create(
            nombre_comercial_stand='Local Hibrido',
            total_area_m2=80,
        )
        self.proveedor = Tercero.objects.create(
            nit='9001',
            razon_social='Proveedor Hibrido',
            tipo='PROVEEDOR',
            nombre_rep_legal='Representante',
        )
        self.contrato = Contrato.objects.create(
            num_contrato='H-1',
            tipo_contrato_cliente_proveedor='PROVEEDOR',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2024, 1, 1),
            fecha_inicial_contrato=date(2024, 1, 1),
            fecha_final_inicial=date(2030, 12, 31),
            modalidad_pago='Hibrido (Min Garantizado)',
            porcentaje_ventas=5,
            canon_minimo_garantizado=Decimal('1000000'),
            reporta_ventas=True,
            proveedor=self.proveedor,
            local=self.local,
        )
        self.ipc_historico = IPCHistorico.objects.create(
            año=2025,
            valor_ipc=Decimal('5.00'),
        )
        CalculoIPC.objects.create(
            contrato=self.contrato,
            año_aplicacion=2025,
            fecha_aplicacion=date(2025, 1, 1),
            ipc_historico=self.ipc_historico,
            canon_anterior=Decimal('1000000'),
            porcentaje_total_aplicar=Decimal('5.00'),
            valor_incremento=Decimal('50000'),
            nuevo_canon=Decimal('1050000'),
            estado='APLICADO',
        )

    def test_canon_minimo_garantizado_refleja_ajuste_ipc_vigente(self):
        valores = obtener_valores_vigentes_facturacion_ventas(self.contrato, 6, 2025)

        self.assertIsNotNone(valores)
        self.assertEqual(valores['canon_minimo_garantizado'], Decimal('1050000'))

    def test_canon_minimo_garantizado_sin_ipc_usa_valor_contrato(self):
        valores = obtener_valores_vigentes_facturacion_ventas(self.contrato, 6, 2024)

        self.assertIsNotNone(valores)
        self.assertEqual(valores['canon_minimo_garantizado'], Decimal('1000000'))


class CalculoFacturacionVentasFormUrlArchivoTest(TestCase):
    """El formulario de cálculo de % de ventas debe aceptar y guardar la URL
    del archivo digital de soporte, igual que el formulario de informe de ventas."""

    def setUp(self):
        self.local = Local.objects.create(
            nombre_comercial_stand='Local Ventas Form',
            total_area_m2=60,
        )
        self.tercero = Tercero.objects.create(
            nit='9101',
            razon_social='Cliente Form',
            tipo='ARRENDATARIO',
            nombre_rep_legal='Representante',
        )
        self.contrato = Contrato.objects.create(
            num_contrato='F-1',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2025, 1, 1),
            fecha_inicial_contrato=date(2025, 1, 1),
            fecha_final_inicial=date(2028, 12, 31),
            modalidad_pago='Variable Puro',
            porcentaje_ventas=5,
            reporta_ventas=True,
            arrendatario=self.tercero,
            local=self.local,
        )

    def test_form_acepta_y_limpia_url_archivo(self):
        form = CalculoFacturacionVentasForm(data={
            'contrato': self.contrato.id,
            'mes': '6',
            'año': 2025,
            'ventas_totales': '1.000.000',
            'devoluciones': '0',
            'observaciones': '',
            'url_archivo': '  https://onedrive.com/soporte-ventas  ',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['url_archivo'], 'https://onedrive.com/soporte-ventas')

    def test_form_url_archivo_es_opcional(self):
        form = CalculoFacturacionVentasForm(data={
            'contrato': self.contrato.id,
            'mes': '6',
            'año': 2025,
            'ventas_totales': '1.000.000',
            'devoluciones': '0',
            'observaciones': '',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data.get('url_archivo'))


class ObtenerValoresVigentesFacturacionVentasCanonVigenteTest(TestCase):
    """Caso real: contrato CLIENTE/arrendatario con modalidad Híbrido cuyo
    Canon Mínimo Garantizado lo fijó un Otro Sí, y luego se aplicó un cálculo
    de IPC posterior. El % de ventas debe coincidir con el "Canon Vigente"
    que ya muestran los informes/dashboard (obtener_canon_vigente), que
    prioriza por fecha de aplicación sobre el Otro Sí."""

    def setUp(self):
        self.local = Local.objects.create(
            nombre_comercial_stand='Local Hall Gastro',
            total_area_m2=50,
        )
        self.arrendatario = Tercero.objects.create(
            nit='9201',
            razon_social='Arrendatario Hibrido',
            tipo='ARRENDATARIO',
            nombre_rep_legal='Representante',
        )
        self.contrato = Contrato.objects.create(
            num_contrato='H-2',
            tipo_contrato_cliente_proveedor='CLIENTE',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2008, 1, 1),
            fecha_inicial_contrato=date(2008, 1, 1),
            fecha_final_inicial=date(2030, 12, 31),
            modalidad_pago='Hibrido (Min Garantizado)',
            porcentaje_ventas=8,
            canon_minimo_garantizado=Decimal('10000000'),
            reporta_ventas=True,
            arrendatario=self.arrendatario,
            local=self.local,
        )
        OtroSi.objects.create(
            contrato=self.contrato,
            numero_otrosi='OS-2',
            estado='APROBADO',
            fecha_otrosi=date(2021, 1, 1),
            effective_from=date(2021, 1, 1),
            nuevo_canon_minimo_garantizado=Decimal('8579032'),
            descripcion='Ajuste canon mínimo',
            fecha_aprobacion=timezone.make_aware(timezone.datetime(2021, 1, 1, 9, 0)),
        )
        self.ipc_historico = IPCHistorico.objects.create(
            año=2025,
            valor_ipc=Decimal('5.10'),
        )
        CalculoIPC.objects.create(
            contrato=self.contrato,
            año_aplicacion=2026,
            fecha_aplicacion=date(2026, 1, 1),
            ipc_historico=self.ipc_historico,
            canon_anterior=Decimal('15232287'),
            canon_anterior_manual=True,
            porcentaje_total_aplicar=Decimal('5.10'),
            valor_incremento=Decimal('776846.64'),
            nuevo_canon=Decimal('16009133.64'),
            estado='APLICADO',
        )

    def test_canon_minimo_garantizado_usa_el_canon_vigente_oficial(self):
        valores = obtener_valores_vigentes_facturacion_ventas(self.contrato, 5, 2026)

        self.assertIsNotNone(valores)
        self.assertEqual(valores['canon_minimo_garantizado'], Decimal('16009133.64'))
        self.assertIn('IPC', valores['fuente_canon_minimo_garantizado'])
        self.assertIn('01/01/2026', valores['fuente_canon_minimo_garantizado'])

    def test_canon_minimo_garantizado_antes_del_ipc_usa_el_otrosi(self):
        valores = obtener_valores_vigentes_facturacion_ventas(self.contrato, 6, 2022)

        self.assertIsNotNone(valores)
        self.assertEqual(valores['canon_minimo_garantizado'], Decimal('8579032'))
        self.assertIn('OS-2', valores['fuente_canon_minimo_garantizado'])


class EliminarInformeVentasCascadaTest(TestCase):
    """Al eliminar un Informe de Ventas, los Cálculos de Facturación
    asociados (confirmados o no) deben eliminarse también."""

    def setUp(self):
        self.local = Local.objects.create(
            nombre_comercial_stand='Local Cascada',
            total_area_m2=40,
        )
        self.tercero = Tercero.objects.create(
            nit='9301',
            razon_social='Cliente Cascada',
            tipo='ARRENDATARIO',
            nombre_rep_legal='Representante',
        )
        self.contrato = Contrato.objects.create(
            num_contrato='C-1',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2025, 1, 1),
            fecha_inicial_contrato=date(2025, 1, 1),
            fecha_final_inicial=date(2028, 12, 31),
            modalidad_pago='Variable Puro',
            porcentaje_ventas=5,
            reporta_ventas=True,
            arrendatario=self.tercero,
            local=self.local,
        )

    def test_eliminar_informe_borra_calculo_confirmado_asociado(self):
        from gestion.models import CalculoFacturacionVentas, InformeVentas

        informe = InformeVentas.objects.create(contrato=self.contrato, mes=6, año=2025)
        calculo = CalculoFacturacionVentas.objects.create(
            contrato=self.contrato,
            informe_ventas=informe,
            mes=6,
            año=2025,
            ventas_totales=Decimal('1000000'),
            devoluciones=Decimal('0'),
            base_neta=Decimal('1000000'),
            modalidad_contrato='VARIABLE_PURO',
            porcentaje_ventas_vigente=Decimal('5'),
            valor_calculado_porcentaje=Decimal('50000'),
            valor_a_facturar_variable=Decimal('50000'),
            aplica_variable=True,
            confirmado=True,
        )
        calculo_id = calculo.id

        informe.delete()

        self.assertFalse(CalculoFacturacionVentas.objects.filter(id=calculo_id).exists())
