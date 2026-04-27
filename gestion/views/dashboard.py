from datetime import timedelta

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from gestion.decorators import login_required_custom, ajax_login_required
from gestion.models import Contrato, Local, Poliza, Tercero
from gestion.services.alertas import (
    obtener_alertas_expiracion_contratos,
    obtener_alertas_ipc,
    obtener_alertas_salario_minimo,
    obtener_alertas_preaviso,
    obtener_alertas_polizas_requeridas_no_aportadas,
    obtener_alertas_terminacion_anticipada,
    obtener_alertas_renovacion_automatica,
    obtener_polizas_criticas,
    obtener_tipo_condicion_ipc_vigente,
    AlertaPolizaRequerida,
    _obtener_fecha_final_contrato,
)
from gestion.services.exportes import (
    ColumnaExportacion,
    ExportacionVaciaError,
    generar_excel_corporativo,
)
from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
from .utils import _respuesta_archivo_excel, obtener_canon_vigente


@login_required_custom
def dashboard(request):
    """
    Dashboard principal — carga instantánea.
    Solo realiza 2 queries COUNT. Las estadísticas pesadas y las alertas
    se cargan vía AJAX por api_conteos_alertas() y api_detalle_alertas().
    """
    context = {
        'total_contratos': Contrato.objects.count(),
        'total_polizas': Poliza.objects.count(),
        'fecha_actual': timezone.now().date(),
    }
    return render(request, 'gestion/dashboard/index.html', context)


@login_required_custom
def centro_alertas(request):
    """
    Vista dedicada para el centro de alertas.
    Renderiza el contenedor vacío — las alertas se cargan vía AJAX.
    """
    tipo_filtro = request.GET.get('tipo_alerta', '')
    context = {
        'tipo_filtro': tipo_filtro,
        'fecha_actual': timezone.now().date(),
    }
    return render(request, 'gestion/alertas/index.html', context)


@ajax_login_required
def api_conteos_alertas(request):
    """
    Endpoint AJAX: devuelve estadísticas generales + conteos de alertas.
    No devuelve el detalle — solo números para el panel de inicio.
    """
    fecha_actual = timezone.now().date()

    # Vigentes/vencidos directamente en DB (sin loop Python)
    contratos_vigentes = Contrato.objects.filter(vigente=True).count()
    contratos_vencidos = Contrato.objects.count() - contratos_vigentes

    # Única consulta con todos los datos necesarios para el resto del endpoint
    contratos_list = list(
        Contrato.objects.filter(vigente=True)
        .select_related('arrendatario', 'proveedor', 'local', 'tipo_contrato', 'tipo_servicio')
        .prefetch_related(
            'otrosi', 'renovaciones_automaticas',
            'polizas', 'polizas__otrosi', 'polizas__renovacion_automatica',
        )
    )

    # Conteo de modalidades en un solo loop (usa caché de prefetch)
    contratos_fijos = 0
    contratos_variables = 0
    contratos_hibridos = 0
    for contrato in contratos_list:
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_modalidad_pago', fecha_actual
        )
        modalidad_actual = (
            otrosi_modificador.nueva_modalidad_pago
            if otrosi_modificador and otrosi_modificador.nueva_modalidad_pago
            else contrato.modalidad_pago
        )
        if modalidad_actual == 'Fijo':
            contratos_fijos += 1
        elif modalidad_actual == 'Variable Puro':
            contratos_variables += 1
        elif modalidad_actual == 'Hibrido (Min Garantizado)':
            contratos_hibridos += 1

    # Todos los conteos de alertas usan la misma lista en memoria (0 queries adicionales)
    vencimiento = len(obtener_alertas_expiracion_contratos(fecha_referencia=fecha_actual, ventana_dias=90, contratos_qs=contratos_list))
    polizas_criticas = len(obtener_polizas_criticas(fecha_referencia=fecha_actual))
    preaviso = len(obtener_alertas_preaviso(fecha_referencia=fecha_actual, contratos_qs=contratos_list))
    ipc_list = obtener_alertas_ipc(fecha_referencia=fecha_actual, contratos_qs=contratos_list)
    sm_list = obtener_alertas_salario_minimo(fecha_referencia=fecha_actual, contratos_qs=contratos_list)

    # Deduplicación IPC / Salario Mínimo
    ids_en_sm = {a.contrato.id for a in sm_list}
    ids_en_ipc = {a.contrato.id for a in ipc_list}
    contratos_duplicados = ids_en_ipc & ids_en_sm
    if contratos_duplicados:
        ipc_list = [
            a for a in ipc_list
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'IPC'
        ]
        sm_list = [
            a for a in sm_list
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'SALARIO_MINIMO'
        ]

    polizas_requeridas = len(obtener_alertas_polizas_requeridas_no_aportadas(fecha_referencia=fecha_actual, contratos_qs=contratos_list))
    terminacion = len(obtener_alertas_terminacion_anticipada(fecha_referencia=fecha_actual, contratos_qs=contratos_list))
    renovacion_automatica = len(obtener_alertas_renovacion_automatica(fecha_referencia=fecha_actual))

    return JsonResponse({
        'contratos_vigentes': contratos_vigentes,
        'contratos_vencidos': contratos_vencidos,
        'total_polizas': Poliza.objects.count(),
        'contratos_fijos': contratos_fijos,
        'contratos_variables': contratos_variables,
        'contratos_hibridos': contratos_hibridos,
        'alertas': {
            'vencimiento': vencimiento,
            'polizas_criticas': polizas_criticas,
            'preaviso': preaviso,
            'ipc': len(ipc_list),
            'salario_minimo': len(sm_list),
            'polizas_requeridas': polizas_requeridas,
            'terminacion': terminacion,
            'renovacion_automatica': renovacion_automatica,
        },
    })


