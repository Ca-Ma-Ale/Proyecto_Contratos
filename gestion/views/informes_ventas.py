from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from django.http import HttpResponse

from gestion.decorators import login_required_custom
from gestion.forms import InformeVentasForm, FiltroContratosVentasForm, FiltroInformesEntregadosForm, CalculoFacturacionVentasForm
from gestion.models import Contrato, InformeVentas, CalculoFacturacionVentas
from gestion.utils_otrosi import (
    obtener_valores_vigentes_facturacion_ventas,
    es_fecha_fuera_vigencia_contrato,
    get_ultimo_otrosi_que_modifico_campo_hasta_fecha,
)
from gestion.services.exportes import generar_pdf_calculo_facturacion, generar_excel_calculo_facturacion, generar_excel_informes_ventas
from gestion.views.utils import obtener_configuracion_empresa


def _obtener_fecha_final_para_corte(contrato, fecha_referencia):
    """Determina la fecha final vigente del contrato para la fecha de corte."""
    otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato,
        'nueva_fecha_final_actualizada',
        fecha_referencia,
    )
    if otrosi_modificador and getattr(otrosi_modificador, 'nueva_fecha_final_actualizada', None):
        return otrosi_modificador.nueva_fecha_final_actualizada
    return contrato.fecha_final_actualizada or contrato.fecha_final_inicial


def _es_contrato_vigente_en_fecha(contrato, fecha_referencia):
    """Verifica si el contrato está vigente para la fecha de corte proporcionada."""
    fecha_final = _obtener_fecha_final_para_corte(contrato, fecha_referencia)
    if not fecha_final:
        return True
    return fecha_final >= fecha_referencia


@login_required_custom
def lista_informes_ventas(request):
    """Vista para listar contratos que reportan ventas con filtros y fecha de corte"""
    contratos = Contrato.objects.filter(reporta_ventas=True).select_related(
        'arrendatario', 'proveedor', 'local', 'tipo_contrato', 'tipo_servicio'
    ).order_by('num_contrato')
    
    filtro_form = FiltroContratosVentasForm(request.GET or None)
    
    # Valores por defecto de fecha de corte
    ahora = timezone.now()
    mes_seleccionado = ahora.month
    año_seleccionado = ahora.year
    
    estado_vigencia = 'vigentes'
    if filtro_form.is_valid():
        tipo_contrato_cliente_proveedor = filtro_form.cleaned_data.get('tipo_contrato_cliente_proveedor')
        tipo_contrato = filtro_form.cleaned_data.get('tipo_contrato')
        buscar = filtro_form.cleaned_data.get('buscar')
        mes_seleccionado = int(filtro_form.cleaned_data.get('mes') or mes_seleccionado)
        estado_vigencia = filtro_form.cleaned_data.get('estado_vigencia') or estado_vigencia
        
        if tipo_contrato_cliente_proveedor:
            contratos = contratos.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cliente_proveedor)
        
        if tipo_contrato:
            contratos = contratos.filter(tipo_contrato=tipo_contrato)
        
        if buscar:
            contratos = contratos.filter(
                Q(arrendatario__razon_social__icontains=buscar) |
                Q(arrendatario__nit__icontains=buscar) |
                Q(proveedor__razon_social__icontains=buscar) |
                Q(proveedor__nit__icontains=buscar)
            )
    
    from calendar import monthrange
    ultimo_dia_mes = monthrange(año_seleccionado, mes_seleccionado)[1]
    fecha_corte = date(año_seleccionado, mes_seleccionado, ultimo_dia_mes)

    # Determinar contratos que aplican según fecha de corte
    contratos_info = []
    contratos_fuera_periodo = []
    for contrato in contratos:
        if es_fecha_fuera_vigencia_contrato(contrato, fecha_corte):
            contratos_fuera_periodo.append(contrato)
            continue
        
        contrato_vigente = _es_contrato_vigente_en_fecha(contrato, fecha_corte)
        if estado_vigencia == 'vigentes' and not contrato_vigente:
            continue
        if estado_vigencia == 'vencidos' and contrato_vigente:
            continue

        valores_vigentes = obtener_valores_vigentes_facturacion_ventas(contrato, mes_seleccionado, año_seleccionado)
        if valores_vigentes:
            contratos_info.append({
                'contrato': contrato,
                'valores': valores_vigentes,
            })

    if contratos_fuera_periodo:
        messages.info(
            request,
            'Algunos contratos no se muestran porque la fecha seleccionada es anterior al inicio del contrato.'
        )
    
    meses_nombres = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    mes_nombre = meses_nombres[mes_seleccionado] if 1 <= mes_seleccionado <= 12 else f'Mes {mes_seleccionado}'
    
    context = {
        'contratos_info': contratos_info,
        'filtro_form': filtro_form,
        'total_contratos': len(contratos_info),
        'mes_seleccionado': mes_seleccionado,
        'año_seleccionado': año_seleccionado,
        'mes_nombre': mes_nombre,
    }
    
    return render(request, 'gestion/informes/ventas/lista.html', context)


