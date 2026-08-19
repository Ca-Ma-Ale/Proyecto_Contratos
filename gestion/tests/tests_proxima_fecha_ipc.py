"""
Regresion: la proxima fecha de ajuste IPC/SMLV se corria un anio cuando
fecha_aumento_ipc era la fecha exacta del primer ajuste (posterior al inicio
del contrato). La regla del "primer ciclo" solo aplica cuando fecha_aumento_ipc
no es posterior a fecha_inicial_contrato.
"""
from datetime import date

from django.test import TestCase

from gestion.models import Contrato, Local, Tercero
from gestion.utils_ipc import calcular_proxima_fecha_aumento


class ProximaFechaAumentoSinCalculosTest(TestCase):

    def setUp(self):
        self.local = Local.objects.create(nombre_comercial_stand='Local IPC', total_area_m2=100)
        self.tercero = Tercero.objects.create(
            nit='903000001', razon_social='Cliente IPC',
            tipo='ARRENDATARIO', nombre_rep_legal='Representante',
        )

    def crear(self, inicio, aumento, periodicidad):
        return Contrato.objects.create(
            num_contrato=f'IPC-{inicio}-{aumento}',
            objeto_destinacion='Objeto', nit_concedente='800', rep_legal_concedente='Legal',
            fecha_firma=inicio, fecha_inicial_contrato=inicio,
            fecha_final_inicial=date(inicio.year + 5, inicio.month, inicio.day),
            modalidad_pago='Fijo', tipo_condicion_ipc='IPC',
            periodicidad_ipc=periodicidad, fecha_aumento_ipc=aumento,
            arrendatario=self.tercero, local=self.local, vigente=True,
        )

    def test_fecha_especifica_posterior_al_inicio_es_el_primer_ajuste(self):
        # Caso 2025-107: inicia 2025-11-15, ajuste pactado 2026-01-01 -> ya vencido en 2026-08-18
        c = self.crear(date(2025, 11, 15), date(2026, 1, 1), 'FECHA_ESPECIFICA')
        self.assertEqual(calcular_proxima_fecha_aumento(c, date(2026, 8, 18)), date(2026, 1, 1))

    def test_fecha_especifica_un_anio_despues_del_inicio(self):
        # Inicia 2025-08-15, ajuste 2026-08-15 -> vencido hace 3 dias, no 2027
        c = self.crear(date(2025, 8, 15), date(2026, 8, 15), 'FECHA_ESPECIFICA')
        self.assertEqual(calcular_proxima_fecha_aumento(c, date(2026, 8, 18)), date(2026, 8, 15))

    def test_fecha_aumento_igual_al_inicio_espera_el_primer_ciclo(self):
        # Inicia 2026-03-20 con fecha_aumento = inicio -> primer IPC en 2027-03-20
        c = self.crear(date(2026, 3, 20), date(2026, 3, 20), 'ANUAL')
        self.assertEqual(calcular_proxima_fecha_aumento(c, date(2026, 8, 18)), date(2027, 3, 20))

    def test_fecha_aumento_anterior_al_inicio_usa_primera_ocurrencia_posterior(self):
        # Inicia 2026-03-01 con ajuste "cada 1 de enero" -> primer IPC 2027-01-01
        c = self.crear(date(2026, 3, 1), date(2026, 1, 1), 'FECHA_ESPECIFICA')
        self.assertEqual(calcular_proxima_fecha_aumento(c, date(2026, 8, 18)), date(2027, 1, 1))

    def test_primer_ciclo_no_se_reporta_vencido_antes_de_cumplirse(self):
        # Inicia 2025-06-01 = fecha_aumento; el 2026-05-01 el primer ajuste (2026-06-01) aun no llega
        c = self.crear(date(2025, 6, 1), date(2025, 6, 1), 'ANUAL')
        self.assertEqual(calcular_proxima_fecha_aumento(c, date(2026, 5, 1)), date(2026, 6, 1))

    def test_ocurrencia_mas_reciente_en_anios_posteriores(self):
        # Inicia 2023-06-15 = fecha_aumento; en 2026-08-18 la ocurrencia pendiente es 2026-06-15
        c = self.crear(date(2023, 6, 15), date(2023, 6, 15), 'ANUAL')
        self.assertEqual(calcular_proxima_fecha_aumento(c, date(2026, 8, 18)), date(2026, 6, 15))
