"""
Señales para el sistema de gestión de contratos.
"""
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from gestion.models import OtroSi, RenovacionAutomatica, Poliza


@receiver(pre_delete, sender=OtroSi)
def eliminar_polizas_otrosi(sender, instance, **kwargs):
    """
    Antes de eliminar un OtroSi, eliminar todas sus pólizas asociadas.
    """
    polizas_count = instance.polizas.count()
    if polizas_count > 0:
        # Registrar eliminación de cada póliza para auditoría si existe el sistema
        try:
            from gestion.models import registrar_eliminacion
            for poliza in instance.polizas.all():
                # Intentar registrar eliminación si existe la función
                try:
                    registrar_eliminacion(poliza, instance.contrato.creado_por if hasattr(instance.contrato, 'creado_por') else None)
                except Exception:
                    pass
        except ImportError:
            pass
        instance.polizas.all().delete()


@receiver(pre_delete, sender=RenovacionAutomatica)
def eliminar_polizas_renovacion(sender, instance, **kwargs):
    """
    Antes de eliminar una RenovacionAutomatica, eliminar todas sus pólizas asociadas.
    """
    polizas_count = instance.polizas.count()
    if polizas_count > 0:
        # Registrar eliminación de cada póliza para auditoría si existe el sistema
        try:
            from gestion.models import registrar_eliminacion
            for poliza in instance.polizas.all():
                # Intentar registrar eliminación si existe la función
                try:
                    registrar_eliminacion(poliza, instance.contrato.creado_por if hasattr(instance.contrato, 'creado_por') else None)
                except Exception:
                    pass
        except ImportError:
            pass
        instance.polizas.all().delete()
