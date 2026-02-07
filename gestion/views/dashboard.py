from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from gestion.decorators import login_required_custom
from gestion.models import Contrato, Poliza
from gestion.services.alertas import (
    obtener_alertas_expiracion_contratos,
    obtener_alertas_ipc,
    obtener_alertas_salario_minimo,
    obtener_alertas_preaviso,
    obtener_alertas_polizas_requeridas_no_aportadas,
    obtener_alertas_terminacion_anticipada,
    obtener_alertas_renovacion_automatica,
    obtener_polizas_criticas,
    AlertaPolizaRequerida,
)
from gestion.services.exportes import (
    ColumnaExportacion,
    ExportacionVaciaError,
    generar_excel_corporativo,
)
from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
from .utils import _estado_vigente_contrato, _respuesta_archivo_excel


@login_required_custom
def dashboard(request):
    """
    Dashboard principal con alertas avanzadas para la gestión de contratos
    """
    fecha_actual = timezone.now().date()
    tipo_filtro = request.GET.get('tipo_alerta', '')  # Filtro para alertas: CLIENTE, PROVEEDOR o vacío (todos)
    total_contratos = Contrato.objects.count()

    todos_los_contratos = Contrato.objects.prefetch_related('otrosi')
    contratos_vigentes = 0
    contratos_vencidos = 0
    contratos_vigentes_list = []

    for contrato in todos_los_contratos:
        if _estado_vigente_contrato(contrato, fecha_actual):
            contratos_vigentes += 1
            contratos_vigentes_list.append(contrato)
        else:
            contratos_vencidos += 1

    total_polizas = Poliza.objects.count()

    contratos_fijos = 0
    contratos_variables = 0
    contratos_hibridos = 0

    for contrato in contratos_vigentes_list:
        # Usar efecto cadena para obtener modalidad vigente hasta fecha_actual
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_modalidad_pago', fecha_actual
        )
        if otrosi_modificador and otrosi_modificador.nueva_modalidad_pago:
            modalidad_actual = otrosi_modificador.nueva_modalidad_pago
        else:
            modalidad_actual = contrato.modalidad_pago
        
        if modalidad_actual == 'Fijo':
            contratos_fijos += 1
        elif modalidad_actual == 'Variable Puro':
            contratos_variables += 1
        elif modalidad_actual == 'Hibrido (Min Garantizado)':
            contratos_hibridos += 1
    
    contratos_por_vencer_list = obtener_alertas_expiracion_contratos(fecha_referencia=fecha_actual, ventana_dias=90)
    contratos_por_vencer_con_fecha = []
    for contrato in contratos_por_vencer_list:
        # Filtrar por tipo de contrato si se especifica
        if tipo_filtro and contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        # Usar efecto cadena para obtener fecha final vigente hasta fecha_actual
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_final_actualizada', fecha_actual
        )
        if otrosi_modificador and otrosi_modificador.nueva_fecha_final_actualizada:
            fecha_final_actual = otrosi_modificador.nueva_fecha_final_actualizada
        else:
            fecha_final_actual = contrato.fecha_final_actualizada or contrato.fecha_final_inicial
        contratos_por_vencer_con_fecha.append({
            'contrato': contrato,
            'fecha_final_actualizada': fecha_final_actual,
        })
    total_alertas_vencimiento = len(contratos_por_vencer_con_fecha)
    
    polizas_criticas_list = obtener_polizas_criticas(fecha_referencia=fecha_actual)
    polizas_criticas = []
    for poliza in polizas_criticas_list:
        # Filtrar por tipo de contrato si se especifica
        if tipo_filtro and poliza.contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        polizas_criticas.append(poliza)
    total_polizas_criticas = len(polizas_criticas)
    
    alertas_preaviso_list = obtener_alertas_preaviso(fecha_referencia=fecha_actual)
    alertas_preaviso_con_fecha = []
    for contrato in alertas_preaviso_list:
        # Filtrar por tipo de contrato si se especifica
        if tipo_filtro and contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        # Usar efecto cadena para obtener fecha final vigente hasta fecha_actual
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_final_actualizada', fecha_actual
        )
        if otrosi_modificador and otrosi_modificador.nueva_fecha_final_actualizada:
            fecha_final_actual = otrosi_modificador.nueva_fecha_final_actualizada
        else:
            fecha_final_actual = contrato.fecha_final_actualizada or contrato.fecha_final_inicial
        alertas_preaviso_con_fecha.append({
            'contrato': contrato,
            'fecha_final_actualizada': fecha_final_actual,
        })
    total_alertas_preaviso = len(alertas_preaviso_con_fecha)
    
    alertas_ipc_list = obtener_alertas_ipc(fecha_referencia=fecha_actual, tipo_contrato_cp=tipo_filtro if tipo_filtro else None)
    alertas_ipc = []
    for alerta in alertas_ipc_list:
        alertas_ipc.append(alerta)
    total_alertas_ipc = len(alertas_ipc)
    
    alertas_salario_minimo_list = obtener_alertas_salario_minimo(fecha_referencia=fecha_actual, tipo_contrato_cp=tipo_filtro if tipo_filtro else None)
    alertas_salario_minimo = []
    for alerta in alertas_salario_minimo_list:
        alertas_salario_minimo.append(alerta)
    total_alertas_salario_minimo = len(alertas_salario_minimo)
    
    # Combinar alertas de IPC y Salario Mínimo para mostrar en la misma sección
    alertas_ajuste_facturacion = list(alertas_ipc) + list(alertas_salario_minimo)
    # Ordenar por prioridad (danger primero, luego warning, luego success) y luego por meses restantes
    alertas_ajuste_facturacion.sort(key=lambda alerta: (
        0 if alerta.color_alerta == 'danger'
        else 1 if alerta.color_alerta == 'warning'
        else 2,
        alerta.meses_restantes,
        alerta.contrato.num_contrato,
    ))
    total_alertas_ajuste_facturacion = len(alertas_ajuste_facturacion)
    
    alertas_polizas_requeridas_list = obtener_alertas_polizas_requeridas_no_aportadas(fecha_referencia=fecha_actual)
    alertas_polizas_requeridas = []
    for alerta in alertas_polizas_requeridas_list:
        # Filtrar por tipo de contrato si se especifica
        if tipo_filtro and alerta.contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        alertas_polizas_requeridas.append(alerta)
    total_alertas_polizas_requeridas = len(alertas_polizas_requeridas)
    
    alertas_terminacion_list = obtener_alertas_terminacion_anticipada(fecha_referencia=fecha_actual)
    alertas_terminacion = []
    for alerta in alertas_terminacion_list:
        # Filtrar por tipo de contrato si se especifica
        if tipo_filtro and alerta.contrato.tipo_contrato_cliente_proveedor != tipo_filtro:
            continue
        alertas_terminacion.append(alerta)
    total_alertas_terminacion = len(alertas_terminacion)
    
    alertas_renovacion_automatica = obtener_alertas_renovacion_automatica(fecha_referencia=fecha_actual)
    total_alertas_renovacion_automatica = len(alertas_renovacion_automatica)
    
    context = {
        'fecha_actual': fecha_actual,
        'tipo_filtro': tipo_filtro,
        'total_contratos': total_contratos,
        'contratos_vigentes': contratos_vigentes,
        'contratos_vencidos': contratos_vencidos,
        'total_polizas': total_polizas,
        'contratos_fijos': contratos_fijos,
        'contratos_variables': contratos_variables,
        'contratos_hibridos': contratos_hibridos,
        'contratos_por_vencer': contratos_por_vencer_con_fecha,
        'total_alertas_vencimiento': total_alertas_vencimiento,
        'polizas_criticas': polizas_criticas,
        'total_polizas_criticas': total_polizas_criticas,
        'hay_polizas_con_colchon': any(
            getattr(p, 'tiene_colchon', False) for p in polizas_criticas
        ),
        'alertas_preaviso_renovacion': alertas_preaviso_con_fecha,
        'total_alertas_preaviso': total_alertas_preaviso,
        'alertas_ipc': alertas_ipc,
        'total_alertas_ipc': total_alertas_ipc,
        'alertas_salario_minimo': alertas_salario_minimo,
        'total_alertas_salario_minimo': total_alertas_salario_minimo,
        'alertas_ajuste_facturacion': alertas_ajuste_facturacion,
        'total_alertas_ajuste_facturacion': total_alertas_ajuste_facturacion,
        'alertas_polizas_requeridas': alertas_polizas_requeridas,
        'total_alertas_polizas_requeridas': total_alertas_polizas_requeridas,
        'alertas_terminacion': alertas_terminacion,
        'total_alertas_terminacion': total_alertas_terminacion,
        'alertas_renovacion_automatica': alertas_renovacion_automatica,
        'total_alertas_renovacion_automatica': total_alertas_renovacion_automatica,
    }
    
    return render(request, 'gestion/dashboard/index.html', context)


