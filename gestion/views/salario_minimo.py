"""
Vistas para el módulo de gestión de Salario Mínimo
"""
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import SalarioMinimoHistoricoForm, CalculoSalarioMinimoForm, EditarCalculoSalarioMinimoForm
from gestion.models import SalarioMinimoHistorico, CalculoSalarioMinimo, Contrato
from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
from gestion.utils_salario_minimo import (
    obtener_canon_base_para_salario_minimo,
    calcular_ajuste_salario_minimo,
    obtener_contratos_pendientes_ajuste_salario_minimo,
    validar_salario_minimo_disponible,
    obtener_ultimo_calculo_salario_minimo_contrato,
    obtener_fuente_porcentaje_salario_minimo,
    obtener_fuente_puntos_adicionales_salario_minimo,
    verificar_otrosi_vigente_para_fecha,
    verificar_calculo_existente_para_fecha,
)
from gestion.utils_formateo import limpiar_valor_numerico


@login_required_custom
def lista_salario_minimo_historico(request):
    """Lista todos los contratos con acción de calcular Salario Mínimo"""
    fecha_actual = date.today()
    
    # Obtener todos los contratos activos con tipo SALARIO_MINIMO
    contratos = Contrato.objects.filter(
        vigente=True,
        tipo_condicion_ipc='SALARIO_MINIMO'
    ).select_related(
        'arrendatario', 'proveedor', 'local', 'tipo_contrato', 'tipo_servicio'
    ).prefetch_related('otrosi').order_by('num_contrato')
    
    # Preparar información de cada contrato
    contratos_info = []
    for contrato in contratos:
        # Obtener fecha final actualizada considerando otrosí
        otrosi_mod = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_final_actualizada', fecha_actual
        )
        if otrosi_mod and otrosi_mod.nueva_fecha_final_actualizada:
            fecha_final = otrosi_mod.nueva_fecha_final_actualizada
        else:
            fecha_final = contrato.fecha_final_actualizada or contrato.fecha_inicial_contrato
        
        # Obtener fecha de aumento considerando otrosí
        otrosi_fecha = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_aumento_ipc', fecha_actual
        )
        if otrosi_fecha and otrosi_fecha.nueva_fecha_aumento_ipc:
            fecha_aumento = otrosi_fecha.nueva_fecha_aumento_ipc
        else:
            fecha_aumento = contrato.fecha_aumento_ipc
        
        # Obtener último cálculo de Salario Mínimo si existe
        ultimo_calculo = CalculoSalarioMinimo.objects.filter(contrato=contrato).order_by('-fecha_aplicacion', '-fecha_calculo').first()
        
        contratos_info.append({
            'contrato': contrato,
            'fecha_final': fecha_final,
            'fecha_aumento': fecha_aumento,
            'ultimo_calculo': ultimo_calculo,
        })
    
    context = {
        'contratos_info': contratos_info,
        'titulo': 'Gestión de Salario Mínimo - Contratos',
        'fecha_actual': fecha_actual,
    }
    return render(request, 'gestion/salario_minimo/contratos_lista.html', context)


@login_required_custom
def historico_salario_minimo_valores(request):
    """Lista el histórico completo de valores del Salario Mínimo"""
    salario_minimo_historico = SalarioMinimoHistorico.objects.all().order_by('-año')
    
    context = {
        'salario_minimo_historico': salario_minimo_historico,
        'titulo': 'Histórico de Salario Mínimo',
    }
    return render(request, 'gestion/salario_minimo/historico_lista.html', context)


@admin_required
def nuevo_salario_minimo_historico(request):
    """Vista para agregar un nuevo valor de Salario Mínimo histórico"""
    if request.method == 'POST':
        form = SalarioMinimoHistoricoForm(request.POST)
        
        if form.is_valid():
            smlv = form.save(commit=False)
            smlv.creado_por = request.user.get_full_name() or request.user.username
            smlv.save()
            messages.success(request, f'Salario Mínimo {smlv.año} (${smlv.valor_salario_minimo:,.2f}) agregado exitosamente!')
            return redirect('gestion:historico_salario_minimo_valores')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = SalarioMinimoHistoricoForm()
    
    context = {
        'form': form,
        'titulo': 'Nuevo Salario Mínimo Histórico',
    }
    return render(request, 'gestion/salario_minimo/historico_form.html', context)


