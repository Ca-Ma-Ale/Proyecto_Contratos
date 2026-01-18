"""
Utilidades para registrar auditoría de acciones en el sistema.
"""
from django.utils import timezone


def registrar_creacion(instancia, usuario):
    """
    Registra la creación de una instancia.
    
    Args:
        instancia: Instancia del modelo a registrar
        usuario: Usuario que realiza la acción
    """
    if usuario and usuario.is_authenticated:
        nombre_usuario = usuario.get_full_name() or usuario.username
        if hasattr(instancia, 'creado_por'):
            instancia.creado_por = nombre_usuario
        if hasattr(instancia, 'fecha_creacion'):
            instancia.fecha_creacion = timezone.now()
        # También establecer fecha_modificacion en la creación
        if hasattr(instancia, 'fecha_modificacion'):
            instancia.fecha_modificacion = timezone.now()
        if hasattr(instancia, 'modificado_por'):
            instancia.modificado_por = nombre_usuario


def registrar_modificacion(instancia, usuario):
    """
    Registra la modificación de una instancia.
    
    Args:
        instancia: Instancia del modelo a registrar
        usuario: Usuario que realiza la acción
    """
    if usuario and usuario.is_authenticated:
        nombre_usuario = usuario.get_full_name() or usuario.username
        if hasattr(instancia, 'modificado_por'):
            instancia.modificado_por = nombre_usuario
        if hasattr(instancia, 'fecha_modificacion'):
            instancia.fecha_modificacion = timezone.now()


def registrar_eliminacion(instancia, usuario):
    """
    Registra la eliminación de una instancia antes de eliminarla.
    IMPORTANTE: Llamar ANTES de hacer delete().
    
    Args:
        instancia: Instancia del modelo a registrar
        usuario: Usuario que realiza la acción
    """
    if usuario and usuario.is_authenticated:
        nombre_usuario = usuario.get_full_name() or usuario.username
        if hasattr(instancia, 'eliminado_por'):
            instancia.eliminado_por = nombre_usuario
        if hasattr(instancia, 'fecha_eliminacion'):
            instancia.fecha_eliminacion = timezone.now()
            # Guardar antes de eliminar para registrar la eliminación
            instancia.save(update_fields=['eliminado_por', 'fecha_eliminacion'])


def guardar_con_auditoria(instancia, usuario, es_nuevo=None):
    """
    Guarda una instancia registrando automáticamente la auditoría.
    
    Args:
        instancia: Instancia del modelo a guardar
        usuario: Usuario que realiza la acción
        es_nuevo: Si es None, se detecta automáticamente. True = nuevo, False = modificación
    """
    if es_nuevo is None:
        es_nuevo = instancia.pk is None
    
    if es_nuevo:
        registrar_creacion(instancia, usuario)
    else:
        registrar_modificacion(instancia, usuario)
    
    instancia.save()

