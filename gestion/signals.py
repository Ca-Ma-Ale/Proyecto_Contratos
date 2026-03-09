"""
Señales para el sistema de gestión de contratos.

Señales existentes:
  - eliminar_polizas_otrosi         : borra pólizas al eliminar OtroSí
  - eliminar_polizas_renovacion     : borra pólizas al eliminar Renovación

Señales nuevas (Efecto Cadena):
  - otrosi_aprobado                 : registra dependencias al aprobar OtroSí
  - otrosi_eliminado                : libera dependencias al eliminar OtroSí
  - renovacion_aprobada             : registra dependencias al aprobar Renovación
  - renovacion_eliminada            : libera dependencias al eliminar Renovación
  - calculo_ipc_aplicado            : registra dependencias al aplicar CalculoIPC
  - calculo_ipc_eliminado           : libera dependencias al eliminar CalculoIPC
  - calculo_smlv_aplicado           : registra dependencias al aplicar CalculoSMLV
  - calculo_smlv_eliminado          : libera dependencias al eliminar CalculoSMLV
  - calculo_ventas_confirmado       : registra dependencias al confirmar Cálculo Ventas
  - calculo_ventas_eliminado        : libera dependencias al eliminar Cálculo Ventas
"""
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from gestion.models import (
    CalculoFacturacionVentas,
    CalculoIPC,
    CalculoSalarioMinimo,
    OtroSi,
    Poliza,
    RenovacionAutomatica,
)


# ─────────────────────────────────────────────────────────────────────────────
# SEÑALES EXISTENTES — Eliminación de pólizas
# ─────────────────────────────────────────────────────────────────────────────

@receiver(pre_delete, sender=OtroSi)
def eliminar_polizas_otrosi(sender, instance, **kwargs):
    """Antes de eliminar un OtroSi, eliminar todas sus pólizas asociadas."""
    polizas_count = instance.polizas.count()
    if polizas_count > 0:
        try:
            from gestion.models import registrar_eliminacion
            for poliza in instance.polizas.all():
                try:
                    registrar_eliminacion(
                        poliza,
                        instance.contrato.creado_por if hasattr(instance.contrato, 'creado_por') else None
                    )
                except Exception:
                    pass
        except ImportError:
            pass
        instance.polizas.all().delete()


@receiver(pre_delete, sender=RenovacionAutomatica)
def eliminar_polizas_renovacion(sender, instance, **kwargs):
    """Antes de eliminar una RenovacionAutomatica, eliminar todas sus pólizas asociadas."""
    polizas_count = instance.polizas.count()
    if polizas_count > 0:
        try:
            from gestion.models import registrar_eliminacion
            for poliza in instance.polizas.all():
                try:
                    registrar_eliminacion(
                        poliza,
                        instance.contrato.creado_por if hasattr(instance.contrato, 'creado_por') else None
                    )
                except Exception:
                    pass
        except ImportError:
            pass
        instance.polizas.all().delete()


# ─────────────────────────────────────────────────────────────────────────────
# SEÑALES NUEVAS — Efecto Cadena
# ─────────────────────────────────────────────────────────────────────────────

# ── OtroSí ───────────────────────────────────────────────────────────────────

# Guardamos el estado anterior para detectar la transición a APROBADO
_OTROSI_ESTADO_ANTERIOR: dict[int, str] = {}


@receiver(pre_save, sender=OtroSi)
def otrosi_pre_save(sender, instance, **kwargs):
    """Captura el estado actual antes de guardar para detectar transiciones."""
    if instance.pk:
        try:
            anterior = OtroSi.objects.get(pk=instance.pk)
            _OTROSI_ESTADO_ANTERIOR[instance.pk] = anterior.estado
        except OtroSi.DoesNotExist:
            pass


@receiver(post_save, sender=OtroSi)
def otrosi_post_save(sender, instance, created, **kwargs):
    """
    Detecta cuando un OtroSí pasa a estado APROBADO y registra sus dependencias.
    Solo actúa en la transición BORRADOR/EN_REVISION → APROBADO.
    """
    from gestion.services.chain_validation import registrar_dependencias_otrosi

    estado_anterior = _OTROSI_ESTADO_ANTERIOR.pop(instance.pk, None)

    if instance.estado == 'APROBADO' and estado_anterior != 'APROBADO':
        try:
            registrar_dependencias_otrosi(instance)
        except Exception:
            pass  # La auditoría no debe romper el flujo


