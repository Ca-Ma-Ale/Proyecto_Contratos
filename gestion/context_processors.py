"""
Context processors para hacer disponible información global en todos los templates
"""

import logging

logger = logging.getLogger(__name__)


def admin_general_status(request):
    """
    Expone si el usuario actual es Admin General en todos los templates.
    """
    es_admin_general = False
    if request.user.is_authenticated:
        try:
            es_admin_general = request.user.perfil.es_admin_general
        except Exception:
            pass
    return {'es_admin_general': es_admin_general}


def empresa_config(request):
    """
    Agrega la configuración de la empresa al contexto de todos los templates
    """
    try:
        from gestion.views.utils import obtener_configuracion_empresa
        configuracion_empresa = obtener_configuracion_empresa()
        return {
            'empresa_config': configuracion_empresa,
        }
    except Exception as e:
        logger.warning("No se pudo cargar la configuración de empresa: %s", str(e))
        return {
            'empresa_config': None,
        }