@login_required_custom
def exportaciones(request):
    """
    Centro de exportaciones de reportes del sistema.
    Permite seleccionar el informe a descargar.
    """
    fecha_actual = timezone.now().date()
    contratos_por_vencer = obtener_alertas_expiracion_contratos(fecha_referencia=fecha_actual, ventana_dias=90)
    polizas_criticas = obtener_polizas_criticas(fecha_referencia=fecha_actual)
    alertas_preaviso = obtener_alertas_preaviso(fecha_referencia=fecha_actual)
    alertas_ipc = obtener_alertas_ipc(fecha_referencia=fecha_actual)
    alertas_salario_minimo = obtener_alertas_salario_minimo(fecha_referencia=fecha_actual)
    alertas_polizas_requeridas = obtener_alertas_polizas_requeridas_no_aportadas(fecha_referencia=fecha_actual)
    alertas_terminacion = obtener_alertas_terminacion_anticipada(fecha_referencia=fecha_actual)

    total_contratos = Contrato.objects.count()
    
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
            'total_registros': len(contratos_por_vencer),
            'url_name': 'gestion:exportar_alertas_vencimiento',
        },
        {
            'codigo': 'alertas_polizas',
            'nombre': 'Alertas de Pólizas Críticas',
            'descripcion': 'Pólizas vencidas, próximas a vencer o sin aportar.',
            'total_registros': len(polizas_criticas),
            'url_name': 'gestion:exportar_alertas_polizas',
        },
        {
            'codigo': 'alertas_preaviso',
            'nombre': 'Alertas de Renovación (Preaviso)',
            'descripcion': 'Contratos que requieren envío de preaviso de no renovación.',
            'total_registros': len(alertas_preaviso),
            'url_name': 'gestion:exportar_alertas_preaviso',
        },
        {
            'codigo': 'alertas_ipc',
            'nombre': 'Alertas de Ajuste de IPC',
            'descripcion': 'Contratos con ajustes de canon próximos por índice IPC.',
            'total_registros': len(alertas_ipc),
            'url_name': 'gestion:exportar_alertas_ipc',
        },
        {
            'codigo': 'alertas_salario_minimo',
            'nombre': 'Alertas de Ajuste de Salario Mínimo',
            'descripcion': 'Contratos con ajustes de canon próximos por Salario Mínimo.',
            'total_registros': len(alertas_salario_minimo),
            'url_name': 'gestion:exportar_alertas_salario_minimo',
        },
        {
            'codigo': 'alertas_polizas_requeridas',
            'nombre': 'Alertas de Pólizas Requeridas No Aportadas',
            'descripcion': 'Contratos con pólizas requeridas que no han sido aportadas o están vencidas.',
            'total_registros': len(alertas_polizas_requeridas),
            'url_name': 'gestion:exportar_alertas_polizas_requeridas',
        },
        {
            'codigo': 'alertas_terminacion',
            'nombre': 'Alertas de Terminación Anticipada',
            'descripcion': 'Contratos dentro del período de terminación anticipada.',
            'total_registros': len(alertas_terminacion),
            'url_name': 'gestion:exportar_alertas_terminacion',
        },
    ]

    context = {
        'fecha_actual': fecha_actual,
        'reportes': reportes,
    }
    return render(request, 'gestion/exportaciones/index.html', context)


