from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gestion.models import Contrato, Local, OtroSi, RenovacionAutomatica, Tercero


class ListaContratosPerformanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='listado', password='testpass123'
        )
        self.client.force_login(self.user)
        self.local = Local.objects.create(
            nombre_comercial_stand='Local 1',
            total_area_m2=100,
        )

    def crear_contrato(self, numero, fecha_final):
        tercero = Tercero.objects.create(
            nit=f'900{numero}',
            razon_social=f'Tercero {numero}',
            tipo='ARRENDATARIO',
            nombre_rep_legal='Representante',
        )
        return Contrato.objects.create(
            num_contrato=f'C-{numero}',
            objeto_destinacion='Objeto',
            nit_concedente='800',
            rep_legal_concedente='Legal',
            fecha_firma=date(2025, 1, 1),
            fecha_inicial_contrato=date(2025, 1, 1),
            fecha_final_inicial=fecha_final,
            modalidad_pago='Fijo',
            arrendatario=tercero,
            local=self.local,
        )

    def agregar_eventos(self, contrato, numero):
        fecha_aprobacion = timezone.make_aware(
            timezone.datetime(2025, 1, numero, 9, 0)
        )
        OtroSi.objects.create(
            contrato=contrato,
            numero_otrosi=f'OS-{numero}',
            estado='APROBADO',
            fecha_otrosi=date(2025, 1, numero),
            effective_from=date(2025, 1, numero),
            nueva_fecha_final_actualizada=date(2027, 12, 31),
            descripcion='Extension',
            fecha_aprobacion=fecha_aprobacion,
        )
        RenovacionAutomatica.objects.create(
            contrato=contrato,
            numero_renovacion=f'RA-{numero}',
            estado='APROBADO',
            fecha_renovacion=date(2025, 2, numero),
            effective_from=date(2025, 2, numero),
            fecha_inicio_nueva_vigencia=date(2026, 1, 1),
            nueva_fecha_final_actualizada=date(2028, 12, 31),
            meses_renovacion=12,
            fecha_final_anterior=date(2026, 12, 31),
            fecha_aprobacion=fecha_aprobacion,
        )

    def test_lista_contratos_prefetches_events_without_query_per_contract(self):
        for numero in range(1, 6):
            contrato = self.crear_contrato(numero, date(2026, 12, 31))
            self.agregar_eventos(contrato, numero)

        with self.assertNumQueries(15):
            response = self.client.get(reverse('gestion:lista_contratos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'C-1')
        self.assertContains(response, 'C-5')
        self.assertContains(response, 'OS-5')