@admin_required
def editar_salario_minimo_historico(request, smlv_id):
    """Vista para editar un valor de Salario Mínimo histórico"""
    smlv = get_object_or_404(SalarioMinimoHistorico, id=smlv_id)
    
    if request.method == 'POST':
        form = SalarioMinimoHistoricoForm(request.POST, instance=smlv)
        
        if form.is_valid():
            smlv = form.save(commit=False)
            smlv.modificado_por = request.user.get_full_name() or request.user.username
            smlv.save()
            messages.success(request, f'Salario Mínimo {smlv.año} actualizado exitosamente!')
            return redirect('gestion:historico_salario_minimo_valores')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = SalarioMinimoHistoricoForm(instance=smlv)
    
    context = {
        'form': form,
        'smlv': smlv,
        'titulo': f'Editar Salario Mínimo {smlv.año}',
    }
    return render(request, 'gestion/salario_minimo/historico_form.html', context)


@admin_required
def eliminar_salario_minimo_historico(request, smlv_id):
    """Vista para eliminar un valor de Salario Mínimo histórico"""
    smlv = get_object_or_404(SalarioMinimoHistorico, id=smlv_id)
    
    if request.method == 'POST':
        año = smlv.año
        smlv.delete()
        messages.success(request, f'Salario Mínimo {año} eliminado exitosamente!')
        return redirect('gestion:historico_salario_minimo_valores')
    
    # Verificar si hay cálculos que usan este Salario Mínimo
    calculos = CalculoSalarioMinimo.objects.filter(salario_minimo_historico=smlv)
    
    context = {
        'smlv': smlv,
        'calculos': calculos,
        'titulo': f'Eliminar Salario Mínimo {smlv.año}',
    }
    return render(request, 'gestion/salario_minimo/historico_eliminar.html', context)