@login_required_custom
def nuevo_informe_ventas(request):
    """Vista para crear un nuevo informe de ventas"""
    if request.method == 'POST':
        form = InformeVentasForm(request.POST)
        
        if form.is_valid():
            informe = form.save(commit=False)
            informe.registrado_por = request.user.get_username() if request.user.is_authenticated else None
            informe.estado = 'PENDIENTE'
            informe.fecha_entrega = None
            informe.fecha_limite = None
            
            informe.save()
            messages.success(request, f'Informe de ventas creado exitosamente para {informe.contrato.num_contrato} - {informe.get_mes_display()}/{informe.año}')
            # Redirigir automáticamente al cálculo
            from django.urls import reverse
            return redirect(reverse('gestion:calcular_facturacion') + f'?informe_id={informe.id}')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = InformeVentasForm()
        # Si viene un contrato_id en la URL, pre-seleccionarlo
        contrato_id = request.GET.get('contrato_id')
        if contrato_id:
            try:
                contrato = Contrato.objects.get(id=contrato_id, reporta_ventas=True)
                form.fields['contrato'].initial = contrato
            except Contrato.DoesNotExist:
                pass
        mes_param = request.GET.get('mes')
        año_param = request.GET.get('año')
        if mes_param and mes_param.isdigit():
            form.fields['mes'].initial = int(mes_param)
        if año_param and año_param.isdigit():
            form.fields['año'].initial = int(año_param)
    
    context = {
        'form': form,
        'titulo': 'Nuevo Informe de Ventas',
    }
    
    return render(request, 'gestion/informes/ventas/form.html', context)


@login_required_custom
def editar_informe_ventas(request, informe_id):
    """Vista para editar un informe de ventas existente"""
    informe = get_object_or_404(InformeVentas, id=informe_id)
    
    if request.method == 'POST':
        form = InformeVentasForm(request.POST, instance=informe)
        
        if form.is_valid():
            informe = form.save(commit=False)
            informe.estado = 'PENDIENTE'
            informe.fecha_entrega = None
            informe.save()
            messages.success(request, f'Informe de ventas actualizado exitosamente para {informe.contrato.num_contrato} - {informe.get_mes_display()}/{informe.año}. Redirigiendo al cálculo...')
            # Redirigir automáticamente al cálculo (igual que crear)
            from django.urls import reverse
            return redirect(reverse('gestion:calcular_facturacion') + f'?informe_id={informe.id}')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = InformeVentasForm(instance=informe)
    
    context = {
        'form': form,
        'informe': informe,
        'titulo': 'Editar Informe de Ventas',
    }
    
    return render(request, 'gestion/informes/ventas/form.html', context)