@login_required_custom
def exportar_alertas_ipc(request):
    """
    Genera el archivo Excel con las alertas de IPC vigentes.
    """
    from gestion.forms import FiltroExportacionAlertasForm
    
    tipo_contrato_cp = request.GET.get('tipo_contrato_cp', '') or request.POST.get('tipo_contrato_cliente_proveedor', '')
    
    # Si es GET sin parámetro tipo_contrato_cp, mostrar formulario de selección
    if request.method == 'GET' and 'tipo_contrato_cp' not in request.GET:
        form = FiltroExportacionAlertasForm()
        context = {
            'form': form,
            'titulo': 'Exportar Alertas de IPC',
            'descripcion': 'Seleccione el tipo de contrato para exportar las alertas de ajuste de IPC.',
            'url_exportacion': 'gestion:exportar_alertas_ipc',
        }
        return render(request, 'gestion/exportaciones/seleccionar_tipo.html', context)
    
    alertas = obtener_alertas_ipc(tipo_contrato_cp=tipo_contrato_cp if tipo_contrato_cp else None)

    try:
        columnas = [
            ColumnaExportacion('Número de Contrato', ancho=22),
            ColumnaExportacion('Tercero', ancho=28),
            ColumnaExportacion('Local', ancho=26),
            ColumnaExportacion('Mes de Ajuste', ancho=18, alineacion='center'),
            ColumnaExportacion('Condición IPC', ancho=26),
            ColumnaExportacion('Meses Restantes', ancho=18, es_numerica=True, alineacion='right'),
            ColumnaExportacion('Severidad', ancho=22),
            ColumnaExportacion('Otrosí Modificador', ancho=25),
        ]

        severidades_legibles = {
            'danger': 'Crítica (0-1 mes)',
            'warning': 'Moderada (2 meses)',
            'success': 'Preventiva (3+ meses)',
        }

        registros = []
        for alerta in alertas:
            tercero = alerta.contrato.obtener_tercero()
            nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
            local_nombre = alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-'
            registros.append((
                alerta.contrato.num_contrato,
                nombre_tercero,
                local_nombre,
                alerta.mes_ajuste,
                alerta.condicion_ipc,
                int(alerta.meses_restantes),
                severidades_legibles.get(alerta.color_alerta, alerta.color_alerta),
                alerta.otrosi_modificador or 'Contrato Original',
            ))

        archivo = generar_excel_corporativo(
            nombre_hoja='Alertas IPC',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'alertas_ipc')


