"""
Comando para diagnosticar por que un contrato no aparece en Informes de Ventas.
"""

from calendar import monthrange
from datetime import date

from django.core.management.base import BaseCommand

from gestion.models import Contrato
from gestion.utils_otrosi import (
    obtener_valores_vigentes_facturacion_ventas,
    es_fecha_fuera_vigencia_contrato,
)
from gestion.views.utils import _obtener_fecha_final_contrato


def _es_contrato_vigente_en_fecha(contrato, fecha_referencia):
    fecha_final = _obtener_fecha_final_contrato(contrato, fecha_referencia)
    if not fecha_final:
        return True
    return fecha_final >= fecha_referencia


class Command(BaseCommand):
    help = 'Diagnostica por que un contrato no aparece en Informes de Ventas'

    def add_arguments(self, parser):
        parser.add_argument('num_contrato', type=str, help='Numero de contrato (ej: 2026-0102)')
        parser.add_argument('--mes', type=int, default=None, help='Mes (1-12), default: mes actual')
        parser.add_argument('--año', type=int, default=None, help='Año, default: año actual')

    def handle(self, *args, **options):
        num_contrato = options['num_contrato']
        mes = options['mes'] or date.today().month
        año = options['año'] or date.today().year

        self.stdout.write(self.style.SUCCESS(f'=== Diagnostico Informes Ventas: {num_contrato} ===\n'))
        self.stdout.write(f'Periodo: {mes}/{año}\n')

        contrato = Contrato.objects.filter(num_contrato=num_contrato).first()
        if not contrato:
            self.stdout.write(self.style.ERROR(f'Contrato {num_contrato} no encontrado en la base de datos.'))
            return

        ultimo_dia = monthrange(año, mes)[1]
        fecha_corte = date(año, mes, ultimo_dia)

        self.stdout.write(f'Contrato encontrado: {contrato.num_contrato}')
        self.stdout.write(f'  reporta_ventas: {contrato.reporta_ventas}')
        self.stdout.write(f'  modalidad_pago: {contrato.modalidad_pago}')
        self.stdout.write(f'  porcentaje_ventas: {contrato.porcentaje_ventas}')
        self.stdout.write(f'  fecha_inicial_contrato: {contrato.fecha_inicial_contrato}')
        self.stdout.write(f'  fecha_final_inicial: {contrato.fecha_final_inicial}')
        self.stdout.write('')

        if not contrato.reporta_ventas:
            self.stdout.write(self.style.ERROR('CAUSA: reporta_ventas=False. El contrato no reporta ventas.'))
            return

        fuera_vigencia = es_fecha_fuera_vigencia_contrato(contrato, fecha_corte)
        self.stdout.write(f'es_fecha_fuera_vigencia_contrato(contrato, {fecha_corte}): {fuera_vigencia}')
        if fuera_vigencia:
            self.stdout.write(self.style.ERROR(
                'CAUSA: La fecha de corte esta fuera de la vigencia del contrato '
                '(anterior al inicio o posterior al fin).'
            ))
            fecha_final = _obtener_fecha_final_contrato(contrato, fecha_corte)
            self.stdout.write(f'  fecha_final vigente: {fecha_final}')
            return

        contrato_vigente = _es_contrato_vigente_en_fecha(contrato, fecha_corte)
        self.stdout.write(f'_es_contrato_vigente_en_fecha(contrato, {fecha_corte}): {contrato_vigente}')
        fecha_final = _obtener_fecha_final_contrato(contrato, fecha_corte)
        self.stdout.write(f'  fecha_final vigente: {fecha_final}')

        valores = obtener_valores_vigentes_facturacion_ventas(contrato, mes, año)
        self.stdout.write(f'obtener_valores_vigentes_facturacion_ventas: {"SI" if valores else "NO"}')
        if not valores:
            self.stdout.write(self.style.ERROR(
                'CAUSA: obtener_valores_vigentes_facturacion_ventas retorna None. '
                'Posibles razones: modalidad no es Variable Puro o Hibrido, o porcentaje_ventas es None.'
            ))
            self.stdout.write(f'  modalidad requerida: Variable Puro o Hibrido (Min Garantizado)')
            self.stdout.write(f'  modalidad actual (contrato): {contrato.modalidad_pago}')
            return

        self.stdout.write(self.style.SUCCESS('El contrato DEBERIA aparecer en Informes de Ventas.'))
        self.stdout.write(f'  valores: {valores}')
