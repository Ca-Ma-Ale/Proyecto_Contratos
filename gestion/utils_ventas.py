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