@receiver(pre_delete, sender=OtroSi)
def otrosi_pre_delete_cadena(sender, instance, **kwargs):
    """
    Captura el estado del OtroSí antes de que sea eliminado
    para poder liberar dependencias después.
    """
    # Guardamos el pk para usarlo en post_delete
    # (en post_delete, instance ya no existe en BD pero el objeto Python sí)
    pass


@receiver(post_delete, sender=OtroSi)
def otrosi_post_delete(sender, instance, **kwargs):
    """
    Libera las DependenciaDocumento donde este OtroSí era el bloqueador.
    También registra el evento en el historial de auditoría.
    """
    from gestion.services.chain_validation import auditar_cambio, liberar_dependencias

    eliminados = liberar_dependencias('OTROSI', instance.pk)

    if eliminados > 0:
        auditar_cambio(
            tipo_documento='OTROSI',
            documento_id=instance.pk,
            documento_descripcion=f"OtroSí {instance.numero_otrosi} (eliminado)",
            nombre_campo='estado',
            valor_anterior=instance.estado,
            valor_nuevo='ELIMINADO',
            modificado_por=getattr(instance, '_eliminado_por', 'sistema'),
            causa_tipo='ELIMINACION_OTROSI',
            causa_descripcion=(
                f"OtroSí {instance.numero_otrosi} eliminado. "
                f"Se liberaron {eliminados} bloqueos."
            ),
        )


# ── RenovaciónAutomática ──────────────────────────────────────────────────────

_RENOVACION_ESTADO_ANTERIOR: dict[int, str] = {}


@receiver(pre_save, sender=RenovacionAutomatica)
def renovacion_pre_save(sender, instance, **kwargs):
    """Captura el estado actual antes de guardar."""
    if instance.pk:
        try:
            anterior = RenovacionAutomatica.objects.get(pk=instance.pk)
            _RENOVACION_ESTADO_ANTERIOR[instance.pk] = anterior.estado
        except RenovacionAutomatica.DoesNotExist:
            pass


@receiver(post_save, sender=RenovacionAutomatica)
def renovacion_post_save(sender, instance, created, **kwargs):
    """
    Detecta cuando una RenovaciónAutomática pasa a APROBADA y registra dependencias.
    """
    from gestion.services.chain_validation import registrar_dependencias_renovacion

    estado_anterior = _RENOVACION_ESTADO_ANTERIOR.pop(instance.pk, None)

    if instance.estado == 'APROBADA' and estado_anterior != 'APROBADA':
        try:
            registrar_dependencias_renovacion(instance)
        except Exception:
            pass


@receiver(post_delete, sender=RenovacionAutomatica)
def renovacion_post_delete(sender, instance, **kwargs):
    """Libera dependencias al eliminar una RenovaciónAutomática."""
    from gestion.services.chain_validation import auditar_cambio, liberar_dependencias

    eliminados = liberar_dependencias('RENOVACION', instance.pk)

    if eliminados > 0:
        auditar_cambio(
            tipo_documento='RENOVACION',
            documento_id=instance.pk,
            documento_descripcion=f"Renovación Automática #{instance.numero_renovacion} (eliminada)",
            nombre_campo='estado',
            valor_anterior=instance.estado,
            valor_nuevo='ELIMINADA',
            modificado_por=getattr(instance, '_eliminado_por', 'sistema'),
            causa_tipo='ELIMINACION_RENOVACION',
            causa_descripcion=(
                f"Renovación #{instance.numero_renovacion} eliminada. "
                f"Se liberaron {eliminados} bloqueos."
            ),
        )


# ── CalculoIPC ────────────────────────────────────────────────────────────────

_CALCULO_IPC_ESTADO_ANTERIOR: dict[int, str] = {}


@receiver(pre_save, sender=CalculoIPC)
def calculo_ipc_pre_save(sender, instance, **kwargs):
    """Captura el estado actual antes de guardar."""
    if instance.pk:
        try:
            anterior = CalculoIPC.objects.get(pk=instance.pk)
            _CALCULO_IPC_ESTADO_ANTERIOR[instance.pk] = anterior.estado
        except CalculoIPC.DoesNotExist:
            pass