@login_required_custom
def exportar_alertas_salario_minimo(request):
    """
    Genera el archivo Excel con las alertas de Salario Mínimo vigentes.
    """
    from gestion.forms import FiltroExportacionAlertasForm
    
    tipo_contrato_cp = request.GET.get('tipo_contrato_cp', '') or request.POST.get('tipo_contrato_cliente_proveedor', '')
    
    # Si es GET sin parámetro tipo_contrato_cp, mostrar formulario de selección
    if request.method == 'GET' and 'tipo_contrato_cp' not in request.GET:
        form = FiltroExportacionAlertasForm()
        context = {
            'form': form,
            'titulo': 'Exportar Alertas de Salario Mínimo',
            'descripcion': 'Seleccione el tipo de contrato para exportar las alertas de ajuste de Salario Mínimo.',
            'url_exportacion': 'gestion:exportar_alertas_salario_minimo',
        }
        return render(request, 'gestion/exportaciones/seleccionar_tipo.html', context)
    
    try:
        alertas = obtener_alertas_salario_minimo(tipo_contrato_cp=tipo_contrato_cp if tipo_contrato_cp else None)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener alertas de salario mínimo: {str(e)}", exc_info=True)
        messages.error(request, 'Error al obtener las alertas de Salario Mínimo. Por favor, intente nuevamente.')
        return redirect('gestion:exportaciones')

    if not alertas:
        messages.warning(request, 'No hay alertas de Salario Mínimo para exportar.')
        return redirect('gestion:exportaciones')

    try:
        columnas = [
            ColumnaExportacion('Número de Contrato', ancho=22),
            ColumnaExportacion('Tercero', ancho=28),
            ColumnaExportacion('Local', ancho=26),
            ColumnaExportacion('Mes de Ajuste', ancho=18, alineacion='center'),
            ColumnaExportacion('Condición Salario Mínimo', ancho=30),
            ColumnaExportacion('Meses Restantes', ancho=18, es_numerica=True, alineacion='right'),
            ColumnaExportacion('Severidad', ancho=22),
            ColumnaExportacion('Otrosí Modificador', ancho=25),
        ]

        severidades_legibles = {
            'danger': 'Crítica (0-1 mes)',
            'warning': 'Moderada (2 meses)',
            'success': 'Preventiva (3+ meses)',
        }

        registros = []
        for alerta in alertas:
            try:
                tercero = alerta.contrato.obtener_tercero()
                nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
                local_nombre = alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-'
                mes_ajuste = alerta.mes_ajuste if alerta.mes_ajuste else '-'
                condicion_sm = alerta.condicion_salario_minimo if alerta.condicion_salario_minimo else '-'
                meses_restantes_valor = int(alerta.meses_restantes) if alerta.meses_restantes is not None else 0
                severidad = severidades_legibles.get(alerta.color_alerta, alerta.color_alerta) if alerta.color_alerta else 'N/A'
                otrosi_mod = alerta.otrosi_modificador if alerta.otrosi_modificador else 'Contrato Original'
                
                registros.append((
                    alerta.contrato.num_contrato,
                    nombre_tercero,
                    local_nombre,
                    mes_ajuste,
                    condicion_sm,
                    meses_restantes_valor,
                    severidad,
                    otrosi_mod,
                ))
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error al procesar alerta de salario mínimo para contrato {alerta.contrato.num_contrato}: {str(e)}", exc_info=True)
                continue

        if not registros:
            messages.warning(request, 'No se pudieron procesar las alertas de Salario Mínimo para exportar.')
            return redirect('gestion:exportaciones')

        archivo = generar_excel_corporativo(
            nombre_hoja='Alertas Salario Mínimo',
            columnas=columnas,
            registros=registros,
        )

    except ExportacionVaciaError:
        messages.warning(request, 'No hay alertas de Salario Mínimo para exportar.')
        return redirect('gestion:exportaciones')
    except ValueError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error de validación al exportar alertas de salario mínimo: {str(e)}", exc_info=True)
        messages.error(request, f'Error de validación al generar el archivo Excel: {str(e)}. Por favor, verifique los datos.')
        return redirect('gestion:exportaciones')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error al exportar alertas de salario mínimo: {str(e)}", exc_info=True)
        messages.error(request, f'Error al generar el archivo Excel: {str(e)}. Por favor, intente nuevamente o contacte al administrador.')
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'alertas_salario_minimo')