@login_required_custom
def calcular_salario_minimo(request):
    """Vista para calcular el ajuste de canon por Salario Mínimo"""
    if request.method == 'POST':
        form = CalculoSalarioMinimoForm(request.POST, user=request.user)
        accion = request.POST.get('accion', 'calcular')
        
        if form.is_valid():
            contrato = form.cleaned_data['contrato']
            fecha_aplicacion = form.cleaned_data['fecha_aplicacion']
            salario_minimo_historico = form.cleaned_data['salario_minimo_historico']
            canon_anterior_manual = form.cleaned_data.get('canon_anterior_manual', False)
            canon_anterior = form.cleaned_data.get('canon_anterior')
            observaciones = form.cleaned_data.get('observaciones', '')
            
            # Si no es manual y no hay canon, obtenerlo automáticamente
            if not canon_anterior_manual and not canon_anterior:
                canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
                if canon_info['canon']:
                    canon_anterior = canon_info['canon']
                    messages.info(request, f'Canon anterior obtenido automáticamente desde: {canon_info["fuente"]}')
                else:
                    if request.user.is_staff:
                        messages.warning(
                            request, 
                            f'No se pudo obtener el canon anterior automáticamente. '
                            f'El contrato {contrato.num_contrato} no tiene canon fijo ni canon mínimo garantizado registrado. '
                            f'Por favor, marque la opción "Ingresar Canon Anterior Manualmente" e ingrese el valor.'
                        )
                    else:
                        messages.warning(
                            request, 
                            f'No se pudo obtener el canon anterior automáticamente. '
                            f'Por favor, contacte a un administrador para ingresar el canon anterior manualmente.'
                        )
                    form.add_error(None, 'No se pudo obtener el canon anterior automáticamente. Por favor, ingréselo manualmente.')
                    context = {'form': form, 'titulo': 'Calcular Ajuste por Salario Mínimo', 'user': request.user}
                    return render(request, 'gestion/salario_minimo/calcular_form.html', context)
            
            # Validar que el canon anterior esté presente
            if not canon_anterior:
                form.add_error('canon_anterior', 'El canon anterior es requerido.')
                context = {'form': form, 'titulo': 'Calcular Ajuste por Salario Mínimo', 'user': request.user}
                return render(request, 'gestion/salario_minimo/calcular_form.html', context)
            
            # Obtener variación porcentual del salario mínimo histórico
            variacion_salario_minimo = salario_minimo_historico.variacion_porcentual
            
            if variacion_salario_minimo is None:
                # Si no hay variación (primer año), usar porcentaje del contrato como fallback
                fuente_porcentaje_info = obtener_fuente_porcentaje_salario_minimo(contrato, fecha_aplicacion)
                variacion_salario_minimo = fuente_porcentaje_info['porcentaje'] or Decimal('0')
                if variacion_salario_minimo:
                    messages.info(request, f'No hay variación calculada (primer año). Usando porcentaje del contrato: {variacion_salario_minimo}%')
                else:
                    form.add_error(None, 'No se pudo obtener la variación del salario mínimo ni el porcentaje del contrato.')
                    context = {'form': form, 'titulo': 'Calcular Ajuste por Salario Mínimo', 'user': request.user}
                    return render(request, 'gestion/salario_minimo/calcular_form.html', context)
            else:
                messages.info(request, f'Variación del Salario Mínimo {salario_minimo_historico.año}: {variacion_salario_minimo}%')
            
            # Obtener puntos adicionales considerando OtroSi
            fuente_puntos_info = obtener_fuente_puntos_adicionales_salario_minimo(contrato, fecha_aplicacion)
            puntos_adicionales = fuente_puntos_info['puntos']
            
            # Verificar si existe un Otro Sí vigente que modifica el canon para esta fecha
            otrosi_info = verificar_otrosi_vigente_para_fecha(contrato, fecha_aplicacion)
            
            # Calcular el ajuste usando la variación del salario mínimo
            resultado = calcular_ajuste_salario_minimo(
                canon_anterior,
                variacion_salario_minimo,
                puntos_adicionales
            )
            
            # Si hay un Otro Sí vigente con valor diferente, usar el valor del Otro Sí
            if otrosi_info['existe'] and otrosi_info['valor_canon']:
                valor_calculado = resultado['nuevo_canon']
                valor_otrosi = otrosi_info['valor_canon']
                if abs(valor_calculado - valor_otrosi) > Decimal('0.01'):  # Tolerancia de 1 centavo
                    # Actualizar el resultado con el valor del Otro Sí
                    diferencia = valor_otrosi - canon_anterior
                    resultado['nuevo_canon'] = valor_otrosi
                    resultado['valor_incremento'] = diferencia
                    # Recalcular el porcentaje total basado en el valor del Otro Sí
                    if canon_anterior > 0:
                        porcentaje_aplicado = ((valor_otrosi / canon_anterior) - Decimal('1')) * Decimal('100')
                        resultado['porcentaje_total'] = porcentaje_aplicado
            
            # Si solo se calcula, mostrar resultado sin guardar
            if accion == 'calcular':
                canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
                if canon_anterior_manual:
                    canon_info['fuente'] = 'Manual (Usuario)'
                
                # Verificar si hay otro sí vigente con valor diferente
                alerta_otrosi = None
                if otrosi_info['existe'] and otrosi_info['valor_canon']:
                    valor_calculado = resultado['nuevo_canon']
                    valor_otrosi = otrosi_info['valor_canon']
                    if abs(valor_calculado - valor_otrosi) > Decimal('0.01'):  # Tolerancia de 1 centavo
                        alerta_otrosi = {
                            'existe': True,
                            'otrosi': otrosi_info['otrosi'],
                            'valor_otrosi': valor_otrosi,
                            'valor_calculado': valor_calculado,
                            'diferencia': abs(valor_calculado - valor_otrosi),
                        }
                        messages.info(
                            request,
                            f'ℹ️ INFORMACIÓN: Existe un Otro Sí vigente ({otrosi_info["otrosi"].numero_otrosi}) '
                            f'que establece un canon de ${valor_otrosi:,.2f} para este período. '
                            f'El cálculo por Salario Mínimo da ${valor_calculado:,.2f}. '
                            f'Se utilizará automáticamente el valor del Otro Sí vigente (${valor_otrosi:,.2f}) como definitivo.'
                        )
                
                context = {
                    'form': form,
                    'titulo': 'Calcular Ajuste por Salario Mínimo',
                    'mostrar_resultado': True,
                    'resultado': resultado,
                    'canon_anterior': canon_anterior,
                    'salario_minimo_historico': salario_minimo_historico,
                    'variacion_salario_minimo': variacion_salario_minimo,
                    'puntos_adicionales': puntos_adicionales,
                    'fuente_canon': canon_info.get('fuente', 'Automático'),
                    'fuente_puntos': fuente_puntos_info,
                    'contrato': contrato,
                    'fecha_aplicacion': fecha_aplicacion,
                    'observaciones': observaciones,
                    'canon_anterior_manual': canon_anterior_manual,
                    'alerta_otrosi': alerta_otrosi,
                    'user': request.user,
                }
                return render(request, 'gestion/salario_minimo/calcular_form.html', context)
            
            # Si se va a guardar
            if accion == 'guardar':
                aplicar_calculo = request.POST.get('aplicar_calculo')
                if not aplicar_calculo or aplicar_calculo not in ['si', 'no']:
                    form.add_error(None, 'Debe seleccionar si desea aplicar el cálculo ahora o solo guardarlo.')
                    canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
                    if canon_anterior_manual:
                        canon_info['fuente'] = 'Manual (Usuario)'
                    
                    fuente_porcentaje = obtener_fuente_porcentaje_salario_minimo(contrato, fecha_aplicacion)
                    
                    # Verificar si hay otro sí vigente con valor diferente
                    alerta_otrosi = None
                    if otrosi_info['existe'] and otrosi_info['valor_canon']:
                        valor_calculado = resultado['nuevo_canon']
                        valor_otrosi = otrosi_info['valor_canon']
                        if abs(valor_calculado - valor_otrosi) > Decimal('0.01'):  # Tolerancia de 1 centavo
                            alerta_otrosi = {
                                'existe': True,
                                'otrosi': otrosi_info['otrosi'],
                                'valor_otrosi': valor_otrosi,
                                'valor_calculado': valor_calculado,
                                'diferencia': abs(valor_calculado - valor_otrosi),
                            }
                    
                    context = {
                        'form': form,
                        'titulo': 'Calcular Ajuste por Salario Mínimo',
                        'mostrar_resultado': True,
                        'resultado': resultado,
                        'canon_anterior': canon_anterior,
                        'salario_minimo_historico': salario_minimo_historico,
                        'variacion_salario_minimo': variacion_salario_minimo,
                        'puntos_adicionales': puntos_adicionales,
                        'fuente_canon': canon_info.get('fuente', 'Automático'),
                        'fuente_puntos': fuente_puntos_info,
                        'contrato': contrato,
                        'fecha_aplicacion': fecha_aplicacion,
                        'observaciones': observaciones,
                        'canon_anterior_manual': canon_anterior_manual,
                        'alerta_otrosi': alerta_otrosi,
                        'user': request.user,
                    }
                    return render(request, 'gestion/salario_minimo/calcular_form.html', context)
                
                # Si es manual, mostrar alerta de confirmación
                if canon_anterior_manual:
                    request.session['calculo_salario_minimo_pendiente'] = {
                        'contrato_id': contrato.id,
                        'fecha_aplicacion': fecha_aplicacion.isoformat(),
                        'salario_minimo_historico_id': salario_minimo_historico.id,
                        'canon_anterior': str(canon_anterior),
                        'variacion_salario_minimo': str(variacion_salario_minimo),
                        'canon_anterior_manual': True,
                        'observaciones': observaciones,
                        'aplicar_calculo': aplicar_calculo,
                    }
                    return redirect('gestion:confirmar_calculo_salario_minimo')
                
                # Si no es manual, guardar directamente
                canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
                if canon_anterior_manual:
                    canon_info['fuente'] = 'Manual (Usuario)'
                
                # Preparar observaciones: agregar nota si se usó valor de Otro Sí
                observaciones_finales = observaciones
                if otrosi_info['existe'] and otrosi_info['valor_canon']:
                    valor_calculado_original = calcular_ajuste_salario_minimo(
                        canon_anterior,
                        variacion_salario_minimo,
                        puntos_adicionales
                    )['nuevo_canon']
                    if abs(valor_calculado_original - otrosi_info['valor_canon']) > Decimal('0.01'):
                        nota_otrosi = f"\n[Valor ajustado por Otro Sí {otrosi_info['otrosi'].numero_otrosi}: ${otrosi_info['valor_canon']:,.2f} (Cálculo SMLV: ${valor_calculado_original:,.2f})]"
                        observaciones_finales = (observaciones + nota_otrosi) if observaciones else nota_otrosi.strip()
                
                estado_calculo = 'APLICADO' if aplicar_calculo == 'si' else 'PENDIENTE'
                
                calculo = CalculoSalarioMinimo.objects.create(
                    contrato=contrato,
                    año_aplicacion=fecha_aplicacion.year,
                    fecha_aplicacion=fecha_aplicacion,
                    salario_minimo_historico=salario_minimo_historico,
                    canon_anterior=canon_anterior,
                    canon_anterior_manual=canon_anterior_manual,
                    fuente_canon_anterior=canon_info.get('fuente', 'Automático'),
                    porcentaje_salario_minimo=variacion_salario_minimo,
                    puntos_adicionales=puntos_adicionales,
                    porcentaje_total_aplicar=resultado['porcentaje_total'],
                    valor_incremento=resultado['valor_incremento'],
                    nuevo_canon=resultado['nuevo_canon'],
                    periodicidad_contrato=contrato.periodicidad_ipc,
                    fecha_aumento_contrato=contrato.fecha_aumento_ipc,
                    observaciones=observaciones_finales,
                    estado=estado_calculo,
                    calculado_por=request.user.get_full_name() or request.user.username,
                )
                
                if aplicar_calculo == 'si':
                    calculo.aplicado_por = request.user.get_full_name() or request.user.username
                    calculo.fecha_aplicacion_real = timezone.now()
                    calculo.save()
                    messages.success(request, f'Cálculo de Salario Mínimo guardado y aplicado exitosamente!')
                else:
                    messages.success(request, f'Cálculo de Salario Mínimo guardado exitosamente! El cálculo quedó pendiente para aplicar después.')
                
                return redirect('gestion:detalle_calculo_salario_minimo', calculo_id=calculo.id)
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        contrato_id = request.GET.get('contrato')
        año = request.GET.get('año', date.today().year)
        
        form = CalculoSalarioMinimoForm(user=request.user, contrato_initial=contrato_id)
        
        # Establecer fecha de aplicación por defecto como fecha actual
        form.initial['fecha_aplicacion'] = date.today()
        
        # Intentar obtener el Salario Mínimo del año automáticamente
        salario_minimo_historico = validar_salario_minimo_disponible(int(año))
        if salario_minimo_historico:
            form.initial['salario_minimo_historico'] = salario_minimo_historico.id
        else:
            messages.warning(
                request,
                f'No se encontró el Salario Mínimo del año {año}. '
                f'Por favor, agregue el Salario Mínimo histórico del año {año} primero.'
            )
        
        # Intentar obtener el canon automáticamente si hay un contrato seleccionado
        if contrato_id:
            try:
                contrato = Contrato.objects.get(id=contrato_id)
                # Inicializar el contrato en el formulario
                form.initial['contrato'] = contrato
                
                fecha_aplicacion_str = request.GET.get('fecha_aplicacion')
                if fecha_aplicacion_str:
                    fecha_aplicacion = date.fromisoformat(fecha_aplicacion_str)
                elif contrato.fecha_aumento_ipc:
                    fecha_aplicacion = date(
                        int(año),
                        contrato.fecha_aumento_ipc.month,
                        contrato.fecha_aumento_ipc.day
                    )
                else:
                    # Por defecto, usar la fecha actual
                    fecha_aplicacion = date.today()
                
                # Siempre establecer la fecha de aplicación
                form.initial['fecha_aplicacion'] = fecha_aplicacion
                
                canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
                if canon_info['canon']:
                    form.initial['canon_anterior'] = str(canon_info['canon'])
                    messages.info(request, f'Canon anterior sugerido desde: {canon_info["fuente"]}')
                
                # La variación se calcula automáticamente desde el salario mínimo histórico
                if salario_minimo_historico and salario_minimo_historico.variacion_porcentual:
                    form.initial['porcentaje_salario_minimo'] = salario_minimo_historico.variacion_porcentual
                    messages.info(request, f'Variación del Salario Mínimo {salario_minimo_historico.año}: {salario_minimo_historico.variacion_porcentual}%')
                elif salario_minimo_historico:
                    # Si no hay variación (primer año), intentar obtener del contrato
                    from gestion.utils_salario_minimo import obtener_fuente_porcentaje_salario_minimo
                    fuente_porcentaje_info = obtener_fuente_porcentaje_salario_minimo(contrato, fecha_aplicacion)
                    if fuente_porcentaje_info.get('porcentaje'):
                        form.initial['porcentaje_salario_minimo'] = fuente_porcentaje_info['porcentaje']
                        messages.info(request, f'No hay variación calculada (primer año). Usando porcentaje del contrato: {fuente_porcentaje_info["porcentaje"]}%')
            except (Contrato.DoesNotExist, ValueError):
                pass
    
    context = {
        'form': form,
        'titulo': 'Calcular Ajuste por Salario Mínimo',
        'user': request.user,
    }
    return render(request, 'gestion/salario_minimo/calcular_form.html', context)


