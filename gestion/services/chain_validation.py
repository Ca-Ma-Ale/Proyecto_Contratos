"""
ChainValidationService — Servicio central de validación de efecto cadena.

Responsabilidades:
  1. verificar_bloqueos()       — consulta qué campos están bloqueados y por qué
  2. registrar_dependencias()   — crea DependenciaDocumento al aprobar un doc
  3. liberar_dependencias()     — elimina DependenciaDocumento al borrar un doc
  4. auditar_cambio()           — registra HistorialCampoContrato
  5. puede_eliminar()           — indica si un documento puede borrarse

Solo invocado desde views, signals y el override de save() del Contrato.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

from gestion.constants import (
    CAMPOS_BLOQUEADOS_POR_CALCULO_IPC,
    CAMPOS_BLOQUEADOS_POR_CALCULO_SMLV,
    CAMPOS_BLOQUEADOS_POR_CALCULO_VENTAS,
    CAMPOS_BLOQUEADOS_POR_RENOVACION,
    CAMPOS_OTROSI_BLOQUEADOS_POR_CALCULO_IPC,
    CAMPOS_POLIZAS_CONTRATO,
    LABELS_CAMPOS,
    MAPA_OTROSI_A_CONTRATO,
)

if TYPE_CHECKING:
    from gestion.models import (
        Contrato,
        OtroSi,
        RenovacionAutomatica,
        CalculoIPC,
        CalculoSalarioMinimo,
        CalculoFacturacionVentas,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _label(campo: str) -> str:
    return LABELS_CAMPOS.get(campo, campo.replace('_', ' ').title())


def _serialize(value) -> object:
    """Convierte valores a tipos serializables en JSON."""
    if value is None:
        return None
    if hasattr(value, 'isoformat'):   # date / datetime
        return value.isoformat()
    if hasattr(value, '__float__'):   # Decimal
        return float(value)
    return str(value)


# ─────────────────────────────────────────────────────────────────────────────
# 1. verificar_bloqueos
# ─────────────────────────────────────────────────────────────────────────────

def verificar_bloqueos(tipo: str, objeto_id: int, campos: list[str] | None = None) -> dict:
    """
    Retorna un diccionario campo → lista de bloqueadores activos.

    Args:
        tipo      : 'CONTRATO' | 'OTROSI'
        objeto_id : pk del documento
        campos    : lista de campos a consultar. Si es None consulta todos.

    Returns:
        {
          'valor_canon_fijo': [
            {
              'tipo': 'OTROSI',
              'id': 42,
              'descripcion': 'OtroSí #2 — Canon $5.200.000',
              'url': '/otrosi/42/',
              'label': 'Valor Canon Fijo',
            },
            ...
          ],
          'fecha_final_actualizada': [],   # vacío → no bloqueado
          ...
        }
    """
    from gestion.models import DependenciaDocumento

    qs = DependenciaDocumento.objects.filter(
        bloqueado_tipo=tipo,
        bloqueado_id=objeto_id,
    )
    if campos:
        qs = qs.filter(campo_bloqueado__in=campos)

    resultado: dict[str, list] = {}
    if campos:
        for c in campos:
            resultado[c] = []

    for dep in qs.order_by('campo_bloqueado', '-fecha_registro'):
        campo = dep.campo_bloqueado
        if campo not in resultado:
            resultado[campo] = []
        resultado[campo].append({
            'tipo':        dep.bloqueador_tipo,
            'id':          dep.bloqueador_id,
            'descripcion': dep.bloqueador_descripcion,
            'url':         dep.bloqueador_url,
            'label':       dep.label_campo or _label(campo),
        })

    return resultado


def hay_bloqueos(tipo: str, objeto_id: int, campos: list[str]) -> bool:
    """Versión rápida: True si al menos un campo está bloqueado."""
    from gestion.models import DependenciaDocumento
    return DependenciaDocumento.objects.filter(
        bloqueado_tipo=tipo,
        bloqueado_id=objeto_id,
        campo_bloqueado__in=campos,
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# 2. registrar_dependencias
# ─────────────────────────────────────────────────────────────────────────────

def registrar_dependencias_otrosi(otrosi: 'OtroSi') -> None:
    """
    Llamado cuando un OtroSí pasa a estado APROBADO.

    Crea DependenciaDocumento para:
      a) Cada campo modificado → bloquea el Contrato Base
      b) Cada campo modificado → bloquea OtroSís anteriores que tengan ese campo
    """
    from gestion.models import DependenciaDocumento
    from django.urls import reverse

    try:
        url_otrosi = reverse('gestion:detalle_otrosi', args=[otrosi.pk])
    except Exception:
        url_otrosi = ''

    fecha_str = otrosi.fecha_otrosi.strftime('%d/%m/%Y') if otrosi.fecha_otrosi else ''
    desc_base = f"OtroSí {otrosi.numero_otrosi} — Aprobado {fecha_str}"

    # ── a) Bloquear Contrato Base ────────────────────────────────────────────
    campos_a_bloquear_en_contrato: list[str] = []

    for campo_otrosi, campo_contrato in MAPA_OTROSI_A_CONTRATO.items():
        valor = getattr(otrosi, campo_otrosi, None)
        if valor is not None and valor != '':
            campos_a_bloquear_en_contrato.append(campo_contrato)
            _crear_dependencia(
                bloqueador_tipo='OTROSI',
                bloqueador_id=otrosi.pk,
                bloqueador_descripcion=f"{desc_base} | {_label(campo_contrato)}: {_serialize(valor)}",
                bloqueador_url=url_otrosi,
                bloqueado_tipo='CONTRATO',
                bloqueado_id=otrosi.contrato_id,
                campo=campo_contrato,
            )

    # modifica_polizas bloquea todos los campos de pólizas
    if otrosi.modifica_polizas:
        for campo_poliza in CAMPOS_POLIZAS_CONTRATO:
            _crear_dependencia(
                bloqueador_tipo='OTROSI',
                bloqueador_id=otrosi.pk,
                bloqueador_descripcion=f"{desc_base} | Modificación de pólizas",
                bloqueador_url=url_otrosi,
                bloqueado_tipo='CONTRATO',
                bloqueado_id=otrosi.contrato_id,
                campo=campo_poliza,
            )

    # ── b) Bloquear OtroSís anteriores ──────────────────────────────────────
    from gestion.models import OtroSi
    otrosis_anteriores = OtroSi.objects.filter(
        contrato_id=otrosi.contrato_id,
        estado='APROBADO',
    ).exclude(pk=otrosi.pk)

    if otrosi.fecha_otrosi:
        otrosis_anteriores = otrosis_anteriores.filter(
            fecha_otrosi__lt=otrosi.fecha_otrosi
        )

    for campo_otrosi in MAPA_OTROSI_A_CONTRATO:
        valor = getattr(otrosi, campo_otrosi, None)
        if valor is None or valor == '':
            continue
        for oa in otrosis_anteriores:
            if getattr(oa, campo_otrosi, None) not in (None, ''):
                _crear_dependencia(
                    bloqueador_tipo='OTROSI',
                    bloqueador_id=otrosi.pk,
                    bloqueador_descripcion=f"{desc_base} | reemplaza {_label(campo_otrosi)}",
                    bloqueador_url=url_otrosi,
                    bloqueado_tipo='OTROSI',
                    bloqueado_id=oa.pk,
                    campo=campo_otrosi,
                )


def registrar_dependencias_renovacion(renovacion: 'RenovacionAutomatica') -> None:
    """Llamado cuando una RenovaciónAutomática pasa a estado APROBADA."""
    from django.urls import reverse
    try:
        url = reverse('gestion:editar_renovacion_automatica', args=[renovacion.pk])
    except Exception:
        url = ''

    fecha_str = renovacion.fecha_renovacion.strftime('%d/%m/%Y') if renovacion.fecha_renovacion else ''
    desc = f"Renovación Automática #{renovacion.numero_renovacion} — Aprobada {fecha_str}"

    # Bloquea fecha_final_actualizada en el Contrato
    _crear_dependencia(
        bloqueador_tipo='RENOVACION',
        bloqueador_id=renovacion.pk,
        bloqueador_descripcion=desc,
        bloqueador_url=url,
        bloqueado_tipo='CONTRATO',
        bloqueado_id=renovacion.contrato_id,
        campo='fecha_final_actualizada',
    )

    # Bloquea OtroSís anteriores que tenían nueva_fecha_final_actualizada
    from gestion.models import OtroSi
    for oa in OtroSi.objects.filter(
        contrato_id=renovacion.contrato_id,
        estado='APROBADO',
        nueva_fecha_final_actualizada__isnull=False,
    ):
        _crear_dependencia(
            bloqueador_tipo='RENOVACION',
            bloqueador_id=renovacion.pk,
            bloqueador_descripcion=f"{desc} | reemplaza fecha final de OtroSí {oa.numero_otrosi}",
            bloqueador_url=url,
            bloqueado_tipo='OTROSI',
            bloqueado_id=oa.pk,
            campo='nueva_fecha_final_actualizada',
        )


def registrar_dependencias_calculo_ipc(calculo: 'CalculoIPC') -> None:
    """Llamado cuando un CalculoIPC pasa a estado APLICADO."""
    from django.urls import reverse
    try:
        url = reverse('gestion:detalle_calculo_ipc', args=[calculo.pk])
    except Exception:
        url = ''

    fecha_str = calculo.fecha_aplicacion.strftime('%d/%m/%Y') if calculo.fecha_aplicacion else ''
    desc = f"Ajuste IPC {calculo.año_aplicacion} — Aplicado {fecha_str} — Nuevo canon: ${calculo.nuevo_canon:,.0f}"

    for campo in CAMPOS_BLOQUEADOS_POR_CALCULO_IPC:
        _crear_dependencia(
            bloqueador_tipo='CALCULO_IPC',
            bloqueador_id=calculo.pk,
            bloqueador_descripcion=desc,
            bloqueador_url=url,
            bloqueado_tipo='CONTRATO',
            bloqueado_id=calculo.contrato_id,
            campo=campo,
        )

    # Bloquear OtroSís anteriores que definían el canon base
    from gestion.models import OtroSi
    for oa in OtroSi.objects.filter(
        contrato_id=calculo.contrato_id,
        estado='APROBADO',
        nuevo_valor_canon__isnull=False,
    ):
        for campo_os in CAMPOS_OTROSI_BLOQUEADOS_POR_CALCULO_IPC:
            if getattr(oa, campo_os, None) is not None:
                _crear_dependencia(
                    bloqueador_tipo='CALCULO_IPC',
                    bloqueador_id=calculo.pk,
                    bloqueador_descripcion=f"{desc} | tomó canon de OtroSí {oa.numero_otrosi} como base",
                    bloqueador_url=url,
                    bloqueado_tipo='OTROSI',
                    bloqueado_id=oa.pk,
                    campo=campo_os,
                )


def registrar_dependencias_calculo_smlv(calculo: 'CalculoSalarioMinimo') -> None:
    """Llamado cuando un CalculoSalarioMinimo pasa a estado APLICADO."""
    from django.urls import reverse
    try:
        url = reverse('gestion:lista_calculos_salario_minimo')
    except Exception:
        url = ''

    fecha_str = calculo.fecha_aplicacion.strftime('%d/%m/%Y') if calculo.fecha_aplicacion else ''
    desc = f"Ajuste SMLV {calculo.año_aplicacion} — Aplicado {fecha_str} — Nuevo canon: ${calculo.nuevo_canon:,.0f}"

    for campo in CAMPOS_BLOQUEADOS_POR_CALCULO_SMLV:
        _crear_dependencia(
            bloqueador_tipo='CALCULO_SMLV',
            bloqueador_id=calculo.pk,
            bloqueador_descripcion=desc,
            bloqueador_url=url,
            bloqueado_tipo='CONTRATO',
            bloqueado_id=calculo.contrato_id,
            campo=campo,
        )


def registrar_dependencias_calculo_ventas(calculo: 'CalculoFacturacionVentas') -> None:
    """Llamado cuando un CalculoFacturacionVentas pasa a confirmado=True."""
    from django.urls import reverse
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    mes_nombre = meses[calculo.mes - 1] if 1 <= calculo.mes <= 12 else str(calculo.mes)
    desc = f"Cálculo Ventas {mes_nombre}/{calculo.año} — Confirmado — ${calculo.valor_a_facturar_variable:,.0f}"

    try:
        url = reverse('gestion:resultado_calculo_facturacion', args=[calculo.pk])
    except Exception:
        url = ''

    for campo in CAMPOS_BLOQUEADOS_POR_CALCULO_VENTAS:
        _crear_dependencia(
            bloqueador_tipo='CALCULO_VENTAS',
            bloqueador_id=calculo.pk,
            bloqueador_descripcion=desc,
            bloqueador_url=url,
            bloqueado_tipo='CONTRATO',
            bloqueado_id=calculo.contrato_id,
            campo=campo,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. liberar_dependencias
# ─────────────────────────────────────────────────────────────────────────────

def liberar_dependencias(bloqueador_tipo: str, bloqueador_id: int) -> int:
    """
    Elimina todas las DependenciaDocumento donde este documento es el bloqueador.
    Llamado desde signals post_delete o al anular cálculos.

    Retorna el número de registros eliminados.
    """
    from gestion.models import DependenciaDocumento
    eliminados, _ = DependenciaDocumento.objects.filter(
        bloqueador_tipo=bloqueador_tipo,
        bloqueador_id=bloqueador_id,
    ).delete()
    return eliminados


def recalcular_dependencias_otrosi(otrosi_pk: int) -> None:
    """
    Recalcula las dependencias de un OtroSí: elimina las existentes y las regenera.
    Útil para corregir registros creados con lógica anterior incorrecta.

    Uso desde la shell:
        from gestion.services.chain_validation import recalcular_dependencias_otrosi
        recalcular_dependencias_otrosi(<pk>)
    """
    from gestion.models import OtroSi
    otrosi = OtroSi.objects.get(pk=otrosi_pk)
    liberar_dependencias('OTROSI', otrosi_pk)
    if otrosi.estado == 'APROBADO':
        registrar_dependencias_otrosi(otrosi)


# ─────────────────────────────────────────────────────────────────────────────
# 4. auditar_cambio
# ─────────────────────────────────────────────────────────────────────────────

def auditar_cambio(
    tipo_documento: str,
    documento_id: int,
    documento_descripcion: str,
    nombre_campo: str,
    valor_anterior,
    valor_nuevo,
    modificado_por: str,
    causa_tipo: str,
    causa_descripcion: str = '',
    ip_origen: str | None = None,
) -> None:
    """
    Registra un cambio en HistorialCampoContrato.
    No lanza excepciones: si falla, no debe interrumpir el flujo principal.
    """
    try:
        from gestion.models import HistorialCampoContrato
        HistorialCampoContrato.objects.create(
            tipo_documento=tipo_documento,
            documento_id=documento_id,
            documento_descripcion=documento_descripcion,
            nombre_campo=nombre_campo,
            label_campo=_label(nombre_campo),
            valor_anterior=_serialize(valor_anterior),
            valor_nuevo=_serialize(valor_nuevo),
            modificado_por=modificado_por or 'sistema',
            fecha_modificacion=timezone.now(),
            ip_origen=ip_origen,
            causa_tipo=causa_tipo,
            causa_descripcion=causa_descripcion,
        )
    except Exception:
        pass  # Auditoría no debe romper el flujo de negocio


# ─────────────────────────────────────────────────────────────────────────────
# 5. puede_eliminar
# ─────────────────────────────────────────────────────────────────────────────

def puede_eliminar(bloqueador_tipo: str, bloqueador_id: int) -> tuple[bool, list[dict]]:
    """
    Verifica si un documento puede eliminarse.

    Un documento NO puede eliminarse si él mismo está bloqueado por otros
    documentos posteriores.

    Ejemplo: OtroSí #1 no puede eliminarse si OtroSí #2 bloquea algún
    campo de OtroSí #1.

    Returns:
        (True, [])           → puede eliminarse
        (False, [bloqueadores]) → no puede; lista de quién lo bloquea
    """
    from gestion.models import DependenciaDocumento

    # El tipo del OtroSí como "bloqueado" es 'OTROSI'
    tipo_bloqueado = _tipo_bloqueado_para(bloqueador_tipo)
    if not tipo_bloqueado:
        return True, []

    deps = DependenciaDocumento.objects.filter(
        bloqueado_tipo=tipo_bloqueado,
        bloqueado_id=bloqueador_id,
    ).order_by('bloqueador_tipo', 'bloqueador_id')

    if not deps.exists():
        return True, []

    bloqueadores = []
    vistos = set()
    for dep in deps:
        clave = (dep.bloqueador_tipo, dep.bloqueador_id)
        if clave not in vistos:
            vistos.add(clave)
            bloqueadores.append({
                'tipo':        dep.bloqueador_tipo,
                'id':          dep.bloqueador_id,
                'descripcion': dep.bloqueador_descripcion,
                'url':         dep.bloqueador_url,
            })

    return False, bloqueadores


def _tipo_bloqueado_para(bloqueador_tipo: str) -> str | None:
    """Mapea el tipo bloqueador al tipo que aparece como 'bloqueado'."""
    return {
        'OTROSI':         'OTROSI',
        'RENOVACION':     None,     # las renovaciones no son bloqueadas por nadie más
        'CALCULO_IPC':    None,
        'CALCULO_SMLV':   None,
        'CALCULO_VENTAS': None,
    }.get(bloqueador_tipo)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers privados
# ─────────────────────────────────────────────────────────────────────────────

def _crear_dependencia(
    bloqueador_tipo: str,
    bloqueador_id: int,
    bloqueador_descripcion: str,
    bloqueador_url: str,
    bloqueado_tipo: str,
    bloqueado_id: int,
    campo: str,
) -> None:
    """
    Crea una DependenciaDocumento evitando duplicados.
    Si ya existe (mismo bloqueador + bloqueado + campo), no crea otra.
    """
    from gestion.models import DependenciaDocumento
    DependenciaDocumento.objects.get_or_create(
        bloqueador_tipo=bloqueador_tipo,
        bloqueador_id=bloqueador_id,
        bloqueado_tipo=bloqueado_tipo,
        bloqueado_id=bloqueado_id,
        campo_bloqueado=campo,
        defaults={
            'bloqueador_descripcion': bloqueador_descripcion,
            'bloqueador_url':         bloqueador_url,
            'label_campo':            _label(campo),
        },
    )