@login_required_custom
def exportar_alertas_vencimiento(request):
    from gestion.forms import FiltroExportacionAlertasForm
    
    fecha_actual = timezone.now().date()
    tipo_contrato_cp = request.GET.get('tipo_contrato_cp', '') or request.POST.get('tipo_contrato_cliente_proveedor', '')
    
    # Si es GET sin parámetro tipo_contrato_cp, mostrar formulario de selección
    if request.method == 'GET' and 'tipo_contrato_cp' not in request.GET:
        form = FiltroExportacionAlertasForm()
        context = {
            'form': form,
            'titulo': 'Exportar Alertas de Vencimiento',
            'descripcion': 'Seleccione el tipo de contrato para exportar las alertas de vencimiento de contratos.',
            'url_exportacion': 'gestion:exportar_alertas_vencimiento',
        }
        return render(request, 'gestion/exportaciones/seleccionar_tipo.html', context)
    
    contratos = list(obtener_alertas_expiracion_contratos(
        fecha_referencia=fecha_actual,
        ventana_dias=90,
        tipo_contrato_cp=tipo_contrato_cp if tipo_contrato_cp else None
    ))

    if not contratos:
        messages.warning(request, 'No hay contratos por vencer en la ventana configurada.')
        return redirect('gestion:exportaciones')

    columnas = [
        ColumnaExportacion('Número de Contrato', ancho=22),
        ColumnaExportacion('Arrendatario', ancho=30),
        ColumnaExportacion('Local', ancho=26),
        ColumnaExportacion('Fecha Final', ancho=18, alineacion='center'),
        ColumnaExportacion('Días Restantes', ancho=18, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Modalidad', ancho=20),
        ColumnaExportacion('Otrosí Modificador', ancho=25),
    ]

    registros = []
    for contrato in contratos:
        # Usar efecto cadena para obtener fecha final vigente hasta fecha_actual
        otrosi_modificador_fecha = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_final_actualizada', fecha_actual
        )
        if otrosi_modificador_fecha and otrosi_modificador_fecha.nueva_fecha_final_actualizada:
            fecha_final_actual = otrosi_modificador_fecha.nueva_fecha_final_actualizada
            otrosi_numero = otrosi_modificador_fecha.numero_otrosi
        else:
            fecha_final_actual = contrato.fecha_final_actualizada or contrato.fecha_final_inicial
            otrosi_numero = None
        
        # Usar efecto cadena para obtener modalidad vigente hasta fecha_actual
        otrosi_modificador_modalidad = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_modalidad_pago', fecha_actual
        )
        if otrosi_modificador_modalidad and otrosi_modificador_modalidad.nueva_modalidad_pago:
            modalidad_actual = otrosi_modificador_modalidad.nueva_modalidad_pago
        else:
            modalidad_actual = contrato.modalidad_pago or 'Sin especificar'
        
        dias_restantes = None
        if fecha_final_actual:
            dias_restantes = (fecha_final_actual - fecha_actual).days

        tercero = contrato.obtener_tercero()
        nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
        local_nombre = contrato.local.nombre_comercial_stand if contrato.local else '-'
        registros.append(
            (
                contrato.num_contrato,
                nombre_tercero,
                local_nombre,
                fecha_final_actual,
                dias_restantes,
                modalidad_actual,
                otrosi_numero or 'Contrato Original',
            )
        )

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Contratos por Vencer',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'alertas_vencimiento_contratos')