@ajax_login_required
def api_detalle_alertas(request):
    """
    Endpoint AJAX: devuelve HTML pre-renderizado con todas las tarjetas de alertas.
    Acepta ?tipo_alerta=CLIENTE|PROVEEDOR para filtrar.
    """
    fecha_actual = timezone.now().date()
    tipo_filtro = request.GET.get('tipo_alerta', '')

    # === Lógica idéntica al dashboard original ===
    contratos_por_vencer_list = obtener_alertas_expiracion_contratos(fecha_referencia=fecha_actual, ventana_dias=90)
    contratos_por_vencer_con_fecha = []
    for contrato in contratos_por_vencer_list:
        if tipo_filtro and contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_actual)
        contratos_por_vencer_con_fecha.append({
            'contrato': contrato,
            'fecha_final_actualizada': fecha_final_actual,
        })

    polizas_criticas_list = obtener_polizas_criticas(fecha_referencia=fecha_actual)
    polizas_criticas = [
        p for p in polizas_criticas_list
        if not tipo_filtro or p.contrato.tipo_contrato_cliente_proveedor == tipo_filtro
    ]

    alertas_preaviso_list = obtener_alertas_preaviso(fecha_referencia=fecha_actual)
    alertas_preaviso_con_fecha = []
    for contrato in alertas_preaviso_list:
        if tipo_filtro and contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_actual)
        alertas_preaviso_con_fecha.append({
            'contrato': contrato,
            'fecha_final_actualizada': fecha_final_actual,
        })

    alertas_ipc_list = obtener_alertas_ipc(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_filtro if tipo_filtro else None
    )
    alertas_ipc = list(alertas_ipc_list)

    alertas_salario_minimo_list = obtener_alertas_salario_minimo(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_filtro if tipo_filtro else None
    )
    alertas_salario_minimo = list(alertas_salario_minimo_list)

    # Deduplicación IPC / Salario Mínimo (preservar lógica original)
    ids_en_sm = {a.contrato.id for a in alertas_salario_minimo}
    ids_en_ipc = {a.contrato.id for a in alertas_ipc}
    contratos_duplicados = ids_en_ipc & ids_en_sm
    if contratos_duplicados:
        alertas_ipc = [
            a for a in alertas_ipc
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'IPC'
        ]
        alertas_salario_minimo = [
            a for a in alertas_salario_minimo
            if a.contrato.id not in contratos_duplicados
            or obtener_tipo_condicion_ipc_vigente(a.contrato, fecha_actual) == 'SALARIO_MINIMO'
        ]

    alertas_polizas_requeridas_list = obtener_alertas_polizas_requeridas_no_aportadas(fecha_referencia=fecha_actual)
    alertas_polizas_requeridas = [
        a for a in alertas_polizas_requeridas_list
        if not tipo_filtro or a.contrato.tipo_contrato_cliente_proveedor == tipo_filtro
    ]

    alertas_terminacion_list = obtener_alertas_terminacion_anticipada(fecha_referencia=fecha_actual)
    alertas_terminacion = [
        a for a in alertas_terminacion_list
        if not tipo_filtro or a.contrato.tipo_contrato_cliente_proveedor == tipo_filtro
    ]

    alertas_renovacion_automatica = obtener_alertas_renovacion_automatica(fecha_referencia=fecha_actual)

    context = {
        'fecha_actual': fecha_actual,
        'tipo_filtro': tipo_filtro,
        'contratos_por_vencer': contratos_por_vencer_con_fecha,
        'total_alertas_vencimiento': len(contratos_por_vencer_con_fecha),
        'polizas_criticas': polizas_criticas,
        'total_polizas_criticas': len(polizas_criticas),
        'hay_polizas_con_colchon': any(getattr(p, 'tiene_colchon', False) for p in polizas_criticas),
        'alertas_preaviso_renovacion': alertas_preaviso_con_fecha,
        'total_alertas_preaviso': len(alertas_preaviso_con_fecha),
        'alertas_ipc': alertas_ipc,
        'total_alertas_ipc': len(alertas_ipc),
        'alertas_salario_minimo': alertas_salario_minimo,
        'total_alertas_salario_minimo': len(alertas_salario_minimo),
        'alertas_polizas_requeridas': alertas_polizas_requeridas,
        'total_alertas_polizas_requeridas': len(alertas_polizas_requeridas),
        'alertas_terminacion': alertas_terminacion,
        'total_alertas_terminacion': len(alertas_terminacion),
        'alertas_renovacion_automatica': alertas_renovacion_automatica,
        'total_alertas_renovacion_automatica': len(alertas_renovacion_automatica),
    }

    html = render_to_string(
        'gestion/alertas/_detalle_alertas.html',
        context,
        request=request,
    )

    totales = {
        'vencimiento': len(contratos_por_vencer_con_fecha),
        'polizas_criticas': len(polizas_criticas),
        'preaviso': len(alertas_preaviso_con_fecha),
        'ipc': len(alertas_ipc),
        'salario_minimo': len(alertas_salario_minimo),
        'polizas_requeridas': len(alertas_polizas_requeridas),
        'terminacion': len(alertas_terminacion),
        'renovacion_automatica': len(alertas_renovacion_automatica),
    }

    return JsonResponse({'html': html, 'totales': totales})