@login_required_custom
def confirmar_calculo_salario_minimo(request):
    """Vista para confirmar el cálculo de Salario Mínimo con canon manual"""
    if 'calculo_salario_minimo_pendiente' not in request.session:
        messages.error(request, 'No hay cálculo pendiente de confirmación.')
        return redirect('gestion:calcular_salario_minimo')
    
    datos = request.session['calculo_salario_minimo_pendiente']
    contrato = get_object_or_404(Contrato, id=datos['contrato_id'])
    salario_minimo_historico = get_object_or_404(SalarioMinimoHistorico, id=datos['salario_minimo_historico_id'])
    fecha_aplicacion = date.fromisoformat(datos['fecha_aplicacion'])
    canon_anterior = Decimal(datos['canon_anterior'])
    variacion_salario_minimo = Decimal(datos['variacion_salario_minimo'])
    observaciones = datos.get('observaciones', '')
    aplicar_calculo = datos.get('aplicar_calculo', 'no')
    
    if request.method == 'POST':
        fuente_puntos_info = obtener_fuente_puntos_adicionales_salario_minimo(contrato, fecha_aplicacion)
        puntos_adicionales = fuente_puntos_info['puntos']
        resultado = calcular_ajuste_salario_minimo(
            canon_anterior,
            variacion_salario_minimo,
            puntos_adicionales
        )
        
        estado_calculo = 'APLICADO' if aplicar_calculo == 'si' else 'PENDIENTE'
        
        canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
        if datos.get('canon_anterior_manual'):
            canon_info['fuente'] = 'Manual (Usuario)'
        
        fuente_porcentaje = obtener_fuente_porcentaje_salario_minimo(contrato, fecha_aplicacion)
        
        # Preparar observaciones: agregar nota si se usó valor de Otro Sí
        observaciones_finales = observaciones
        if otrosi_info['existe'] and otrosi_info['valor_canon']:
            valor_calculado_original = calcular_ajuste_salario_minimo(
                canon_anterior,
                variacion_salario_minimo,
                puntos_adicionales
            )['nuevo_canon']
            if abs(valor_calculado_original - otrosi_info['valor_canon']) > Decimal('0.01'):
                nota_otrosi = f"\n[Valor ajustado por Otro Sí {otrosi_info['otrosi'].numero_otrosi}: ${otrosi_info['valor_canon']:,.2f} (Cálculo SMLV: ${valor_calculado_original:,.2f})]"
                observaciones_finales = (observaciones + nota_otrosi) if observaciones else nota_otrosi.strip()
        
        calculo = CalculoSalarioMinimo.objects.create(
            contrato=contrato,
            año_aplicacion=fecha_aplicacion.year,
            fecha_aplicacion=fecha_aplicacion,
            salario_minimo_historico=salario_minimo_historico,
            canon_anterior=canon_anterior,
            canon_anterior_manual=True,
            fuente_canon_anterior=canon_info.get('fuente', 'Manual (Usuario)'),
            porcentaje_salario_minimo=variacion_salario_minimo,
            puntos_adicionales=puntos_adicionales,
            porcentaje_total_aplicar=resultado['porcentaje_total'],
            valor_incremento=resultado['valor_incremento'],
            nuevo_canon=resultado['nuevo_canon'],
            periodicidad_contrato=contrato.periodicidad_ipc,
            fecha_aumento_contrato=contrato.fecha_aumento_ipc,
            observaciones=observaciones_finales,
            estado=estado_calculo,
            calculado_por=request.user.get_full_name() or request.user.username,
        )
        
        if aplicar_calculo == 'si':
            calculo.aplicado_por = request.user.get_full_name() or request.user.username
            calculo.fecha_aplicacion_real = timezone.now()
            calculo.save()
            messages.success(request, f'Cálculo de Salario Mínimo guardado y aplicado exitosamente!')
        else:
            messages.success(request, f'Cálculo de Salario Mínimo guardado exitosamente! El cálculo quedó pendiente para aplicar después.')
        
        del request.session['calculo_salario_minimo_pendiente']
        return redirect('gestion:detalle_calculo_salario_minimo', calculo_id=calculo.id)
    
    fuente_puntos_info = obtener_fuente_puntos_adicionales_salario_minimo(contrato, fecha_aplicacion)
    puntos_adicionales = fuente_puntos_info['puntos']
    resultado = calcular_ajuste_salario_minimo(
        canon_anterior,
        variacion_salario_minimo,
        puntos_adicionales
    )
    
    # Verificar si hay Otro Sí vigente y ajustar resultado si es necesario
    otrosi_info = verificar_otrosi_vigente_para_fecha(contrato, fecha_aplicacion)
    if otrosi_info['existe'] and otrosi_info['valor_canon']:
        valor_calculado_original = resultado['nuevo_canon']
        valor_otrosi = otrosi_info['valor_canon']
        if abs(valor_calculado_original - valor_otrosi) > Decimal('0.01'):
            diferencia = valor_otrosi - canon_anterior
            resultado['nuevo_canon'] = valor_otrosi
            resultado['valor_incremento'] = diferencia
            if canon_anterior > 0:
                porcentaje_aplicado = ((valor_otrosi / canon_anterior) - Decimal('1')) * Decimal('100')
                resultado['porcentaje_total'] = porcentaje_aplicado
    
    canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
    if datos.get('canon_anterior_manual'):
        canon_info['fuente'] = 'Manual (Usuario)'
    
    context = {
        'contrato': contrato,
        'salario_minimo_historico': salario_minimo_historico,
        'fecha_aplicacion': fecha_aplicacion,
        'canon_anterior': canon_anterior,
        'variacion_salario_minimo': variacion_salario_minimo,
        'puntos_adicionales': puntos_adicionales,
        'fuente_puntos': fuente_puntos_info,
        'fuente_canon': canon_info.get('fuente', 'Automático'),
        'resultado': resultado,
        'observaciones': observaciones,
        'aplicar_calculo': aplicar_calculo,
        'titulo': 'Confirmar Cálculo de Salario Mínimo',
    }
    return render(request, 'gestion/salario_minimo/confirmar_calculo.html', context)