@login_required_custom
def exportar_alertas_polizas(request):
    from gestion.forms import FiltroExportacionAlertasForm
    
    fecha_actual = timezone.now().date()
    tipo_contrato_cp = request.GET.get('tipo_contrato_cp', '') or request.POST.get('tipo_contrato_cliente_proveedor', '')
    
    # Si es GET sin parámetro tipo_contrato_cp, mostrar formulario de selección
    if request.method == 'GET' and 'tipo_contrato_cp' not in request.GET:
        form = FiltroExportacionAlertasForm()
        context = {
            'form': form,
            'titulo': 'Exportar Alertas de Pólizas Críticas',
            'descripcion': 'Seleccione el tipo de contrato para exportar las alertas de pólizas críticas.',
            'url_exportacion': 'gestion:exportar_alertas_polizas',
        }
        return render(request, 'gestion/exportaciones/seleccionar_tipo.html', context)
    
    polizas = list(obtener_polizas_criticas(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_contrato_cp if tipo_contrato_cp else None
    ))

    if not polizas:
        messages.warning(request, 'No hay pólizas críticas para exportar.')
        return redirect('gestion:exportaciones')

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

    TIPO_A_CAMPO_FECHA_INICIO = {
        'RCE - Responsabilidad Civil': ('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce'),
        'Cumplimiento': ('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento'),
        'Poliza de Arrendamiento': ('nuevo_fecha_inicio_vigencia_arrendamiento', 'fecha_inicio_vigencia_arrendamiento'),
        'Arrendamiento': ('nuevo_fecha_inicio_vigencia_todo_riesgo', 'fecha_inicio_vigencia_todo_riesgo'),
        'Otra': ('nuevo_fecha_inicio_vigencia_otra_1', 'fecha_inicio_vigencia_otra_1'),
    }

    def _obtener_fecha_inicio_poliza(p):
        if p.fecha_inicio_vigencia:
            return p.fecha_inicio_vigencia
        campo_otrosi, campo_contrato = TIPO_A_CAMPO_FECHA_INICIO.get(p.tipo, (None, None))
        if p.otrosi and campo_otrosi:
            valor = getattr(p.otrosi, campo_otrosi, None)
            if valor:
                return valor
        if p.renovacion_automatica and campo_otrosi:
            valor = getattr(p.renovacion_automatica, campo_otrosi, None)
            if valor:
                return valor
        if campo_contrato:
            valor = getattr(p.contrato, campo_contrato, None)
            if valor:
                return valor
        return p.contrato.fecha_inicial_contrato

    registros = []
    for poliza in polizas:
        dias_restantes = None
        if poliza.fecha_vencimiento:
            dias_restantes = (poliza.fecha_vencimiento - fecha_actual).days
            estado_legible = poliza.obtener_estado_legible()
        else:
            estado_legible = 'Sin fecha registrada'

        fecha_inicio = _obtener_fecha_inicio_poliza(poliza)

        tercero = poliza.contrato.obtener_tercero()
        nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
        registros.append(
            (
                poliza.numero_poliza,
                poliza.get_tipo_display(),
                poliza.contrato.num_contrato,
                nombre_tercero,
                fecha_inicio,
                poliza.fecha_vencimiento,
                dias_restantes,
                estado_legible,
            )
        )

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Pólizas Críticas',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'alertas_polizas_criticas')