@login_required_custom
def exportaciones(request):
    """
    Centro de exportaciones de reportes del sistema.
    Permite seleccionar el informe a descargar.
    """
    fecha_actual = timezone.now().date()
    # Solo conteos simples (COUNT rápido). Los datos de alertas se calculan al generar cada reporte.
    total_contratos = Contrato.objects.count()
    total_terceros = Tercero.objects.count()
    total_locales = Local.objects.count()

    reportes = [
        {
            'codigo': 'exportar_contratos',
            'nombre': 'Exportar Contratos',
            'descripcion': 'Exportación completa de contratos con filtros avanzados (estado, tipo, fechas, arrendatario, local, etc.).',
            'total_registros': total_contratos,
            'url_name': 'gestion:exportar_contratos',
        },
        {
            'codigo': 'alertas_vencimiento',
            'nombre': 'Alertas de Vencimiento de Contrato',
            'descripcion': 'Contratos que vencen dentro de la ventana de monitoreo.',
            'total_registros': None,
            'url_name': 'gestion:exportar_alertas_vencimiento',
        },
        {
            'codigo': 'alertas_polizas',
            'nombre': 'Alertas de Pólizas Críticas',
            'descripcion': 'Pólizas vencidas, próximas a vencer o sin aportar.',
            'total_registros': None,
            'url_name': 'gestion:exportar_alertas_polizas',
        },
        {
            'codigo': 'alertas_preaviso',
            'nombre': 'Alertas de Renovación (Preaviso)',
            'descripcion': 'Contratos que requieren envío de preaviso de no renovación.',
            'total_registros': None,
            'url_name': 'gestion:exportar_alertas_preaviso',
        },
        {
            'codigo': 'estado_preavisos',
            'nombre': 'Estado de Preavisos',
            'descripcion': 'Panorama completo de todos los contratos vigentes: cuáles están en ventana de preaviso, cuáles próximos a entrar y cuáles no aplican, con fechas y días.',
            'total_registros': None,
            'url_name': 'gestion:exportar_estado_preavisos',
        },
        {
            'codigo': 'alertas_ipc',
            'nombre': 'Alertas de Ajuste de IPC',
            'descripcion': 'Contratos con ajustes de canon próximos por índice IPC.',
            'total_registros': None,
            'url_name': 'gestion:exportar_alertas_ipc',
        },
        {
            'codigo': 'alertas_salario_minimo',
            'nombre': 'Alertas de Ajuste de Salario Mínimo',
            'descripcion': 'Contratos con ajustes de canon próximos por Salario Mínimo.',
            'total_registros': None,
            'url_name': 'gestion:exportar_alertas_salario_minimo',
        },
        {
            'codigo': 'alertas_polizas_requeridas',
            'nombre': 'Alertas de Pólizas Requeridas No Aportadas',
            'descripcion': 'Contratos con pólizas requeridas que no han sido aportadas o están vencidas.',
            'total_registros': None,
            'url_name': 'gestion:exportar_alertas_polizas_requeridas',
        },
        {
            'codigo': 'alertas_terminacion',
            'nombre': 'Alertas de Terminación Anticipada',
            'descripcion': 'Contratos dentro del período de terminación anticipada.',
            'total_registros': None,
            'url_name': 'gestion:exportar_alertas_terminacion',
        },
        {
            'codigo': 'terceros',
            'nombre': 'Exportar Terceros',
            'descripcion': 'Listado de todos los terceros registrados (arrendatarios y proveedores) con su información de contacto.',
            'total_registros': total_terceros,
            'url_name': 'gestion:exportar_terceros',
        },
        {
            'codigo': 'locales',
            'nombre': 'Exportar Locales',
            'descripcion': 'Listado de todos los locales registrados con nombre comercial, ubicación y área.',
            'total_registros': total_locales,
            'url_name': 'gestion:exportar_locales',
        },
        {
            'codigo': 'recobro_polizas',
            'nombre': 'Recobro de Pólizas',
            'descripcion': 'Contratos con pólizas requeridas y su estado de recobro, con filtros por tipo de póliza y recobro.',
            'total_registros': total_contratos,
            'url_name': 'gestion:exportar_recobro_polizas',
        },
    ]

    context = {
        'fecha_actual': fecha_actual,
        'reportes': reportes,
    }
    return render(request, 'gestion/exportaciones/index.html', context)


def _construir_qs_contratos_filtrado(form):
    """Construye un queryset de contratos vigentes aplicando los filtros del formulario de reportes."""
    from django.db.models import Q

    qs = (
        Contrato.objects.filter(vigente=True)
        .select_related('arrendatario', 'proveedor', 'local')
        .prefetch_related('otrosi', 'renovaciones_automaticas')
    )

    tipo_cp = form.cleaned_data.get('tipo_contrato_cliente_proveedor')
    if tipo_cp:
        qs = qs.filter(tipo_contrato_cliente_proveedor=tipo_cp)

    tipo_contrato = form.cleaned_data.get('tipo_contrato')
    if tipo_contrato:
        qs = qs.filter(tipo_contrato=tipo_contrato)

    arrendatario = form.cleaned_data.get('arrendatario')
    if arrendatario:
        qs = qs.filter(arrendatario=arrendatario)

    local = form.cleaned_data.get('local')
    if local:
        qs = qs.filter(local=local)

    modalidad = form.cleaned_data.get('modalidad_pago')
    if modalidad:
        qs = qs.filter(modalidad_pago=modalidad)

    prorroga = form.cleaned_data.get('prorroga_automatica')
    if prorroga == 'si':
        qs = qs.filter(prorroga_automatica=True)
    elif prorroga == 'no':
        qs = qs.filter(prorroga_automatica=False)

    fecha_inicio_desde = form.cleaned_data.get('fecha_inicio_desde')
    if fecha_inicio_desde:
        qs = qs.filter(fecha_inicial_contrato__gte=fecha_inicio_desde)

    fecha_inicio_hasta = form.cleaned_data.get('fecha_inicio_hasta')
    if fecha_inicio_hasta:
        qs = qs.filter(fecha_inicial_contrato__lte=fecha_inicio_hasta)

    fecha_final_desde = form.cleaned_data.get('fecha_final_desde')
    if fecha_final_desde:
        qs = qs.filter(
            Q(fecha_final_actualizada__gte=fecha_final_desde) |
            Q(fecha_final_actualizada__isnull=True, fecha_final_inicial__gte=fecha_final_desde)
        )

    fecha_final_hasta = form.cleaned_data.get('fecha_final_hasta')
    if fecha_final_hasta:
        qs = qs.filter(
            Q(fecha_final_actualizada__lte=fecha_final_hasta) |
            Q(fecha_final_actualizada__isnull=True, fecha_final_inicial__lte=fecha_final_hasta)
        )

    return qs