@login_required_custom
def marcar_entregado_informe(request, informe_id):
    """Vista para marcar un informe como entregado"""
    informe = get_object_or_404(InformeVentas, id=informe_id)
    
    if request.method == 'POST':
        fecha_entrega_str = request.POST.get('fecha_entrega')
        calcular_desde_marcar = request.POST.get('calcular_desde_marcar', 'false') == 'true'
        
        if fecha_entrega_str:
            try:
                fecha_entrega = date.fromisoformat(fecha_entrega_str)
                informe.marcar_como_entregado(fecha_entrega)
            except ValueError:
                informe.marcar_como_entregado()
        else:
            informe.marcar_como_entregado()
        
        messages.success(request, f'Informe de ventas marcado como entregado para {informe.contrato.num_contrato} - {informe.get_mes_display()}/{informe.año}')
        
        # Si se solicita calcular desde marcar, redirigir al formulario de cálculo
        if calcular_desde_marcar and informe.contrato.reporta_ventas:
            from django.urls import reverse
            return redirect(reverse('gestion:calcular_facturacion') + f'?informe_id={informe.id}')
        
        return redirect('gestion:lista_informes_ventas')
    
    context = {
        'informe': informe,
        'puede_calcular': informe.contrato.reporta_ventas,
    }
    
    return render(request, 'gestion/informes/ventas/marcar_entregado.html', context)


@login_required_custom
def marcar_pendiente_informe(request, informe_id):
    """Vista para marcar un informe como pendiente"""
    informe = get_object_or_404(InformeVentas, id=informe_id)
    
    if request.method == 'POST':
        informe.marcar_como_pendiente()
        messages.success(request, f'Informe de ventas marcado como pendiente para {informe.contrato.num_contrato} - {informe.get_mes_display()}/{informe.año}')
        return redirect('gestion:lista_informes_ventas')
    
    context = {
        'informe': informe,
    }
    
    return render(request, 'gestion/informes/ventas/marcar_pendiente.html', context)


@login_required_custom
def eliminar_informe_ventas(request, informe_id):
    """Vista para eliminar un informe de ventas"""
    informe = get_object_or_404(InformeVentas, id=informe_id)
    
    if request.method == 'POST':
        contrato_num = informe.contrato.num_contrato
        mes_año = f"{informe.get_mes_display()}/{informe.año}"
        informe.delete()
        messages.success(request, f'Informe de ventas eliminado: {contrato_num} - {mes_año}')
        return redirect('gestion:lista_informes_ventas')
    
    context = {
        'informe': informe,
    }
    
    return render(request, 'gestion/informes/ventas/eliminar.html', context)