@login_required_custom
def detalle_calculo_salario_minimo(request, calculo_id):
    """Vista para ver el detalle de un cálculo de Salario Mínimo"""
    calculo = get_object_or_404(CalculoSalarioMinimo, id=calculo_id)
    
    fuente_porcentaje = obtener_fuente_porcentaje_salario_minimo(calculo.contrato, calculo.fecha_aplicacion)
    fuente_puntos = obtener_fuente_puntos_adicionales_salario_minimo(calculo.contrato, calculo.fecha_aplicacion)
    
    context = {
        'calculo': calculo,
        'fuente_porcentaje': fuente_porcentaje,
        'fuente_puntos': fuente_puntos,
        'titulo': f'Cálculo Salario Mínimo {calculo.fecha_aplicacion.strftime("%d/%m/%Y")} - {calculo.contrato.num_contrato}',
    }
    return render(request, 'gestion/salario_minimo/calculo_detalle.html', context)


# Vista de edición deshabilitada - Los cálculos de Salario Mínimo no deben editarse
# @login_required_custom
# def editar_calculo_salario_minimo(request, calculo_id):
#     """Vista para editar un cálculo de Salario Mínimo existente"""
#     calculo = get_object_or_404(CalculoSalarioMinimo, id=calculo_id)
#     messages.error(request, 'La edición de cálculos de Salario Mínimo está deshabilitada. Si necesita corregir un cálculo, elimínelo y créelo nuevamente.')
#     return redirect('gestion:detalle_calculo_salario_minimo', calculo_id=calculo.id)