@login_required_custom
def exportar_alertas_ipc(request):
    from gestion.forms import FiltroReportesAlertasForm

    fecha_actual = timezone.now().date()

    if request.method == 'POST':
        form = FiltroReportesAlertasForm(request.POST)
        if form.is_valid():
            alertas = obtener_alertas_ipc(contratos_qs=_construir_qs_contratos_filtrado(form))

            severidades_legibles = {
                'danger': 'Crítica (0-1 mes)',
                'warning': 'Moderada (2 meses)',
                'success': 'Preventiva (3+ meses)',
            }
            columnas = [
                ColumnaExportacion('Número de Contrato', ancho=22),
                ColumnaExportacion('Tercero', ancho=28),
                ColumnaExportacion('Local', ancho=26),
                ColumnaExportacion('Mes de Ajuste', ancho=18, alineacion='center'),
                ColumnaExportacion('Condición IPC', ancho=26),
                ColumnaExportacion('Meses Restantes', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Severidad', ancho=22),
                ColumnaExportacion('Canon Vigente', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Otrosí Modificador', ancho=25),
            ]
            registros = []
            for alerta in alertas:
                tercero = alerta.contrato.obtener_tercero()
                nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
                local_nombre = alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-'
                canon = obtener_canon_vigente(alerta.contrato, fecha_actual)
                registros.append((
                    alerta.contrato.num_contrato,
                    nombre_tercero,
                    local_nombre,
                    alerta.mes_ajuste,
                    alerta.condicion_ipc,
                    int(alerta.meses_restantes),
                    severidades_legibles.get(alerta.color_alerta, alerta.color_alerta),
                    float(canon) if canon else None,
                    alerta.otrosi_modificador or 'Contrato Original',
                ))
            try:
                archivo = generar_excel_corporativo(nombre_hoja='Alertas IPC', columnas=columnas, registros=registros)
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportaciones')
            return _respuesta_archivo_excel(archivo, 'alertas_ipc')
    else:
        form = FiltroReportesAlertasForm()

    return render(request, 'gestion/exportaciones/filtros_reporte.html', {
        'form': form,
        'titulo': 'Alertas de Ajuste de IPC',
        'descripcion': 'Aplique filtros para exportar los contratos con alertas de ajuste por IPC.',
        'url_name': 'gestion:exportar_alertas_ipc',
    })


@login_required_custom
def exportar_alertas_salario_minimo(request):
    from gestion.forms import FiltroReportesAlertasForm

    fecha_actual = timezone.now().date()

    if request.method == 'POST':
        form = FiltroReportesAlertasForm(request.POST)
        if form.is_valid():
            severidades_legibles = {
                'danger': 'Crítica (0-1 mes)',
                'warning': 'Moderada (2 meses)',
                'success': 'Preventiva (3+ meses)',
            }
            columnas = [
                ColumnaExportacion('Número de Contrato', ancho=22),
                ColumnaExportacion('Tercero', ancho=28),
                ColumnaExportacion('Local', ancho=26),
                ColumnaExportacion('Mes de Ajuste', ancho=18, alineacion='center'),
                ColumnaExportacion('Condición Salario Mínimo', ancho=30),
                ColumnaExportacion('Meses Restantes', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Severidad', ancho=22),
                ColumnaExportacion('Canon Vigente', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Otrosí Modificador', ancho=25),
            ]
            try:
                alertas = obtener_alertas_salario_minimo(contratos_qs=_construir_qs_contratos_filtrado(form))
            except Exception:
                messages.error(request, 'Error al obtener las alertas de Salario Mínimo.')
                return redirect('gestion:exportaciones')
            registros = []
            for alerta in alertas:
                try:
                    tercero = alerta.contrato.obtener_tercero()
                    canon = obtener_canon_vigente(alerta.contrato, fecha_actual)
                    registros.append((
                        alerta.contrato.num_contrato,
                        tercero.razon_social if tercero else 'Sin tercero asignado',
                        alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-',
                        alerta.mes_ajuste or '-',
                        alerta.condicion_salario_minimo or '-',
                        int(alerta.meses_restantes) if alerta.meses_restantes is not None else 0,
                        severidades_legibles.get(alerta.color_alerta, alerta.color_alerta) if alerta.color_alerta else 'N/A',
                        float(canon) if canon else None,
                        alerta.otrosi_modificador or 'Contrato Original',
                    ))
                except Exception:
                    continue
            try:
                archivo = generar_excel_corporativo(nombre_hoja='Alertas Salario Mínimo', columnas=columnas, registros=registros)
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportaciones')
            return _respuesta_archivo_excel(archivo, 'alertas_salario_minimo')
    else:
        form = FiltroReportesAlertasForm()

    return render(request, 'gestion/exportaciones/filtros_reporte.html', {
        'form': form,
        'titulo': 'Alertas de Ajuste de Salario Mínimo',
        'descripcion': 'Aplique filtros para exportar los contratos con alertas de ajuste por Salario Mínimo.',
        'url_name': 'gestion:exportar_alertas_salario_minimo',
    })


@login_required_custom
def exportar_alertas_vencimiento(request):
    from gestion.forms import FiltroReportesAlertasForm

    fecha_actual = timezone.now().date()

    if request.method == 'POST':
        form = FiltroReportesAlertasForm(request.POST)
        if form.is_valid():
            contratos = list(obtener_alertas_expiracion_contratos(
                fecha_referencia=fecha_actual,
                ventana_dias=90,
                contratos_qs=_construir_qs_contratos_filtrado(form),
            ))
            from gestion.utils_otrosi import get_otrosi_vigente
            columnas = [
                ColumnaExportacion('Número de Contrato', ancho=22),
                ColumnaExportacion('Arrendatario', ancho=30),
                ColumnaExportacion('Local', ancho=26),
                ColumnaExportacion('Fecha Final', ancho=18, alineacion='center'),
                ColumnaExportacion('Días Restantes', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Modalidad', ancho=20),
                ColumnaExportacion('Canon Vigente', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Otrosí Modificador', ancho=25),
            ]
            registros = []
            for contrato in contratos:
                fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_actual)
                otrosi_vigente = get_otrosi_vigente(contrato, fecha_actual)
                otrosi_numero = None
                if otrosi_vigente:
                    otrosi_numero = getattr(otrosi_vigente, 'numero_otrosi', None) or getattr(otrosi_vigente, 'numero_renovacion', None)
                otrosi_mod_modalidad = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(contrato, 'nueva_modalidad_pago', fecha_actual)
                modalidad_actual = (
                    otrosi_mod_modalidad.nueva_modalidad_pago
                    if otrosi_mod_modalidad and otrosi_mod_modalidad.nueva_modalidad_pago
                    else contrato.modalidad_pago or 'Sin especificar'
                )
                dias_restantes = (fecha_final_actual - fecha_actual).days if fecha_final_actual else None
                tercero = contrato.obtener_tercero()
                canon = obtener_canon_vigente(contrato, fecha_actual)
                registros.append((
                    contrato.num_contrato,
                    tercero.razon_social if tercero else 'Sin tercero asignado',
                    contrato.local.nombre_comercial_stand if contrato.local else '-',
                    fecha_final_actual,
                    dias_restantes,
                    modalidad_actual,
                    float(canon) if canon else None,
                    otrosi_numero or 'Contrato Original',
                ))
            try:
                archivo = generar_excel_corporativo(nombre_hoja='Contratos por Vencer', columnas=columnas, registros=registros)
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportaciones')
            return _respuesta_archivo_excel(archivo, 'alertas_vencimiento_contratos')
    else:
        form = FiltroReportesAlertasForm()

    return render(request, 'gestion/exportaciones/filtros_reporte.html', {
        'form': form,
        'titulo': 'Alertas de Vencimiento de Contrato',
        'descripcion': 'Aplique filtros para exportar los contratos que vencen en los próximos 90 días.',
        'url_name': 'gestion:exportar_alertas_vencimiento',
    })


@login_required_custom
def exportar_alertas_polizas(request):
    from gestion.forms import FiltroReportesAlertasForm

    fecha_actual = timezone.now().date()

    TIPO_A_CAMPO_FECHA_INICIO = {
        'RCE - Responsabilidad Civil': ('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce'),
        'Cumplimiento': ('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento'),
        'Poliza de Arrendamiento': ('nuevo_fecha_inicio_vigencia_arrendamiento', 'fecha_inicio_vigencia_arrendamiento'),
        'Arrendamiento': ('nuevo_fecha_inicio_vigencia_todo_riesgo', 'fecha_inicio_vigencia_todo_riesgo'),
        'Otra': ('nuevo_fecha_inicio_vigencia_otra_1', 'fecha_inicio_vigencia_otra_1'),
    }

    def _fecha_inicio_poliza(p):
        if p.fecha_inicio_vigencia:
            return p.fecha_inicio_vigencia
        campo_otrosi, campo_contrato = TIPO_A_CAMPO_FECHA_INICIO.get(p.tipo, (None, None))
        for obj in (p.otrosi, p.renovacion_automatica):
            if obj and campo_otrosi:
                v = getattr(obj, campo_otrosi, None)
                if v:
                    return v
        if campo_contrato:
            v = getattr(p.contrato, campo_contrato, None)
            if v:
                return v
        return p.contrato.fecha_inicial_contrato

    if request.method == 'POST':
        form = FiltroReportesAlertasForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            contrato_filtros = {}
            if cd.get('tipo_contrato_cliente_proveedor'):
                contrato_filtros['tipo_contrato_cliente_proveedor'] = cd['tipo_contrato_cliente_proveedor']
            if cd.get('tipo_contrato'):
                contrato_filtros['tipo_contrato'] = cd['tipo_contrato']
            if cd.get('arrendatario'):
                contrato_filtros['arrendatario'] = cd['arrendatario']
            if cd.get('local'):
                contrato_filtros['local'] = cd['local']
            if cd.get('modalidad_pago'):
                contrato_filtros['modalidad_pago'] = cd['modalidad_pago']
            polizas = list(obtener_polizas_criticas(
                fecha_referencia=fecha_actual,
                contrato_filtros=contrato_filtros or None,
            ))
            columnas = [
                ColumnaExportacion('Número de Póliza', ancho=22),
                ColumnaExportacion('Tipo', ancho=24),
                ColumnaExportacion('Contrato', ancho=22),
                ColumnaExportacion('Arrendatario', ancho=30),
                ColumnaExportacion('Fecha Inicio Vigencia', ancho=20, alineacion='center'),
                ColumnaExportacion('Fecha Fin Vigencia', ancho=20, alineacion='center'),
                ColumnaExportacion('Días Restantes', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Estado', ancho=24),
            ]
            registros = []
            for poliza in polizas:
                dias_restantes = None
                if poliza.fecha_vencimiento:
                    dias_restantes = (poliza.fecha_vencimiento - fecha_actual).days
                    estado_legible = poliza.obtener_estado_legible()
                else:
                    estado_legible = 'Sin fecha registrada'
                tercero = poliza.contrato.obtener_tercero()
                registros.append((
                    poliza.numero_poliza,
                    poliza.get_tipo_display(),
                    poliza.contrato.num_contrato,
                    tercero.razon_social if tercero else 'Sin tercero asignado',
                    _fecha_inicio_poliza(poliza),
                    poliza.fecha_vencimiento,
                    dias_restantes,
                    estado_legible,
                ))
            try:
                archivo = generar_excel_corporativo(nombre_hoja='Pólizas Críticas', columnas=columnas, registros=registros)
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportaciones')
            return _respuesta_archivo_excel(archivo, 'alertas_polizas_criticas')
    else:
        form = FiltroReportesAlertasForm()

    return render(request, 'gestion/exportaciones/filtros_reporte.html', {
        'form': form,
        'titulo': 'Alertas de Pólizas Críticas',
        'descripcion': 'Aplique filtros para exportar pólizas vencidas o próximas a vencer de contratos vigentes.',
        'url_name': 'gestion:exportar_alertas_polizas',
    })


@login_required_custom
def exportar_alertas_preaviso(request):
    from gestion.forms import FiltroReportesAlertasForm
    from gestion.utils_otrosi import get_otrosi_vigente

    fecha_actual = timezone.now().date()

    if request.method == 'POST':
        form = FiltroReportesAlertasForm(request.POST)
        if form.is_valid():
            contratos = list(obtener_alertas_preaviso(
                fecha_referencia=fecha_actual,
                contratos_qs=_construir_qs_contratos_filtrado(form),
            ))
            columnas = [
                ColumnaExportacion('Número de Contrato', ancho=22),
                ColumnaExportacion('Arrendatario', ancho=30),
                ColumnaExportacion('Local', ancho=26),
                ColumnaExportacion('Fecha Final', ancho=18, alineacion='center'),
                ColumnaExportacion('Días Preaviso Configurados', ancho=24, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Límite Preaviso', ancho=22, alineacion='center'),
                ColumnaExportacion('Canon Vigente', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Otrosí Modificador', ancho=25),
            ]
            registros = []
            for contrato in contratos:
                fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_actual)
                ov = get_otrosi_vigente(contrato, fecha_actual)
                otrosi_numero = (getattr(ov, 'numero_otrosi', None) or getattr(ov, 'numero_renovacion', None)) if ov else None
                dias_preaviso = contrato.dias_preaviso_no_renovacion or 0
                fecha_limite = (fecha_final_actual - timedelta(days=dias_preaviso)) if fecha_final_actual else None
                tercero = contrato.obtener_tercero()
                canon = obtener_canon_vigente(contrato, fecha_actual)
                registros.append((
                    contrato.num_contrato,
                    tercero.razon_social if tercero else 'Sin tercero asignado',
                    contrato.local.nombre_comercial_stand if contrato.local else '-',
                    fecha_final_actual,
                    dias_preaviso,
                    fecha_limite,
                    float(canon) if canon else None,
                    otrosi_numero or 'Contrato Original',
                ))
            try:
                archivo = generar_excel_corporativo(nombre_hoja='Preaviso Renovación', columnas=columnas, registros=registros)
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportaciones')
            return _respuesta_archivo_excel(archivo, 'alertas_preaviso')
    else:
        form = FiltroReportesAlertasForm()

    return render(request, 'gestion/exportaciones/filtros_reporte.html', {
        'form': form,
        'titulo': 'Alertas de Renovación (Preaviso)',
        'descripcion': 'Aplique filtros para exportar los contratos que ya entraron en ventana de preaviso de no renovación.',
        'url_name': 'gestion:exportar_alertas_preaviso',
    })


@login_required_custom
def exportar_estado_preavisos(request):
    from gestion.forms import FiltroReportesAlertasForm

    fecha_actual = timezone.now().date()

    if request.method != 'POST':
        return render(request, 'gestion/exportaciones/filtros_reporte.html', {
            'form': FiltroReportesAlertasForm(),
            'titulo': 'Estado de Preavisos',
            'descripcion': 'Panorama completo de todos los contratos vigentes: estado de preaviso, fechas y días.',
            'url_name': 'gestion:exportar_estado_preavisos',
        })

    form = FiltroReportesAlertasForm(request.POST)
    if not form.is_valid():
        return render(request, 'gestion/exportaciones/filtros_reporte.html', {
            'form': form,
            'titulo': 'Estado de Preavisos',
            'descripcion': 'Panorama completo de todos los contratos vigentes: estado de preaviso, fechas y días.',
            'url_name': 'gestion:exportar_estado_preavisos',
        })

    contratos_qs = _construir_qs_contratos_filtrado(form).order_by('num_contrato')

    ORDEN_ESTADO = {
        'EN VENTANA': 0,
        'PRÓXIMO': 1,
        'EXPIRADO': 2,
        'PRÓRROGA AUTOMÁTICA': 3,
        'SIN DÍAS CONFIGURADOS': 4,
        'SIN FECHA FINAL': 5,
    }

    filas = []
    for contrato in contratos_qs:
        try:
            fecha_final = _obtener_fecha_final_contrato(contrato, fecha_actual)
            tercero = contrato.obtener_tercero()
            nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
            local_nombre = contrato.local.nombre_comercial_stand if contrato.local else '-'
            tipo_cp = contrato.get_tipo_contrato_cliente_proveedor_display() if hasattr(contrato, 'get_tipo_contrato_cliente_proveedor_display') else (contrato.tipo_contrato_cliente_proveedor or '-')
            canon_val = obtener_canon_vigente(contrato, fecha_actual)
            canon_val = float(canon_val) if canon_val else None

            if not fecha_final:
                filas.append({
                    'orden': ORDEN_ESTADO['SIN FECHA FINAL'],
                    'fila': (contrato.num_contrato, nombre_tercero, local_nombre, tipo_cp,
                             'SIN FECHA FINAL', None, 0, None, None, None, canon_val),
                })
                continue

            dias_para_vencer = (fecha_final - fecha_actual).days
            dias_preaviso = contrato.dias_preaviso_no_renovacion or 0

            if contrato.prorroga_automatica:
                filas.append({
                    'orden': ORDEN_ESTADO['PRÓRROGA AUTOMÁTICA'],
                    'fila': (contrato.num_contrato, nombre_tercero, local_nombre, tipo_cp,
                             'PRÓRROGA AUTOMÁTICA', fecha_final, dias_preaviso, None, None, dias_para_vencer, canon_val),
                })
                continue

            if fecha_final < fecha_actual:
                filas.append({
                    'orden': ORDEN_ESTADO['EXPIRADO'],
                    'fila': (contrato.num_contrato, nombre_tercero, local_nombre, tipo_cp,
                             'EXPIRADO', fecha_final, dias_preaviso, None, None, dias_para_vencer, canon_val),
                })
                continue

            if dias_preaviso <= 0:
                filas.append({
                    'orden': ORDEN_ESTADO['SIN DÍAS CONFIGURADOS'],
                    'fila': (contrato.num_contrato, nombre_tercero, local_nombre, tipo_cp,
                             'SIN DÍAS CONFIGURADOS', fecha_final, 0, None, None, dias_para_vencer, canon_val),
                })
                continue

            fecha_inicio_preaviso = fecha_final - timedelta(days=dias_preaviso)
            dias_desde_inicio = (fecha_actual - fecha_inicio_preaviso).days  # positivo = en ventana

            if fecha_actual >= fecha_inicio_preaviso:
                estado = 'EN VENTANA'
                orden = ORDEN_ESTADO['EN VENTANA']
            else:
                estado = 'PRÓXIMO'
                orden = ORDEN_ESTADO['PRÓXIMO']

            filas.append({
                'orden': orden,
                'fecha_inicio_preaviso': fecha_inicio_preaviso,
                'fecha_final': fecha_final,
                'fila': (contrato.num_contrato, nombre_tercero, local_nombre, tipo_cp,
                         estado, fecha_final, dias_preaviso, fecha_inicio_preaviso,
                         dias_desde_inicio, dias_para_vencer, canon_val),
            })
        except Exception:
            continue

    # Ordenar: primero por estado (EN VENTANA → PRÓXIMO → …), luego por fecha
    filas.sort(key=lambda x: (
        x['orden'],
        x.get('fecha_inicio_preaviso') or x.get('fecha_final') or fecha_actual,
    ))

    registros = [f['fila'] for f in filas]

    columnas = [
        ColumnaExportacion('N° Contrato', ancho=30),
        ColumnaExportacion('Tercero', ancho=32),
        ColumnaExportacion('Local', ancho=26),
        ColumnaExportacion('Tipo', ancho=14, alineacion='center'),
        ColumnaExportacion('Estado Preaviso', ancho=24, alineacion='center'),
        ColumnaExportacion('Fecha Final Contrato', ancho=22, alineacion='center'),
        ColumnaExportacion('Días Preaviso Config.', ancho=22, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Fecha Inicio Preaviso', ancho=22, alineacion='center'),
        ColumnaExportacion('Días en Ventana / Días para Entrar', ancho=34, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Días para Vencer', ancho=18, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Canon Vigente', ancho=20, es_numerica=True, alineacion='right'),
    ]

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Estado Preavisos',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'estado_preavisos')


@login_required_custom
def exportar_alertas_polizas_requeridas(request):
    from gestion.forms import FiltroReportesAlertasForm

    fecha_actual = timezone.now().date()

    if request.method == 'POST':
        form = FiltroReportesAlertasForm(request.POST)
        if form.is_valid():
            alertas = obtener_alertas_polizas_requeridas_no_aportadas(
                fecha_referencia=fecha_actual,
                contratos_qs=_construir_qs_contratos_filtrado(form),
            )
            columnas = [
                ColumnaExportacion('Número de Contrato', ancho=22),
                ColumnaExportacion('Arrendatario', ancho=30),
                ColumnaExportacion('Local', ancho=26),
                ColumnaExportacion('Tipo de Póliza Requerida', ancho=30),
                ColumnaExportacion('Nombre Póliza', ancho=28),
                ColumnaExportacion('Valor Requerido', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Fin Requerida', ancho=22, alineacion='center'),
                ColumnaExportacion('Tiene Póliza', ancho=16),
                ColumnaExportacion('Estado', ancho=20),
                ColumnaExportacion('Otrosí Modificador', ancho=25),
            ]
            registros = []
            for alerta in alertas:
                tercero = alerta.contrato.obtener_tercero()
                registros.append((
                    alerta.contrato.num_contrato,
                    tercero.razon_social if tercero else 'Sin tercero asignado',
                    alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-',
                    alerta.tipo_poliza,
                    alerta.nombre_poliza,
                    int(round(float(alerta.valor_requerido))) if alerta.valor_requerido else None,
                    alerta.fecha_fin_requerida,
                    'Sí' if alerta.tiene_poliza else 'No',
                    'Sin póliza' if not alerta.tiene_poliza else 'Póliza vencida',
                    alerta.otrosi_modificador or 'Contrato Original',
                ))
            try:
                archivo = generar_excel_corporativo(nombre_hoja='Pólizas Requeridas No Aportadas', columnas=columnas, registros=registros)
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportaciones')
            return _respuesta_archivo_excel(archivo, 'alertas_polizas_requeridas_no_aportadas')
    else:
        form = FiltroReportesAlertasForm()

    return render(request, 'gestion/exportaciones/filtros_reporte.html', {
        'form': form,
        'titulo': 'Alertas de Pólizas Requeridas No Aportadas',
        'descripcion': 'Aplique filtros para exportar contratos con pólizas requeridas sin aportar o vencidas.',
        'url_name': 'gestion:exportar_alertas_polizas_requeridas',
    })


@login_required_custom
def exportar_alertas_terminacion(request):
    from gestion.forms import FiltroReportesAlertasForm

    fecha_actual = timezone.now().date()

    if request.method == 'POST':
        form = FiltroReportesAlertasForm(request.POST)
        if form.is_valid():
            alertas = obtener_alertas_terminacion_anticipada(
                fecha_referencia=fecha_actual,
                contratos_qs=_construir_qs_contratos_filtrado(form),
            )
            columnas = [
                ColumnaExportacion('Número de Contrato', ancho=22),
                ColumnaExportacion('Arrendatario', ancho=30),
                ColumnaExportacion('Local', ancho=26),
                ColumnaExportacion('Fecha Final', ancho=18, alineacion='center'),
                ColumnaExportacion('Días Restantes', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Días Terminación Anticipada', ancho=28, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Límite Terminación', ancho=24, alineacion='center'),
                ColumnaExportacion('Canon Vigente', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Otrosí Modificador', ancho=25),
            ]
            registros = []
            for alerta in alertas:
                tercero = alerta.contrato.obtener_tercero()
                canon = obtener_canon_vigente(alerta.contrato, fecha_actual)
                registros.append((
                    alerta.contrato.num_contrato,
                    tercero.razon_social if tercero else 'Sin tercero asignado',
                    alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-',
                    alerta.fecha_final_actualizada,
                    alerta.dias_restantes,
                    alerta.dias_terminacion_anticipada,
                    alerta.fecha_limite_terminacion,
                    float(canon) if canon else None,
                    alerta.otrosi_modificador or 'Contrato Original',
                ))
            try:
                archivo = generar_excel_corporativo(nombre_hoja='Terminación Anticipada', columnas=columnas, registros=registros)
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportaciones')
            return _respuesta_archivo_excel(archivo, 'alertas_terminacion_anticipada')
    else:
        form = FiltroReportesAlertasForm()

    return render(request, 'gestion/exportaciones/filtros_reporte.html', {
        'form': form,
        'titulo': 'Alertas de Terminación Anticipada',
        'descripcion': 'Aplique filtros para exportar contratos dentro del período de terminación anticipada.',
        'url_name': 'gestion:exportar_alertas_terminacion',
    })


@login_required_custom
def exportar_terceros(request):
    """
    Genera el archivo Excel con todos los terceros registrados (arrendatarios y proveedores).
    Acepta parámetro GET ?tipo=ARRENDATARIO|PROVEEDOR para filtrar por tipo.
    """
    tipo = request.GET.get('tipo', '')
    terceros = Tercero.objects.all().order_by('tipo', 'razon_social')
    if tipo in ('ARRENDATARIO', 'PROVEEDOR'):
        terceros = terceros.filter(tipo=tipo)

    tipo_display = {'ARRENDATARIO': 'Arrendatarios', 'PROVEEDOR': 'Proveedores'}
    nombre_hoja = tipo_display.get(tipo, 'Terceros')

    columnas = [
        ColumnaExportacion('Tipo', ancho=18, alineacion='center'),
        ColumnaExportacion('NIT', ancho=22),
        ColumnaExportacion('Razón Social', ancho=38),
        ColumnaExportacion('Representante Legal', ancho=32),
        ColumnaExportacion('Supervisor Operativo', ancho=32),
        ColumnaExportacion('Email Supervisor', ancho=38),
    ]

    registros = [
        (
            t.get_tipo_display(),
            t.nit,
            t.razon_social,
            t.nombre_rep_legal,
            t.nombre_supervisor_op or '-',
            t.email_supervisor_op or '-',
        )
        for t in terceros
    ]

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja=nombre_hoja,
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    sufijo = f'_{tipo.lower()}' if tipo else ''
    return _respuesta_archivo_excel(archivo, f'terceros{sufijo}')


@login_required_custom
def exportar_locales(request):
    """
    Genera el archivo Excel con todos los locales registrados.
    """
    locales = Local.objects.all().order_by('nombre_comercial_stand')

    columnas = [
        ColumnaExportacion('Nombre Comercial / Stand', ancho=38),
        ColumnaExportacion('Ubicación', ancho=38),
        ColumnaExportacion('Área Total (m²)', ancho=20, alineacion='right'),
    ]

    registros = [
        (
            local.nombre_comercial_stand,
            local.ubicacion,
            str(local.total_area_m2) if local.total_area_m2 is not None else '-',
        )
        for local in locales
    ]

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Locales',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'locales')


@login_required_custom
def exportar_recobro_polizas(request):
    """
    Genera el archivo Excel con el estado de recobro de pólizas por contrato.
    Solo incluye contratos que exigen al menos una póliza.
    Filtros GET: tipo_contrato (CLIENTE/PROVEEDOR), tipo_poliza (rce/cumplimiento/arrendamiento/todo_riesgo/otra), recobro (si/no)
    """
    from django.db.models import Q
    from gestion.models import OtroSi, RenovacionAutomatica

    tipo_contrato = request.GET.get('tipo_contrato', '')
    tipo_poliza = request.GET.get('tipo_poliza', '')
    filtro_recobro = request.GET.get('recobro', '')

    # Si es GET sin filtros, mostrar formulario
    if request.method == 'GET' and not any([tipo_contrato, tipo_poliza, filtro_recobro]):
        context = {
            'titulo': 'Exportar Recobro de Pólizas',
            'descripcion': 'Reporte de contratos con pólizas requeridas y estado de recobro.',
        }
        return render(request, 'gestion/exportaciones/recobro_polizas.html', context)

    contratos = Contrato.objects.all().order_by('num_contrato')
    if tipo_contrato in ('CLIENTE', 'PROVEEDOR'):
        contratos = contratos.filter(tipo_contrato_cliente_proveedor=tipo_contrato)

    TIPOS_POLIZA = [
        ('rce', 'exige_poliza_rce', 'recobro_poliza_rce', 'RCE - Responsabilidad Civil',
         'nuevo_exige_poliza_rce', 'nuevo_recobro_poliza_rce'),
        ('cumplimiento', 'exige_poliza_cumplimiento', 'recobro_poliza_cumplimiento', 'Cumplimiento',
         'nuevo_exige_poliza_cumplimiento', 'nuevo_recobro_poliza_cumplimiento'),
        ('arrendamiento', 'exige_poliza_arrendamiento', 'recobro_poliza_arrendamiento', 'Póliza de Arrendamiento',
         'nuevo_exige_poliza_arrendamiento', 'nuevo_recobro_poliza_arrendamiento'),
        ('todo_riesgo', 'exige_poliza_todo_riesgo', 'recobro_poliza_todo_riesgo', 'Todo Riesgo',
         'nuevo_exige_poliza_todo_riesgo', 'nuevo_recobro_poliza_todo_riesgo'),
        ('otra', 'exige_poliza_otra_1', 'recobro_poliza_otra_1', 'Otras Pólizas',
         'nuevo_exige_poliza_otra_1', 'nuevo_recobro_poliza_otra_1'),
    ]

    if tipo_poliza:
        TIPOS_POLIZA = [t for t in TIPOS_POLIZA if t[0] == tipo_poliza]

    columnas = [
        ColumnaExportacion('N° Contrato', ancho=20),
        ColumnaExportacion('Tipo Contrato', ancho=16, alineacion='center'),
        ColumnaExportacion('Tercero', ancho=35),
        ColumnaExportacion('Local', ancho=28),
        ColumnaExportacion('Tipo Póliza', ancho=28),
        ColumnaExportacion('¿Exige Póliza?', ancho=16, alineacion='center'),
        ColumnaExportacion('¿Aplica Recobro?', ancho=18, alineacion='center'),
        ColumnaExportacion('Documento que lo define', ancho=28),
    ]

    registros = []
    for contrato in contratos:
        tercero = contrato.obtener_tercero()
        nombre_tercero = tercero.razon_social if tercero else 'Sin tercero'
        local_nombre = contrato.local.nombre_comercial_stand if contrato.local else '-'
        tipo_c_display = 'Cliente' if contrato.tipo_contrato_cliente_proveedor == 'CLIENTE' else 'Proveedor'

        for codigo, campo_exige, campo_recobro, label_tipo, campo_exige_doc, campo_recobro_doc in TIPOS_POLIZA:
            exige_efectivo = getattr(contrato, campo_exige, False) or False
            recobro_efectivo = getattr(contrato, campo_recobro, False) or False
            doc_origen = 'Contrato Base'

            # Check OtroSis (APROBADO) that modified this policy
            otrosi_mod = OtroSi.objects.filter(
                contrato=contrato,
                estado='APROBADO',
                modifica_polizas=True,
            ).exclude(**{campo_exige_doc: None}).order_by('fecha_aprobacion').last()

            if otrosi_mod:
                val_exige = getattr(otrosi_mod, campo_exige_doc, None)
                if val_exige is not None:
                    exige_efectivo = val_exige
                    recobro_efectivo = getattr(otrosi_mod, campo_recobro_doc, None) or False
                    doc_origen = f'Otro Sí #{otrosi_mod.numero_otrosi}'

            # Check RenovacionAutomatica (APROBADO) that modified this policy
            renov_mod = RenovacionAutomatica.objects.filter(
                contrato=contrato,
                estado='APROBADO',
                modifica_polizas=True,
            ).exclude(**{campo_exige_doc: None}).order_by('fecha_aprobacion').last()

            if renov_mod:
                val_exige = getattr(renov_mod, campo_exige_doc, None)
                if val_exige is not None:
                    use_renov = True
                    if otrosi_mod and otrosi_mod.fecha_aprobacion and renov_mod.fecha_aprobacion:
                        use_renov = renov_mod.fecha_aprobacion >= otrosi_mod.fecha_aprobacion
                    if use_renov:
                        exige_efectivo = val_exige
                        recobro_efectivo = getattr(renov_mod, campo_recobro_doc, None) or False
                        doc_origen = f'Renovación #{renov_mod.numero_renovacion}'

            if not exige_efectivo:
                continue

            aplica_recobro_str = 'Sí' if recobro_efectivo else 'No'

            if filtro_recobro == 'si' and not recobro_efectivo:
                continue
            if filtro_recobro == 'no' and recobro_efectivo:
                continue

            registros.append((
                contrato.num_contrato,
                tipo_c_display,
                nombre_tercero,
                local_nombre,
                label_tipo,
                'Sí',
                aplica_recobro_str,
                doc_origen,
            ))

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Recobro Pólizas',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'recobro_polizas')