def calcular_facturacion_ventas(contrato, mes, año, ventas_totales, devoluciones):
    """
    Calcula la facturación por ventas según la modalidad del contrato.
    
    Args:
        contrato: Instancia del modelo Contrato
        mes: Mes (1-12)
        año: Año
        ventas_totales: Decimal o float con las ventas totales
        devoluciones: Decimal o float con las devoluciones
    
    Returns:
        dict con los resultados del cálculo o None si hay error
    """
    # Convertir a Decimal para evitar problemas de tipos
    if not isinstance(ventas_totales, Decimal):
        ventas_totales = Decimal(str(ventas_totales))
    if not isinstance(devoluciones, Decimal):
        devoluciones = Decimal(str(devoluciones)) if devoluciones else Decimal('0')
    
    # Obtener valores vigentes para el mes
    valores_vigentes = obtener_valores_vigentes_facturacion_ventas(contrato, mes, año)
    
    if not valores_vigentes:
        return None
    
    # Calcular base neta
    base_neta = ventas_totales - devoluciones
    
    # Calcular valor con porcentaje
    porcentaje = valores_vigentes['porcentaje_ventas']
    valor_calculado_porcentaje = base_neta * (porcentaje / Decimal('100'))
    
    # Determinar modalidad para el cálculo
    modalidad_calculo = None
    if valores_vigentes['modalidad'] == 'Variable Puro':
        modalidad_calculo = 'VARIABLE_PURO'
        valor_a_facturar_variable = valor_calculado_porcentaje
        excedente_sobre_minimo = None
        aplica_variable = True
    elif valores_vigentes['modalidad'] == 'Hibrido (Min Garantizado)':
        modalidad_calculo = 'HIBRIDO_MIN_GARANTIZADO'
        canon_minimo = valores_vigentes['canon_minimo_garantizado']
        
        if canon_minimo is None:
            return None  # Error: debe tener mínimo garantizado
        
        # Comparar valor calculado con mínimo garantizado
        if valor_calculado_porcentaje <= canon_minimo:
            # No aplica variable, solo se factura el mínimo
            valor_a_facturar_variable = Decimal('0')
            excedente_sobre_minimo = None
            aplica_variable = False
        else:
            # Se factura el excedente sobre el mínimo
            excedente_sobre_minimo = valor_calculado_porcentaje - canon_minimo
            valor_a_facturar_variable = excedente_sobre_minimo
            aplica_variable = True
    else:
        return None  # Modalidad no válida
    
    return {
        'base_neta': base_neta,
        'porcentaje_ventas': porcentaje,
        'valor_calculado_porcentaje': valor_calculado_porcentaje,
        'modalidad_calculo': modalidad_calculo,
        'canon_minimo_garantizado': valores_vigentes.get('canon_minimo_garantizado'),
        'canon_fijo': valores_vigentes.get('canon_fijo'),
        'valor_a_facturar_variable': valor_a_facturar_variable,
        'excedente_sobre_minimo': excedente_sobre_minimo,
        'aplica_variable': aplica_variable,
        'otrosi_referencia': valores_vigentes.get('otrosi_referencia'),
        'fecha_referencia': valores_vigentes.get('fecha_referencia'),
    }