@login_required_custom
def exportar_alertas_preaviso(request):
    from gestion.forms import FiltroExportacionAlertasForm
    
    fecha_actual = timezone.now().date()
    tipo_contrato_cp = request.GET.get('tipo_contrato_cp', '') or request.POST.get('tipo_contrato_cliente_proveedor', '')
    
    # Si es GET sin parámetro tipo_contrato_cp, mostrar formulario de selección
    if request.method == 'GET' and 'tipo_contrato_cp' not in request.GET:
        form = FiltroExportacionAlertasForm()
        context = {
            'form': form,
            'titulo': 'Exportar Alertas de Preaviso',
            'descripcion': 'Seleccione el tipo de contrato para exportar las alertas de preaviso de renovación.',
            'url_exportacion': 'gestion:exportar_alertas_preaviso',
        }
        return render(request, 'gestion/exportaciones/seleccionar_tipo.html', context)
    
    contratos = list(obtener_alertas_preaviso(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_contrato_cp if tipo_contrato_cp else None
    ))

    if not contratos:
        messages.warning(request, 'No hay alertas de preaviso disponibles.')
        return redirect('gestion:exportaciones')

    columnas = [
        ColumnaExportacion('Número de Contrato', ancho=22),
        ColumnaExportacion('Arrendatario', ancho=30),
        ColumnaExportacion('Local', ancho=26),
        ColumnaExportacion('Fecha Final', ancho=18, alineacion='center'),
        ColumnaExportacion('Días Preaviso Configurados', ancho=24, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Fecha Límite Preaviso', ancho=22, alineacion='center'),
        ColumnaExportacion('Otrosí Modificador', ancho=25),
    ]

    registros = []
    for contrato in contratos:
        # Usar efecto cadena para obtener fecha final vigente hasta fecha_actual
        otrosi_modificador_fecha = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_final_actualizada', fecha_actual
        )
        if otrosi_modificador_fecha and otrosi_modificador_fecha.nueva_fecha_final_actualizada:
            fecha_final_actual = otrosi_modificador_fecha.nueva_fecha_final_actualizada
            otrosi_numero = otrosi_modificador_fecha.numero_otrosi
        else:
            fecha_final_actual = contrato.fecha_final_actualizada or contrato.fecha_final_inicial
            otrosi_numero = None
        
        dias_preaviso = contrato.dias_preaviso_no_renovacion or 0
        fecha_limite_preaviso = None
        if fecha_final_actual:
            fecha_limite_preaviso = fecha_final_actual - timedelta(days=dias_preaviso)

        tercero = contrato.obtener_tercero()
        nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
        local_nombre = contrato.local.nombre_comercial_stand if contrato.local else '-'
        registros.append(
            (
                contrato.num_contrato,
                nombre_tercero,
                local_nombre,
                fecha_final_actual,
                dias_preaviso,
                fecha_limite_preaviso,
                otrosi_numero or 'Contrato Original',
            )
        )

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Preaviso Renovación',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'alertas_preaviso')


