from django.db.models import Q


MODALIDADES_VENTAS = ['Variable Puro', 'Hibrido (Min Garantizado)']


def contratos_con_configuracion_ventas_queryset():
    from gestion.models import Contrato

    return Contrato.objects.filter(
        Q(reporta_ventas=True)
        | Q(
            modalidad_pago__in=MODALIDADES_VENTAS,
            porcentaje_ventas__isnull=False,
        )
        | Q(
            otrosi__estado='APROBADO',
            otrosi__nuevo_porcentaje_ventas__isnull=False,
        )
    ).distinct()


def contrato_reporta_ventas(contrato, mes=None, año=None):
    """
    Un contrato reporta ventas si tiene marcada la casilla del contrato base
    O si, para el periodo indicado (por defecto el mes actual), su modalidad
    vigente contando Otros Sí es Variable Puro / Híbrido con porcentaje.
    Así un Otro Sí que pasa el contrato a % de ventas se reconoce solo, sin
    que el usuario tenga que editar el contrato original.
    """
    from datetime import date
    from gestion.utils_otrosi import obtener_valores_vigentes_facturacion_ventas

    if getattr(contrato, 'reporta_ventas', False):
        return True
    if not mes or not año:
        hoy = date.today()
        mes, año = hoy.month, hoy.year
    try:
        return obtener_valores_vigentes_facturacion_ventas(contrato, int(mes), int(año)) is not None
    except Exception:
        return False
