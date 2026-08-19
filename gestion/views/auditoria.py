"""
Vistas de auditoría — Efecto Cadena.

Acceso restringido exclusivamente al Admin General.
Muestra el historial de todos los cambios de todos los usuarios
sobre campos relevantes de contratos, OtroSís y renovaciones.
"""
import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from gestion.decorators import admin_general_required
from gestion.models import (
    Contrato,
    DependenciaDocumento,
    HistorialCampoContrato,
)


@admin_general_required
def auditoria_historial_campos(request):
    """
    Historial completo de cambios por campo.
    Filtros: contrato, campo, usuario, causa_tipo, rango de fechas.
    Solo visible para el Admin General.
    """
    qs = HistorialCampoContrato.objects.all()

    # ── Filtros ───────────────────────────────────────────────────────────────
    filtro_contrato = request.GET.get('contrato', '').strip()
    filtro_campo = request.GET.get('campo', '').strip()
    filtro_usuario = request.GET.get('usuario', '').strip()
    filtro_causa = request.GET.get('causa', '').strip()
    filtro_fecha_desde = request.GET.get('fecha_desde', '').strip()
    filtro_fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    filtro_tipo_doc = request.GET.get('tipo_doc', '').strip()

    if filtro_contrato:
        # Busca por numero de contrato (tipo_documento=CONTRATO y documento_descripcion contiene)
        qs = qs.filter(documento_descripcion__icontains=filtro_contrato)

    if filtro_campo:
        qs = qs.filter(nombre_campo__icontains=filtro_campo)

    if filtro_usuario:
        qs = qs.filter(modificado_por__icontains=filtro_usuario)

    if filtro_causa:
        qs = qs.filter(causa_tipo=filtro_causa)

    if filtro_tipo_doc:
        qs = qs.filter(tipo_documento=filtro_tipo_doc)

    if filtro_fecha_desde:
        try:
            from datetime import datetime
            fecha_desde = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')
            qs = qs.filter(fecha_modificacion__date__gte=fecha_desde.date())
        except ValueError:
            pass

    if filtro_fecha_hasta:
        try:
            from datetime import datetime
            fecha_hasta = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            qs = qs.filter(fecha_modificacion__date__lte=fecha_hasta.date())
        except ValueError:
            pass

    qs = qs.order_by('-fecha_modificacion')

    # ── Paginación ────────────────────────────────────────────────────────────
    paginator = Paginator(qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # ── Opciones para filtros ─────────────────────────────────────────────────
    causas_choices = HistorialCampoContrato.CAUSA_CHOICES
    tipos_doc_choices = [
        ('CONTRATO',  'Contrato'),
        ('OTROSI',    'Otro Sí'),
        ('RENOVACION','Renovación Automática'),
    ]

    context = {
        'titulo': 'Historial de Auditoría — Efecto Cadena',
        'page_obj': page_obj,
        'total_registros': qs.count(),
        # Filtros activos
        'filtro_contrato': filtro_contrato,
        'filtro_campo': filtro_campo,
        'filtro_usuario': filtro_usuario,
        'filtro_causa': filtro_causa,
        'filtro_fecha_desde': filtro_fecha_desde,
        'filtro_fecha_hasta': filtro_fecha_hasta,
        'filtro_tipo_doc': filtro_tipo_doc,
        # Opciones
        'causas_choices': causas_choices,
        'tipos_doc_choices': tipos_doc_choices,
    }
    return render(request, 'gestion/auditoria/historial_campos.html', context)


@admin_general_required
def auditoria_dependencias_activas(request):
    """
    Mapa de dependencias activas: qué está bloqueando qué en este momento.
    Solo visible para el Admin General.
    """
    qs = DependenciaDocumento.objects.all()

    # ── Filtros ───────────────────────────────────────────────────────────────
    filtro_bloqueador_tipo = request.GET.get('bloqueador_tipo', '').strip()
    filtro_bloqueado_tipo = request.GET.get('bloqueado_tipo', '').strip()
    filtro_campo = request.GET.get('campo', '').strip()

    if filtro_bloqueador_tipo:
        qs = qs.filter(bloqueador_tipo=filtro_bloqueador_tipo)
    if filtro_bloqueado_tipo:
        qs = qs.filter(bloqueado_tipo=filtro_bloqueado_tipo)
    if filtro_campo:
        qs = qs.filter(campo_bloqueado__icontains=filtro_campo)

    qs = qs.order_by('bloqueado_tipo', 'bloqueado_id', 'campo_bloqueado')

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'titulo': 'Dependencias Activas — Efecto Cadena',
        'page_obj': page_obj,
        'total_registros': qs.count(),
        'filtro_bloqueador_tipo': filtro_bloqueador_tipo,
        'filtro_bloqueado_tipo': filtro_bloqueado_tipo,
        'filtro_campo': filtro_campo,
        'bloqueador_tipos': DependenciaDocumento.BLOQUEADOR_TIPO_CHOICES,
        'bloqueado_tipos': DependenciaDocumento.BLOQUEADO_TIPO_CHOICES,
    }
    return render(request, 'gestion/auditoria/dependencias_activas.html', context)


@admin_general_required
def exportar_historial_campos_csv(request):
    """
    Exporta el historial de campos a CSV.
    Aplica los mismos filtros que la vista principal.
    """
    qs = HistorialCampoContrato.objects.all().order_by('-fecha_modificacion')

    filtro_contrato = request.GET.get('contrato', '').strip()
    filtro_campo = request.GET.get('campo', '').strip()
    filtro_usuario = request.GET.get('usuario', '').strip()
    filtro_causa = request.GET.get('causa', '').strip()

    if filtro_contrato:
        qs = qs.filter(documento_descripcion__icontains=filtro_contrato)
    if filtro_campo:
        qs = qs.filter(nombre_campo__icontains=filtro_campo)
    if filtro_usuario:
        qs = qs.filter(modificado_por__icontains=filtro_usuario)
    if filtro_causa:
        qs = qs.filter(causa_tipo=filtro_causa)

    fecha_str = timezone.now().strftime('%Y%m%d_%H%M')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="auditoria_campos_{fecha_str}.csv"'
    response.write('\ufeff')  # BOM para Excel

    writer = csv.writer(response)
    writer.writerow([
        'Fecha', 'Tipo Documento', 'Documento', 'Campo',
        'Valor Anterior', 'Valor Nuevo',
        'Modificado Por', 'Causa', 'Descripción Causa',
    ])

    from gestion.services.exportes import neutralizar_formula

    for registro in qs:
        writer.writerow([neutralizar_formula(v) for v in (
            registro.fecha_modificacion.strftime('%d/%m/%Y %H:%M:%S'),
            registro.tipo_documento,
            registro.documento_descripcion,
            registro.label_campo or registro.nombre_campo,
            registro.valor_anterior,
            registro.valor_nuevo,
            registro.modificado_por,
            registro.get_causa_tipo_display(),
            registro.causa_descripcion,
        )])

    return response