@login_required_custom
def exportar_alertas_polizas_requeridas(request):
    """
    Genera el archivo Excel con las alertas de pólizas requeridas no aportadas.
    """
    from gestion.forms import FiltroExportacionAlertasForm
    
    fecha_actual = timezone.now().date()
    tipo_contrato_cp = request.GET.get('tipo_contrato_cp', '') or request.POST.get('tipo_contrato_cliente_proveedor', '')
    
    # Si es GET sin parámetro tipo_contrato_cp, mostrar formulario de selección
    if request.method == 'GET' and 'tipo_contrato_cp' not in request.GET:
        form = FiltroExportacionAlertasForm()
        context = {
            'form': form,
            'titulo': 'Exportar Alertas de Pólizas Requeridas',
            'descripcion': 'Seleccione el tipo de contrato para exportar las alertas de pólizas requeridas no aportadas.',
            'url_exportacion': 'gestion:exportar_alertas_polizas_requeridas',
        }
        return render(request, 'gestion/exportaciones/seleccionar_tipo.html', context)
    
    alertas = obtener_alertas_polizas_requeridas_no_aportadas(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_contrato_cp if tipo_contrato_cp else None
    )

    if not alertas:
        messages.warning(request, 'No hay alertas de pólizas requeridas no aportadas.')
        return redirect('gestion:exportaciones')

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
        estado = 'Sin póliza' if not alerta.tiene_poliza else 'Póliza vencida'
        valor_requerido = int(round(float(alerta.valor_requerido))) if alerta.valor_requerido else None

        tercero = alerta.contrato.obtener_tercero()
        nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
        local_nombre = alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-'
        registros.append(
            (
                alerta.contrato.num_contrato,
                nombre_tercero,
                local_nombre,
                alerta.tipo_poliza,
                alerta.nombre_poliza,
                valor_requerido,
                alerta.fecha_fin_requerida,
                'Sí' if alerta.tiene_poliza else 'No',
                estado,
                alerta.otrosi_modificador or 'Contrato Original',
            )
        )

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Pólizas Requeridas No Aportadas',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'alertas_polizas_requeridas_no_aportadas')


@login_required_custom
def exportar_alertas_terminacion(request):
    """
    Genera el archivo Excel con las alertas de terminación anticipada.
    """
    from gestion.forms import FiltroExportacionAlertasForm
    
    fecha_actual = timezone.now().date()
    tipo_contrato_cp = request.GET.get('tipo_contrato_cp', '') or request.POST.get('tipo_contrato_cliente_proveedor', '')
    
    # Si es GET sin parámetro tipo_contrato_cp, mostrar formulario de selección
    if request.method == 'GET' and 'tipo_contrato_cp' not in request.GET:
        form = FiltroExportacionAlertasForm()
        context = {
            'form': form,
            'titulo': 'Exportar Alertas de Terminación Anticipada',
            'descripcion': 'Seleccione el tipo de contrato para exportar las alertas de terminación anticipada.',
            'url_exportacion': 'gestion:exportar_alertas_terminacion',
        }
        return render(request, 'gestion/exportaciones/seleccionar_tipo.html', context)
    
    alertas = obtener_alertas_terminacion_anticipada(
        fecha_referencia=fecha_actual,
        tipo_contrato_cp=tipo_contrato_cp if tipo_contrato_cp else None
    )

    if not alertas:
        messages.warning(request, 'No hay alertas de terminación anticipada.')
        return redirect('gestion:exportaciones')

    columnas = [
        ColumnaExportacion('Número de Contrato', ancho=22),
        ColumnaExportacion('Arrendatario', ancho=30),
        ColumnaExportacion('Local', ancho=26),
        ColumnaExportacion('Fecha Final', ancho=18, alineacion='center'),
        ColumnaExportacion('Días Restantes', ancho=18, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Días Terminación Anticipada', ancho=28, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Fecha Límite Terminación', ancho=24, alineacion='center'),
        ColumnaExportacion('Otrosí Modificador', ancho=25),
    ]

    registros = []
    for alerta in alertas:
        tercero = alerta.contrato.obtener_tercero()
        nombre_tercero = tercero.razon_social if tercero else 'Sin tercero asignado'
        local_nombre = alerta.contrato.local.nombre_comercial_stand if alerta.contrato.local else '-'
        registros.append(
            (
                alerta.contrato.num_contrato,
                nombre_tercero,
                local_nombre,
                alerta.fecha_final_actualizada,
                alerta.dias_restantes,
                alerta.dias_terminacion_anticipada,
                alerta.fecha_limite_terminacion,
                alerta.otrosi_modificador or 'Contrato Original',
            )
        )

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Terminación Anticipada',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:exportaciones')

    return _respuesta_archivo_excel(archivo, 'alertas_terminacion_anticipada')