@admin_required
def eliminar_calculo_salario_minimo(request, calculo_id):
    """Vista para eliminar un cálculo de Salario Mínimo"""
    calculo = get_object_or_404(CalculoSalarioMinimo, id=calculo_id)
    
    if request.method == 'POST':
        contrato_num = calculo.contrato.num_contrato
        fecha = calculo.fecha_aplicacion.strftime("%d/%m/%Y")
        calculo.delete()
        messages.success(request, f'Cálculo de Salario Mínimo para el contrato {contrato_num} de la fecha {fecha} eliminado exitosamente!')
        # Redirigir a la vista de gestión de IPC para que se actualice la información
        return redirect('gestion:lista_ipc_historico')
    
    context = {
        'calculo': calculo,
        'titulo': f'Eliminar Cálculo Salario Mínimo {calculo.fecha_aplicacion.strftime("%d/%m/%Y")} - {calculo.contrato.num_contrato}',
    }
    return render(request, 'gestion/salario_minimo/eliminar_calculo.html', context)


@login_required_custom
def lista_calculos_salario_minimo(request):
    """Lista todos los cálculos de Salario Mínimo realizados"""
    calculos = CalculoSalarioMinimo.objects.all().order_by('-fecha_aplicacion', '-fecha_calculo')
    
    contrato_id = request.GET.get('contrato')
    año = request.GET.get('año')
    estado = request.GET.get('estado')
    
    if contrato_id:
        calculos = calculos.filter(contrato_id=contrato_id)
    if año:
        calculos = calculos.filter(año_aplicacion=int(año))
    if estado:
        calculos = calculos.filter(estado=estado)
    
    context = {
        'calculos': calculos,
        'titulo': 'Cálculos de Salario Mínimo',
    }
    return render(request, 'gestion/salario_minimo/calculos_lista.html', context)


