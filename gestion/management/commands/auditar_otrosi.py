"""
Comando para auditar y corregir novedades en OtroSís:
  - PLAZO_EXTENSION con nuevo_plazo_meses = 0
  - PLAZO_EXTENSION con nueva_fecha_final_actualizada = null
  - AMENDMENT / CANON_CHANGE / POLIZAS_UPDATE con nuevo_plazo_meses = 0

Uso:
    python manage.py auditar_otrosi            # solo audita, no modifica
    python manage.py auditar_otrosi --fix      # audita y corrige automáticamente
"""

from django.core.management.base import BaseCommand
from gestion.models import OtroSi


def _calcular_meses(desde, hasta):
    meses = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    if hasta.day >= desde.day:
        meses += 1
    return meses


TIPOS_SIN_PLAZO = ('AMENDMENT', 'CANON_CHANGE', 'POLIZAS_UPDATE', 'IPC_UPDATE', 'RENEWAL', 'OTRO')


class Command(BaseCommand):
    help = 'Audita OtroSís con novedades en plazo y fecha final. Use --fix para corregir.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Aplica las correcciones automáticamente (por defecto solo audita)',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        modo = 'CORRECCION' if fix else 'SOLO AUDITORIA'

        self.stdout.write(self.style.SUCCESS(
            '\n=== Auditoria OtroSis — Novedades en Plazo y Fecha Final ===\n'
            f'Modo: {modo}\n'
        ))

        novedad_total = 0

        # ── Caso 1: tipos no-plazo con nuevo_plazo_meses = 0 ──────────────────
        self.stdout.write(self.style.WARNING(
            'CASO 1: AMENDMENT / CANON_CHANGE / POLIZAS_UPDATE con nuevo_plazo_meses = 0'
            ' (deberia ser null)\n'
        ))
        caso1 = OtroSi.objects.filter(
            tipo__in=TIPOS_SIN_PLAZO,
            nuevo_plazo_meses=0,
        ).select_related('contrato').order_by('contrato__num_contrato', 'numero_otrosi')

        if not caso1.exists():
            self.stdout.write('  Sin novedades.\n')
        else:
            for os in caso1:
                self.stdout.write(
                    '  [%s] %s | %s | estado=%s' % (
                        os.tipo, os.numero_otrosi,
                        os.contrato.num_contrato, os.estado,
                    )
                )
                novedad_total += 1
                if fix:
                    os.nuevo_plazo_meses = None
                    os.save(update_fields=['nuevo_plazo_meses'])
                    self.stdout.write(self.style.SUCCESS('    -> CORREGIDO: nuevo_plazo_meses = null'))
                else:
                    self.stdout.write('    -> nuevo_plazo_meses = 0 (usar --fix para corregir)')

        self.stdout.write('')

        # ── Caso 2: PLAZO_EXTENSION con nuevo_plazo_meses = 0 ─────────────────
        self.stdout.write(self.style.WARNING(
            'CASO 2: PLAZO_EXTENSION con nuevo_plazo_meses = 0\n'
        ))
        caso2 = OtroSi.objects.filter(
            tipo='PLAZO_EXTENSION',
            nuevo_plazo_meses=0,
        ).select_related('contrato').order_by('contrato__num_contrato', 'numero_otrosi')

        if not caso2.exists():
            self.stdout.write('  Sin novedades.\n')
        else:
            for os in caso2:
                meses = _calcular_meses(os.effective_from, os.effective_to) if os.effective_to else None
                self.stdout.write(
                    '  %s | %s | %s -> %s | meses_calculados=%s | fecha_final_actual=%s' % (
                        os.numero_otrosi, os.contrato.num_contrato,
                        os.effective_from, os.effective_to,
                        meses, os.nueva_fecha_final_actualizada,
                    )
                )
                novedad_total += 1
                if fix and meses is not None:
                    os.nuevo_plazo_meses = meses
                    os.nueva_fecha_final_actualizada = os.effective_to
                    os.save(update_fields=['nuevo_plazo_meses', 'nueva_fecha_final_actualizada'])
                    self.stdout.write(self.style.SUCCESS(
                        '    -> CORREGIDO: nuevo_plazo_meses=%d, fecha_final=%s' % (meses, os.effective_to)
                    ))
                elif fix and meses is None:
                    self.stdout.write(self.style.ERROR(
                        '    -> SIN effective_to — requiere revision manual'
                    ))
                else:
                    self.stdout.write('    -> Usar --fix para corregir')

        self.stdout.write('')

        # ── Caso 3: PLAZO_EXTENSION con nueva_fecha_final_actualizada = null ──
        self.stdout.write(self.style.WARNING(
            'CASO 3: PLAZO_EXTENSION con nueva_fecha_final_actualizada = null\n'
        ))
        caso3 = OtroSi.objects.filter(
            tipo='PLAZO_EXTENSION',
            nueva_fecha_final_actualizada__isnull=True,
        ).exclude(
            nuevo_plazo_meses=0,  # ya cubiertos en caso 2
        ).select_related('contrato').order_by('contrato__num_contrato', 'numero_otrosi')

        if not caso3.exists():
            self.stdout.write('  Sin novedades.\n')
        else:
            for os in caso3:
                meses_calc = _calcular_meses(os.effective_from, os.effective_to) if os.effective_to else None
                self.stdout.write(
                    '  %s | %s | %s -> %s | plazo_actual=%s | meses_calculados=%s' % (
                        os.numero_otrosi, os.contrato.num_contrato,
                        os.effective_from, os.effective_to,
                        os.nuevo_plazo_meses, meses_calc,
                    )
                )
                novedad_total += 1
                if fix and os.effective_to:
                    campos = ['nueva_fecha_final_actualizada']
                    os.nueva_fecha_final_actualizada = os.effective_to
                    if os.nuevo_plazo_meses is None and meses_calc is not None:
                        os.nuevo_plazo_meses = meses_calc
                        campos.append('nuevo_plazo_meses')
                    os.save(update_fields=campos)
                    self.stdout.write(self.style.SUCCESS(
                        '    -> CORREGIDO: fecha_final=%s%s' % (
                            os.effective_to,
                            ', nuevo_plazo_meses=%d' % meses_calc if 'nuevo_plazo_meses' in campos else '',
                        )
                    ))
                elif fix and not os.effective_to:
                    self.stdout.write(self.style.ERROR(
                        '    -> SIN effective_to — requiere revision manual'
                    ))
                else:
                    self.stdout.write('    -> Usar --fix para corregir')

        self.stdout.write('')

        # ── Resumen ────────────────────────────────────────────────────────────
        if novedad_total == 0:
            self.stdout.write(self.style.SUCCESS('=== Sin novedades. Base de datos limpia. ===\n'))
        else:
            if fix:
                self.stdout.write(self.style.SUCCESS(
                    '=== Auditoria completada. %d novedades procesadas. ===\n' % novedad_total
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    '=== %d novedad(es) encontrada(s). Ejecute con --fix para corregir. ===\n' % novedad_total
                ))