@login_required_custom
def calcular_facturacion(request):
    """Vista para calcular facturación por ventas"""
    informe_id = request.GET.get('informe_id') or request.POST.get('informe_id')
    informe = None
    
    if informe_id:
        try:
            informe = InformeVentas.objects.get(id=informe_id)
        except InformeVentas.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = CalculoFacturacionVentasForm(request.POST)
        
        if form.is_valid():
            contrato = form.cleaned_data['contrato']
            mes = int(form.cleaned_data['mes'])
            año = form.cleaned_data['año']
            ventas_totales = form.cleaned_data['ventas_totales']
            devoluciones = form.cleaned_data['devoluciones'] or Decimal('0')
            observaciones = form.cleaned_data.get('observaciones', '')

            from calendar import monthrange
            fecha_corte = date(año, mes, monthrange(año, mes)[1])
            if es_fecha_fuera_vigencia_contrato(contrato, fecha_corte):
                messages.error(
                    request,
                    'El contrato no estaba vigente en el periodo seleccionado. '
                    'Seleccione un mes posterior a la fecha de inicio del contrato.'
                )
                context = {
                    'form': form,
                    'titulo': 'Calcular Facturación por Ventas',
                    'informe': informe,
                }
                return render(request, 'gestion/calculos/facturacion_form.html', context)
            
            # Realizar el cálculo
            resultado = calcular_facturacion_ventas(contrato, mes, año, ventas_totales, devoluciones)
            
            if not resultado:
                messages.error(
                    request,
                    'No se pudo realizar el cálculo. Verifique que el contrato tenga modalidad Variable Puro o Híbrido '
                    'con porcentaje de ventas configurado para el mes seleccionado.'
                )
                context = {
                    'form': form,
                    'titulo': 'Calcular Facturación por Ventas',
                    'informe': informe,
                }
                return render(request, 'gestion/calculos/facturacion_form.html', context)
            
            # Obtener el informe de ventas asociado (usar el informe editado si existe, sino buscar)
            informe_ventas = informe
            if not informe_ventas:
                informe_ventas = InformeVentas.objects.filter(
                    contrato=contrato,
                    mes=mes,
                    año=año
                ).first()
            
            # Guardar el cálculo
            calculo = CalculoFacturacionVentas.objects.create(
                contrato=contrato,
                informe_ventas=informe_ventas,
                mes=mes,
                año=año,
                ventas_totales=ventas_totales,
                devoluciones=devoluciones,
                base_neta=resultado['base_neta'],
                modalidad_contrato=resultado['modalidad_calculo'],
                porcentaje_ventas_vigente=resultado['porcentaje_ventas'],
                canon_minimo_garantizado_vigente=resultado.get('canon_minimo_garantizado'),
                canon_fijo_vigente=resultado.get('canon_fijo'),
                valor_calculado_porcentaje=resultado['valor_calculado_porcentaje'],
                valor_a_facturar_variable=resultado['valor_a_facturar_variable'],
                excedente_sobre_minimo=resultado.get('excedente_sobre_minimo'),
                aplica_variable=resultado['aplica_variable'],
                otrosi_referencia=resultado.get('otrosi_referencia_canon_minimo') or resultado.get('otrosi_referencia_porcentaje') or resultado.get('otrosi_referencia'),
                observaciones=observaciones,
                calculado_por=request.user.get_username() if request.user.is_authenticated else None,
            )
            
            messages.success(
                request,
                f'Cálculo realizado exitosamente para {contrato.num_contrato} - '
                f'{calculo.get_mes_display()}/{año}. Valor a facturar: ${resultado["valor_a_facturar_variable"]:,.2f}'
            )
            
            # Redirigir a la vista de resultados
            return redirect('gestion:resultado_calculo_facturacion', calculo_id=calculo.id)
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
            # Si hay errores y había un informe_id pero no se obtuvo el informe, intentar obtenerlo
            if informe_id and not informe:
                try:
                    informe = InformeVentas.objects.get(id=informe_id)
                except InformeVentas.DoesNotExist:
                    pass
    else:
        # Si viene desde un informe, pre-llenar los datos
        if informe:
            form = CalculoFacturacionVentasForm(initial={
                'contrato': informe.contrato.id,
                'mes': str(informe.mes),
                'año': informe.año,
            })
        else:
            form = CalculoFacturacionVentasForm()
            # Establecer valores por defecto
            form.fields['año'].initial = date.today().year
            mes_actual = date.today().month
            form.fields['mes'].initial = str(mes_actual)
    
    context = {
        'form': form,
        'titulo': 'Calcular Facturación por Ventas',
        'informe': informe,
    }
    
    return render(request, 'gestion/calculos/facturacion_form.html', context)


@login_required_custom
def resultado_calculo_facturacion(request, calculo_id):
    """Vista para mostrar el resultado del cálculo"""
    from decimal import Decimal
    
    calculo = get_object_or_404(CalculoFacturacionVentas, id=calculo_id)
    
    # Obtener el informe asociado si existe
    informe = calculo.informe_ventas
    
    # Verificar si el porcentaje de ventas fue modificado comparando con el contrato base
    porcentaje_modificado = False
    if calculo.porcentaje_ventas_vigente is not None:
        porcentaje_contrato_base = calculo.contrato.porcentaje_ventas
        if porcentaje_contrato_base is None:
            # Si el contrato base no tiene porcentaje pero el cálculo sí, fue modificado
            porcentaje_modificado = calculo.otrosi_referencia is not None
        else:
            porcentaje_modificado = Decimal(str(calculo.porcentaje_ventas_vigente)) != Decimal(str(porcentaje_contrato_base))
            # Solo mostrar badge si fue modificado Y hay una referencia
            porcentaje_modificado = porcentaje_modificado and calculo.otrosi_referencia is not None
    
    # Verificar si el canon mínimo fue modificado comparando con el contrato base
    canon_min_modificado = False
    if calculo.canon_minimo_garantizado_vigente is not None:
        canon_min_contrato_base = calculo.contrato.canon_minimo_garantizado
        if canon_min_contrato_base is None:
            # Si el contrato base no tiene canon mínimo pero el cálculo sí, fue modificado
            canon_min_modificado = calculo.otrosi_referencia is not None
        else:
            canon_min_modificado = Decimal(str(calculo.canon_minimo_garantizado_vigente)) != Decimal(str(canon_min_contrato_base))
            # Solo mostrar badge si fue modificado Y hay una referencia
            canon_min_modificado = canon_min_modificado and calculo.otrosi_referencia is not None
    
    context = {
        'calculo': calculo,
        'desglose': calculo.get_desglose_completo(),
        'informe': informe,
        'porcentaje_modificado': porcentaje_modificado,
        'canon_min_modificado': canon_min_modificado,
    }
    
    return render(request, 'gestion/calculos/facturacion_resultado.html', context)


