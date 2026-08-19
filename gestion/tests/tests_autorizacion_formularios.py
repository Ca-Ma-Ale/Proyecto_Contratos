"""
Regresiones de autorizacion (Cyber Neo CN-006 / CN-007 / CN-008):
- un usuario no-staff no puede alterar datos generales/partes al editar un
  contrato aunque manipule el POST (antes solo habia `disabled` en HTML);
- ContratoForm no acepta campos de auditoria/estado por asignacion masiva;
- un usuario no-staff no puede crear/editar un Otro Si en estado APROBADO.
"""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from gestion.forms import ContratoForm
from gestion.forms_otrosi import OtroSiForm
from gestion.models import Contrato, Local, Tercero, TipoContrato


def _datos_contrato(contrato, **extra):
    """Convierte la instancia en datos POST minimos validos para ContratoForm."""
    datos = {
        'num_contrato': contrato.num_contrato,
        'tipo_contrato_cliente_proveedor': contrato.tipo_contrato_cliente_proveedor,
        'objeto_destinacion': contrato.objeto_destinacion,
        'nit_concedente': contrato.nit_concedente,
        'rep_legal_concedente': contrato.rep_legal_concedente,
        'fecha_firma': contrato.fecha_firma.isoformat(),
        'fecha_inicial_contrato': contrato.fecha_inicial_contrato.isoformat(),
        'fecha_final_inicial': contrato.fecha_final_inicial.isoformat(),
        'duracion_inicial_meses': contrato.duracion_inicial_meses,
        'modalidad_pago': contrato.modalidad_pago,
        'canon_minimo_garantizado': str(contrato.canon_minimo_garantizado),
        'arrendatario': contrato.arrendatario_id,
        'local': contrato.local_id,
        'tipo_contrato': contrato.tipo_contrato_id,
        'dias_preaviso_no_renovacion': contrato.dias_preaviso_no_renovacion,
        'dias_terminacion_anticipada': contrato.dias_terminacion_anticipada,
        'vigente': 'on',
    }
    datos.update(extra)
    return datos


@override_settings(ALLOWED_HOSTS=['*'])
class AutorizacionFormulariosTest(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(username='jefe', password='testpass123', is_staff=True)
        self.auxiliar = User.objects.create_user(username='aux', password='testpass123', is_staff=False)
        self.local = Local.objects.create(nombre_comercial_stand='Local 1', total_area_m2=100)
        self.tipo = TipoContrato.objects.create(nombre='Arrendamiento')
        self.tercero = Tercero.objects.create(
            nit='900111222-3', razon_social='Tercero Uno', tipo='ARRENDATARIO', nombre_rep_legal='Rep',
        )
        self.otro_tercero = Tercero.objects.create(
            nit='900333444-5', razon_social='Tercero Dos', tipo='ARRENDATARIO', nombre_rep_legal='Rep 2',
        )
        self.contrato = Contrato.objects.create(
            num_contrato='C-001', tipo_contrato_cliente_proveedor='CLIENTE',
            objeto_destinacion='Objeto original', nit_concedente='800', rep_legal_concedente='Legal',
            fecha_firma=date(2025, 1, 1), fecha_inicial_contrato=date(2025, 1, 1),
            fecha_final_inicial=date(2026, 12, 31), duracion_inicial_meses=24,
            modalidad_pago='Fijo', canon_minimo_garantizado=1000000,
            arrendatario=self.tercero, local=self.local, tipo_contrato=self.tipo,
            creado_por='sistema', vigente=True,
        )

    # ── CN-006 ───────────────────────────────────────────────────────────
    def test_no_staff_no_puede_cambiar_campos_protegidos_manipulando_el_post(self):
        datos = _datos_contrato(
            self.contrato,
            num_contrato='C-HACKEADO', objeto_destinacion='Objeto alterado',
            arrendatario=self.otro_tercero.pk,
        )
        form = ContratoForm(datos, instance=self.contrato, user=self.auxiliar)
        self.assertTrue(form.is_valid(), form.errors)
        contrato = form.save()
        contrato.refresh_from_db()
        self.assertEqual(contrato.num_contrato, 'C-001')
        self.assertEqual(contrato.objeto_destinacion.lower(), 'objeto original')
        self.assertEqual(contrato.arrendatario_id, self.tercero.pk)

    def test_staff_si_puede_cambiar_campos_generales(self):
        datos = _datos_contrato(self.contrato, objeto_destinacion='Objeto nuevo')
        form = ContratoForm(datos, instance=self.contrato, user=self.staff)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().objeto_destinacion.lower(), 'objeto nuevo')

    def test_vista_editar_ignora_campos_protegidos_de_no_staff(self):
        self.client.force_login(self.auxiliar)
        datos = _datos_contrato(self.contrato, num_contrato='C-HACKEADO')
        self.client.post(f'/contratos/{self.contrato.pk}/editar/', datos)
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.num_contrato, 'C-001')

    # ── CN-007 ───────────────────────────────────────────────────────────
    def test_campos_de_auditoria_y_estado_no_son_asignables_por_formulario(self):
        for campo in ['creado_por', 'fecha_creacion', 'modificado_por', 'fecha_modificacion',
                      'eliminado_por', 'fecha_eliminacion', 'finalizado',
                      'ultima_renovacion_automatica_por', 'fecha_ultima_renovacion_automatica']:
            self.assertNotIn(campo, ContratoForm(user=self.staff).fields, campo)

    def test_no_se_puede_finalizar_contrato_via_edicion(self):
        datos = _datos_contrato(self.contrato, finalizado='on', creado_por='atacante')
        form = ContratoForm(datos, instance=self.contrato, user=self.staff)
        self.assertTrue(form.is_valid(), form.errors)
        contrato = form.save()
        contrato.refresh_from_db()
        self.assertFalse(contrato.finalizado)
        self.assertEqual(contrato.creado_por, 'sistema')

    # ── CN-008 ───────────────────────────────────────────────────────────
    def test_no_staff_no_puede_elegir_estado_aprobado_en_otrosi(self):
        form = OtroSiForm(contrato=self.contrato, contrato_id=self.contrato.pk, user=self.auxiliar)
        estados = [c[0] for c in form.fields['estado'].choices]
        self.assertNotIn('APROBADO', estados)
        self.assertIn('BORRADOR', estados)

    def test_no_staff_con_estado_aprobado_en_post_es_rechazado(self):
        datos = {
            'tipo': 'AMENDMENT', 'estado': 'APROBADO', 'fecha_otrosi': '2026-01-10',
            'effective_from': '2026-01-10', 'descripcion': 'Intento de aprobar',
        }
        form = OtroSiForm(datos, contrato=self.contrato, contrato_id=self.contrato.pk, user=self.auxiliar)
        self.assertFalse(form.is_valid())
        self.assertIn('estado', form.errors)

    def test_staff_conserva_estado_aprobado_disponible(self):
        form = OtroSiForm(contrato=self.contrato, contrato_id=self.contrato.pk, user=self.staff)
        self.assertIn('APROBADO', [c[0] for c in form.fields['estado'].choices])