@receiver(post_save, sender=CalculoIPC)
def calculo_ipc_post_save(sender, instance, created, **kwargs):
    """Detecta cuando CalculoIPC pasa a APLICADO y registra dependencias."""
    from gestion.services.chain_validation import registrar_dependencias_calculo_ipc

    estado_anterior = _CALCULO_IPC_ESTADO_ANTERIOR.pop(instance.pk, None)

    if instance.estado == 'APLICADO' and estado_anterior != 'APLICADO':
        try:
            registrar_dependencias_calculo_ipc(instance)
        except Exception:
            pass


@receiver(post_delete, sender=CalculoIPC)
def calculo_ipc_post_delete(sender, instance, **kwargs):
    """Libera dependencias al eliminar un CalculoIPC."""
    from gestion.services.chain_validation import liberar_dependencias
    liberar_dependencias('CALCULO_IPC', instance.pk)


# ── CalculoSalarioMinimo ──────────────────────────────────────────────────────

_CALCULO_SMLV_ESTADO_ANTERIOR: dict[int, str] = {}


@receiver(pre_save, sender=CalculoSalarioMinimo)
def calculo_smlv_pre_save(sender, instance, **kwargs):
    """Captura el estado actual antes de guardar."""
    if instance.pk:
        try:
            anterior = CalculoSalarioMinimo.objects.get(pk=instance.pk)
            _CALCULO_SMLV_ESTADO_ANTERIOR[instance.pk] = anterior.estado
        except CalculoSalarioMinimo.DoesNotExist:
            pass


@receiver(post_save, sender=CalculoSalarioMinimo)
def calculo_smlv_post_save(sender, instance, created, **kwargs):
    """Detecta cuando CalculoSMLV pasa a APLICADO y registra dependencias."""
    from gestion.services.chain_validation import registrar_dependencias_calculo_smlv

    estado_anterior = _CALCULO_SMLV_ESTADO_ANTERIOR.pop(instance.pk, None)

    if instance.estado == 'APLICADO' and estado_anterior != 'APLICADO':
        try:
            registrar_dependencias_calculo_smlv(instance)
        except Exception:
            pass


@receiver(post_delete, sender=CalculoSalarioMinimo)
def calculo_smlv_post_delete(sender, instance, **kwargs):
    """Libera dependencias al eliminar un CalculoSMLV."""
    from gestion.services.chain_validation import liberar_dependencias
    liberar_dependencias('CALCULO_SMLV', instance.pk)


# ── CalculoFacturacionVentas ──────────────────────────────────────────────────

_CALCULO_VENTAS_CONFIRMADO_ANTERIOR: dict[int, bool] = {}


@receiver(pre_save, sender=CalculoFacturacionVentas)
def calculo_ventas_pre_save(sender, instance, **kwargs):
    """Captura el estado confirmado antes de guardar."""
    if instance.pk:
        try:
            anterior = CalculoFacturacionVentas.objects.get(pk=instance.pk)
            _CALCULO_VENTAS_CONFIRMADO_ANTERIOR[instance.pk] = anterior.confirmado
        except CalculoFacturacionVentas.DoesNotExist:
            pass


@receiver(post_save, sender=CalculoFacturacionVentas)
def calculo_ventas_post_save(sender, instance, created, **kwargs):
    """Detecta cuando CalculoFacturacionVentas pasa a confirmado=True y registra dependencias."""
    from gestion.services.chain_validation import registrar_dependencias_calculo_ventas

    confirmado_anterior = _CALCULO_VENTAS_CONFIRMADO_ANTERIOR.pop(instance.pk, False)

    if instance.confirmado and not confirmado_anterior:
        try:
            registrar_dependencias_calculo_ventas(instance)
        except Exception:
            pass


@receiver(post_delete, sender=CalculoFacturacionVentas)
def calculo_ventas_post_delete(sender, instance, **kwargs):
    """Libera dependencias al eliminar un CalculoFacturacionVentas."""
    from gestion.services.chain_validation import liberar_dependencias
    liberar_dependencias('CALCULO_VENTAS', instance.pk)