@login_required_custom
def finalizar_informe_ventas(request, informe_id):
    """Vista para finalizar un informe de ventas (marcarlo como entregado)"""
    informe = get_object_or_404(InformeVentas, id=informe_id)
    
    if request.method == 'POST':
        fecha_entrega_str = request.POST.get('fecha_entrega')
        
        if fecha_entrega_str:
            try:
                fecha_entrega = date.fromisoformat(fecha_entrega_str)
                informe.marcar_como_entregado(fecha_entrega)
            except ValueError:
                informe.marcar_como_entregado()
        else:
            informe.marcar_como_entregado()
        
        messages.success(request, f'Informe de ventas finalizado exitosamente para {informe.contrato.num_contrato} - {informe.get_mes_display()}/{informe.año}')
        return redirect('gestion:lista_informes_entregados')
    
    # Inicializar fecha de entrega con la fecha de hoy
    fecha_hoy = date.today()
    
    context = {
        'informe': informe,
        'fecha_hoy': fecha_hoy,
    }
    
    return render(request, 'gestion/informes/ventas/finalizar.html', context)


@login_required_custom
def lista_informes_entregados(request):
    """Vista para listar informes de ventas (entregados y pendientes)"""
    # Por defecto mostrar todos los informes, no solo los entregados
    informes = InformeVentas.objects.all().select_related(
        'contrato', 'contrato__arrendatario', 'contrato__local', 'contrato__tipo_contrato'
    ).order_by('-año', '-mes', 'contrato__num_contrato')
    
    # Aplicar filtros
    filtro_form = FiltroInformesEntregadosForm(request.GET)
    
    if filtro_form.is_valid():
        tipo_contrato = filtro_form.cleaned_data.get('tipo_contrato')
        mes = filtro_form.cleaned_data.get('mes')
        año = filtro_form.cleaned_data.get('año')
        estado = filtro_form.cleaned_data.get('estado')
        buscar = filtro_form.cleaned_data.get('buscar')
        
        if tipo_contrato:
            informes = informes.filter(contrato__tipo_contrato=tipo_contrato)
        
        if mes:
            informes = informes.filter(mes=int(mes))
        
        if año:
            informes = informes.filter(año=año)
        
        if estado:
            informes = informes.filter(estado=estado)
        
        if buscar:
            informes = informes.filter(
                Q(contrato__num_contrato__icontains=buscar) |
                Q(contrato__arrendatario__razon_social__icontains=buscar) |
                Q(contrato__arrendatario__nit__icontains=buscar) |
                Q(contrato__local__nombre_comercial_stand__icontains=buscar)
            )
    else:
        # Si no hay filtro de estado, mostrar todos por defecto
        pass
    
    # Estadísticas
    total_informes = informes.count()
    total_entregados = InformeVentas.objects.filter(estado='ENTREGADO').count()
    total_pendientes = InformeVentas.objects.filter(estado='PENDIENTE').count()
    
    context = {
        'informes': informes,
        'filtro_form': filtro_form,
        'total_informes': total_informes,
        'total_entregados': total_entregados,
        'total_pendientes': total_pendientes,
    }
    
    return render(request, 'gestion/informes/ventas/entregados_lista.html', context)