@login_required_custom
def contratos_pendientes_salario_minimo(request):
    """Lista los contratos que requieren ajuste por Salario Mínimo"""
    contratos = obtener_contratos_pendientes_ajuste_salario_minimo()
    
    context = {
        'contratos': contratos,
        'titulo': 'Contratos Pendientes de Ajuste por Salario Mínimo',
    }
    return render(request, 'gestion/salario_minimo/contratos_pendientes.html', context)


@login_required_custom
def obtener_canon_anterior_salario_minimo_ajax(request):
    """Vista AJAX para obtener el canon anterior automáticamente"""
    if request.method == 'GET':
        contrato_id = request.GET.get('contrato_id')
        fecha_aplicacion_str = request.GET.get('fecha_aplicacion')
        
        if not contrato_id or not fecha_aplicacion_str:
            return JsonResponse({'error': 'Faltan parámetros'}, status=400)
        
        try:
            contrato = Contrato.objects.get(id=contrato_id)
            fecha_aplicacion = date.fromisoformat(fecha_aplicacion_str)
            
            canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
            
            if canon_info['canon']:
                canon_value = float(canon_info['canon'])
                return JsonResponse({
                    'canon': canon_value,
                    'fuente': canon_info['fuente'],
                    'es_manual': canon_info['es_manual'],
                })
            else:
                return JsonResponse({
                    'error': 'No se pudo obtener el canon anterior automáticamente'
                }, status=404)
        except Contrato.DoesNotExist:
            return JsonResponse({'error': 'Contrato no encontrado'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error en vista Salario Mínimo", exc_info=True)
            return JsonResponse({'error': 'Error procesando la solicitud. Por favor, intente nuevamente.'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required_custom
def obtener_variacion_salario_minimo_ajax(request):
    """Vista AJAX para obtener la variación porcentual de un Salario Mínimo Histórico"""
    if request.method == 'GET':
        try:
            salario_minimo_id = request.GET.get('salario_minimo_id')
            if not salario_minimo_id:
                return JsonResponse({'error': 'ID de Salario Mínimo no proporcionado'}, status=400)
            
            salario_minimo_historico = SalarioMinimoHistorico.objects.get(id=salario_minimo_id)
            
            variacion = salario_minimo_historico.variacion_porcentual
            if variacion is not None:
                return JsonResponse({
                    'variacion_porcentual': str(variacion),
                    'año': salario_minimo_historico.año
                })
            else:
                return JsonResponse({
                    'variacion_porcentual': None,
                    'año': salario_minimo_historico.año,
                    'mensaje': 'No hay variación calculada (primer año)'
                })
        except SalarioMinimoHistorico.DoesNotExist:
            return JsonResponse({'error': 'Salario Mínimo Histórico no encontrado'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error en obtener_variacion_salario_minimo_ajax", exc_info=True)
            return JsonResponse({'error': 'Error procesando la solicitud'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