@login_required_custom
def descargar_pdf_calculo(request, calculo_id):
    """Vista para descargar el PDF del cálculo"""
    calculo = get_object_or_404(CalculoFacturacionVentas, id=calculo_id)
    configuracion_empresa = obtener_configuracion_empresa()
    
    pdf_content = generar_pdf_calculo_facturacion(calculo, configuracion_empresa)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="calculo_facturacion_{calculo.contrato.num_contrato}_{calculo.get_mes_display()}_{calculo.año}.pdf"'
    
    return response


@login_required_custom
def exportar_informes_excel(request):
    """Vista para exportar informes de ventas a Excel aplicando los mismos filtros de la lista"""
    try:
        from gestion.forms import FiltroInformesEntregadosForm
        
        # Aplicar los mismos filtros que en lista_informes_entregados
        informes = InformeVentas.objects.all().select_related(
            'contrato', 'contrato__arrendatario', 'contrato__proveedor', 'contrato__local', 'contrato__tipo_contrato', 'contrato__tipo_servicio'
        )
        
        # Aplicar filtros desde los parámetros GET
        filtro_form = FiltroInformesEntregadosForm(request.GET)
        
        if filtro_form.is_valid():
            tipo_contrato_cliente_proveedor = filtro_form.cleaned_data.get('tipo_contrato_cliente_proveedor')
            tipo_contrato = filtro_form.cleaned_data.get('tipo_contrato')
            mes = filtro_form.cleaned_data.get('mes')
            año = filtro_form.cleaned_data.get('año')
            estado = filtro_form.cleaned_data.get('estado')
            buscar = filtro_form.cleaned_data.get('buscar')
            
            if tipo_contrato_cliente_proveedor:
                informes = informes.filter(contrato__tipo_contrato_cliente_proveedor=tipo_contrato_cliente_proveedor)
            
            if tipo_contrato:
                informes = informes.filter(contrato__tipo_contrato=tipo_contrato)
            
            if mes:
                informes = informes.filter(mes=int(mes))
            
            if año:
                informes = informes.filter(año=año)
            
            if estado:
                informes = informes.filter(estado=estado)
            
            if buscar:
                informes = informes.filter(
                    Q(contrato__num_contrato__icontains=buscar) |
                    Q(contrato__arrendatario__razon_social__icontains=buscar) |
                    Q(contrato__arrendatario__nit__icontains=buscar) |
                    Q(contrato__proveedor__razon_social__icontains=buscar) |
                    Q(contrato__proveedor__nit__icontains=buscar) |
                    Q(contrato__local__nombre_comercial_stand__icontains=buscar)
                )
        
        # Generar Excel con los informes filtrados
        excel_content = generar_excel_informes_ventas(informes_queryset=informes)
        
        fecha_actual = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'informes_ventas_{fecha_actual}.xlsx'
        
        response = HttpResponse(excel_content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except ValueError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Error de validación al generar archivo Excel", exc_info=True)
        messages.error(request, 'Error de validación al generar el archivo Excel. Por favor, verifique los datos e intente nuevamente.')
        return redirect('gestion:lista_informes_entregados')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("Error al generar archivo Excel", exc_info=True)
        messages.error(request, 'Error al generar el archivo Excel. Por favor, intente nuevamente o contacte al administrador.')
        return redirect('gestion:lista_informes_entregados')


@login_required_custom
def descargar_excel_calculo(request, calculo_id):
    """Vista para descargar el Excel del cálculo"""
    calculo = get_object_or_404(CalculoFacturacionVentas, id=calculo_id)
    
    excel_content = generar_excel_calculo_facturacion(calculo)
    
    response = HttpResponse(excel_content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="calculo_facturacion_{calculo.contrato.num_contrato}_{calculo.get_mes_display()}_{calculo.año}.xlsx"'
    
    return response

