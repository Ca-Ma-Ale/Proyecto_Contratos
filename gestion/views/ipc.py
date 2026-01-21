"""
Vistas para el módulo de gestión de IPC
"""
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import IPCHistoricoForm, CalculoIPCForm, EditarCalculoIPCForm
from gestion.models import IPCHistorico, CalculoIPC, Contrato
from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
from gestion.utils_ipc import (
    obtener_canon_base_para_ipc,
    calcular_ajuste_ipc,
    obtener_contratos_pendientes_ajuste_ipc,
    validar_ipc_disponible,
    obtener_ultimo_calculo_ipc_contrato,
    obtener_fuente_puntos_adicionales,
    calcular_proxima_fecha_aumento,
    obtener_ultimo_calculo_ajuste,
)
from gestion.utils_formateo import limpiar_valor_numerico


@login_required_custom
def lista_ipc_historico(request):
    """Lista todos los contratos con acción de calcular IPC"""
    fecha_actual = date.today()
    
    tipo_filtro_activo = request.GET.get('tipo_contrato_cliente_proveedor', '')
    
    # Obtener todos los contratos activos
    contratos = Contrato.objects.filter(vigente=True).select_related(
        'arrendatario', 'proveedor', 'local', 'tipo_contrato', 'tipo_servicio'
    ).prefetch_related('otrosi').order_by('num_contrato')
    
    # Filtrar por tipo de contrato si se especifica
    if tipo_filtro_activo:
        contratos = contratos.filter(tipo_contrato_cliente_proveedor=tipo_filtro_activo)
    
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
        
        # Obtener fecha de aumento IPC considerando otrosí
        otrosi_fecha_ipc = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
            contrato, 'nueva_fecha_aumento_ipc', fecha_actual
        )
        if otrosi_fecha_ipc and otrosi_fecha_ipc.nueva_fecha_aumento_ipc:
            fecha_aumento_ipc = otrosi_fecha_ipc.nueva_fecha_aumento_ipc
        else:
            fecha_aumento_ipc = contrato.fecha_aumento_ipc
        
        # Calcular próxima fecha de aumento
        proxima_fecha_aumento = calcular_proxima_fecha_aumento(contrato, fecha_actual)
        
        # Obtener último cálculo de ajuste (IPC o Salario Mínimo)
        ultimo_calculo = obtener_ultimo_calculo_ajuste(contrato)
        
        contratos_info.append({
            'contrato': contrato,
            'fecha_final': fecha_final,
            'fecha_aumento_ipc': fecha_aumento_ipc,
            'proxima_fecha_aumento': proxima_fecha_aumento,
            'ultimo_calculo': ultimo_calculo,
        })
    
    context = {
        'contratos_info': contratos_info,
        'titulo': 'Gestión de IPC - Contratos',
        'fecha_actual': fecha_actual,
        'tipo_filtro_activo': tipo_filtro_activo,
    }
    return render(request, 'gestion/ipc/contratos_lista.html', context)


@login_required_custom
def historico_ipc_valores(request):
    """Lista el histórico completo de valores del IPC"""
    ipc_historico = IPCHistorico.objects.all().order_by('-año')
    
    context = {
        'ipc_historico': ipc_historico,
        'titulo': 'Histórico de IPC',
    }
    return render(request, 'gestion/ipc/historico_lista.html', context)


@admin_required
def nuevo_ipc_historico(request):
    """Vista para agregar un nuevo valor de IPC histórico"""
    if request.method == 'POST':
        form = IPCHistoricoForm(request.POST)
        
        if form.is_valid():
            ipc = form.save(commit=False)
            ipc.creado_por = request.user.get_full_name() or request.user.username
            ipc.save()
            messages.success(request, f'IPC {ipc.año} ({ipc.valor_ipc}%) agregado exitosamente!')
            return redirect('gestion:historico_ipc_valores')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = IPCHistoricoForm()
    
    context = {
        'form': form,
        'titulo': 'Nuevo IPC Histórico',
    }
    return render(request, 'gestion/ipc/historico_form.html', context)


@admin_required
def editar_ipc_historico(request, ipc_id):
    """Vista para editar un valor de IPC histórico"""
    ipc = get_object_or_404(IPCHistorico, id=ipc_id)
    
    if request.method == 'POST':
        form = IPCHistoricoForm(request.POST, instance=ipc)
        
        if form.is_valid():
            ipc = form.save(commit=False)
            ipc.modificado_por = request.user.get_full_name() or request.user.username
            ipc.save()
            messages.success(request, f'IPC {ipc.año} actualizado exitosamente!')
            return redirect('gestion:historico_ipc_valores')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = IPCHistoricoForm(instance=ipc)
    
    context = {
        'form': form,
        'ipc': ipc,
        'titulo': f'Editar IPC {ipc.año}',
    }
    return render(request, 'gestion/ipc/historico_form.html', context)


@admin_required
def eliminar_ipc_historico(request, ipc_id):
    """Vista para eliminar un valor de IPC histórico"""
    ipc = get_object_or_404(IPCHistorico, id=ipc_id)
    
    if request.method == 'POST':
        año = ipc.año
        ipc.delete()
        messages.success(request, f'IPC {año} eliminado exitosamente!')
        return redirect('gestion:historico_ipc_valores')
    
    # Verificar si hay cálculos que usan este IPC
    calculos = CalculoIPC.objects.filter(ipc_historico=ipc)
    
    context = {
        'ipc': ipc,
        'calculos': calculos,
        'titulo': f'Eliminar IPC {ipc.año}',
    }
    return render(request, 'gestion/ipc/historico_eliminar.html', context)


@login_required_custom
def calcular_ipc(request):
    """Vista para calcular el ajuste de canon por IPC"""
    if request.method == 'POST':
        form = CalculoIPCForm(request.POST, user=request.user)
        accion = request.POST.get('accion', 'calcular')  # 'calcular' o 'guardar'
        
        if form.is_valid():
            contrato = form.cleaned_data['contrato']
            fecha_aplicacion = form.cleaned_data['fecha_aplicacion']
            ipc_historico = form.cleaned_data['ipc_historico']
            canon_anterior_manual = form.cleaned_data.get('canon_anterior_manual', False)
            canon_anterior = form.cleaned_data.get('canon_anterior')
            observaciones = form.cleaned_data.get('observaciones', '')
            
            # Si no es manual y no hay canon, obtenerlo automáticamente
            if not canon_anterior_manual and not canon_anterior:
                canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
                if canon_info['canon']:
                    canon_anterior = canon_info['canon']
                    # Mostrar mensaje informativo sobre la fuente del canon
                    messages.info(request, f'Canon anterior obtenido automáticamente desde: {canon_info["fuente"]}')
                else:
                    # Si no se puede obtener automáticamente, sugerir ingresarlo manualmente
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
                            f'El contrato {contrato.num_contrato} no tiene canon fijo ni canon mínimo garantizado registrado. '
                            f'Por favor, contacte a un administrador para ingresar el canon anterior manualmente.'
                        )
                    form.add_error(None, 'No se pudo obtener el canon anterior automáticamente. Por favor, ingréselo manualmente.')
                    context = {'form': form, 'titulo': 'Calcular Ajuste por IPC', 'user': request.user}
                    return render(request, 'gestion/ipc/calcular_form.html', context)
            
            # Validar que el canon anterior esté presente
            if not canon_anterior:
                form.add_error('canon_anterior', 'El canon anterior es requerido.')
                context = {'form': form, 'titulo': 'Calcular Ajuste por IPC', 'user': request.user}
                return render(request, 'gestion/ipc/calcular_form.html', context)
            
            # Obtener puntos adicionales considerando OtroSi (efecto cadena)
            fuente_puntos_info = obtener_fuente_puntos_adicionales(contrato, fecha_aplicacion)
            puntos_adicionales = fuente_puntos_info['puntos']
            
            # Calcular el ajuste
            resultado = calcular_ajuste_ipc(
                canon_anterior,
                ipc_historico.valor_ipc,
                puntos_adicionales
            )
            
            # Si solo se calcula, mostrar resultado sin guardar
            if accion == 'calcular':
                # Obtener información del canon anterior
                canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
                if canon_anterior_manual:
                    canon_info['fuente'] = 'Manual (Usuario)'
                
                # Obtener la fuente de los puntos adicionales
                fuente_puntos = obtener_fuente_puntos_adicionales(contrato, fecha_aplicacion)
                
                context = {
                    'form': form,
                    'titulo': 'Calcular Ajuste por IPC',
                    'mostrar_resultado': True,
                    'resultado': resultado,
                    'canon_anterior': canon_anterior,
                    'ipc_historico': ipc_historico,
                    'puntos_adicionales': puntos_adicionales,
                    'fuente_canon': canon_info.get('fuente', 'Automático'),
                    'fuente_puntos': fuente_puntos,
                    'contrato': contrato,
                    'fecha_aplicacion': fecha_aplicacion,
                    'observaciones': observaciones,
                    'canon_anterior_manual': canon_anterior_manual,
                    'user': request.user,
                }
                return render(request, 'gestion/ipc/calcular_form.html', context)
            
            # Si se va a guardar (desde el botón "Guardar Cálculo" en los resultados)
            if accion == 'guardar':
                # Obtener si se desea aplicar el cálculo (obligatorio)
                aplicar_calculo = request.POST.get('aplicar_calculo')
                if not aplicar_calculo or aplicar_calculo not in ['si', 'no']:
                    form.add_error(None, 'Debe seleccionar si desea aplicar el cálculo ahora o solo guardarlo.')
                    # Obtener información del canon anterior
                    canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
                    if canon_anterior_manual:
                        canon_info['fuente'] = 'Manual (Usuario)'
                    
                    # Obtener la fuente de los puntos adicionales
                    fuente_puntos = obtener_fuente_puntos_adicionales(contrato, fecha_aplicacion)
                    
                    context = {
                        'form': form,
                        'titulo': 'Calcular Ajuste por IPC',
                        'mostrar_resultado': True,
                        'resultado': resultado,
                        'canon_anterior': canon_anterior,
                        'ipc_historico': ipc_historico,
                        'puntos_adicionales': puntos_adicionales,
                        'fuente_canon': canon_info.get('fuente', 'Automático'),
                        'fuente_puntos': fuente_puntos,
                        'contrato': contrato,
                        'fecha_aplicacion': fecha_aplicacion,
                        'observaciones': observaciones,
                        'canon_anterior_manual': canon_anterior_manual,
                        'user': request.user,
                    }
                    return render(request, 'gestion/ipc/calcular_form.html', context)
                
                # Si es manual, mostrar alerta de confirmación
                if canon_anterior_manual:
                    # Guardar en sesión para confirmación
                    request.session['calculo_ipc_pendiente'] = {
                        'contrato_id': contrato.id,
                        'fecha_aplicacion': fecha_aplicacion.isoformat(),
                        'ipc_historico_id': ipc_historico.id,
                        'canon_anterior': str(canon_anterior),
                        'canon_anterior_manual': True,
                        'observaciones': observaciones,
                        'aplicar_calculo': aplicar_calculo,
                    }
                    return redirect('gestion:confirmar_calculo_ipc')
                
                # Si no es manual, guardar directamente
                canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
                if canon_anterior_manual:
                    canon_info['fuente'] = 'Manual (Usuario)'
                
                # Determinar el estado según la respuesta
                estado_calculo = 'APLICADO' if aplicar_calculo == 'si' else 'PENDIENTE'
                
                calculo = CalculoIPC.objects.create(
                    contrato=contrato,
                    año_aplicacion=fecha_aplicacion.year,
                    fecha_aplicacion=fecha_aplicacion,
                    ipc_historico=ipc_historico,
                    canon_anterior=canon_anterior,
                    canon_anterior_manual=canon_anterior_manual,
                    fuente_canon_anterior=canon_info.get('fuente', 'Automático'),
                    puntos_adicionales=puntos_adicionales,
                    porcentaje_total_aplicar=resultado['porcentaje_total'],
                    valor_incremento=resultado['valor_incremento'],
                    nuevo_canon=resultado['nuevo_canon'],
                    periodicidad_contrato=contrato.periodicidad_ipc,
                    fecha_aumento_contrato=contrato.fecha_aumento_ipc,
                    observaciones=observaciones,
                    estado=estado_calculo,
                    calculado_por=request.user.get_full_name() or request.user.username,
                )
                
                # Si se debe aplicar, registrar la aplicación
                if aplicar_calculo == 'si':
                    calculo.aplicado_por = request.user.get_full_name() or request.user.username
                    calculo.fecha_aplicacion_real = timezone.now()
                    calculo.save()
                    
                    messages.success(request, f'Cálculo de IPC guardado y aplicado exitosamente! El ajuste ha sido registrado como aplicado.')
                else:
                    messages.success(request, f'Cálculo de IPC guardado exitosamente! El cálculo quedó pendiente para aplicar después.')
                
                return redirect('gestion:detalle_calculo_ipc', calculo_id=calculo.id)
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        contrato_id = request.GET.get('contrato')
        año = request.GET.get('año', date.today().year)
        
        form = CalculoIPCForm(
            contrato_initial=contrato_id,
            año_initial=año,
            user=request.user
        )
        
        # Intentar obtener el canon automáticamente si hay un contrato seleccionado
        if contrato_id:
            try:
                contrato = Contrato.objects.get(id=contrato_id)
                
                # Detectar tipo de contrato y cargar histórico correspondiente
                if contrato.tipo_condicion_ipc == 'SALARIO_MINIMO':
                    # Si es Salario Mínimo, redirigir a la vista de cálculo de Salario Mínimo
                    from gestion.utils_salario_minimo import validar_salario_minimo_disponible
                    salario_minimo_historico = validar_salario_minimo_disponible(int(año))
                    if salario_minimo_historico:
                        return redirect(f"{reverse('gestion:calcular_salario_minimo')}?contrato={contrato_id}&año={año}")
                    else:
                        messages.warning(
                            request,
                            f'No se encontró el Salario Mínimo del año {año}. '
                            f'Por favor, agregue el Salario Mínimo histórico del año {año} primero.'
                        )
                        return redirect('gestion:lista_ipc_historico')
                
                # Si es IPC, continuar con el flujo normal
                # Intentar obtener fecha_aplicacion de los parámetros GET o usar fecha_aumento_ipc del contrato
                fecha_aplicacion_str = request.GET.get('fecha_aplicacion')
                if fecha_aplicacion_str:
                    fecha_aplicacion = date.fromisoformat(fecha_aplicacion_str)
                elif contrato.fecha_aumento_ipc:
                    # Usar la fecha_aumento_ipc del contrato para el año actual
                    fecha_aplicacion = date(
                        int(año),
                        contrato.fecha_aumento_ipc.month,
                        contrato.fecha_aumento_ipc.day
                    )
                else:
                    fecha_aplicacion = None
                
                if fecha_aplicacion:
                    form.initial['fecha_aplicacion'] = fecha_aplicacion
                    canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
                    if canon_info['canon']:
                        # Pre-llenar el campo canon_anterior en el formulario
                        form.initial['canon_anterior'] = str(canon_info['canon'])
                        messages.info(request, f'Canon anterior sugerido desde: {canon_info["fuente"]}')
                    else:
                        if request.user.is_staff:
                            messages.warning(
                                request,
                                f'No se pudo obtener el canon anterior automáticamente para el contrato {contrato.num_contrato}. '
                                f'Por favor, marque "Ingresar Canon Anterior Manualmente" e ingrese el valor.'
                            )
                        else:
                            messages.warning(
                                request,
                                f'No se pudo obtener el canon anterior automáticamente para el contrato {contrato.num_contrato}. '
                                f'Por favor, contacte a un administrador para ingresar el canon anterior manualmente.'
                            )
                
                # Intentar obtener el IPC del año anterior automáticamente
                año_ipc_requerido = int(año) - 1
                ipc_historico = validar_ipc_disponible(int(año))
                if ipc_historico:
                    form.initial['ipc_historico'] = ipc_historico.id
                else:
                    messages.warning(
                        request,
                        f'No se encontró el IPC del año {año_ipc_requerido} (requerido para aplicar en {año}). '
                        f'Por favor, agregue el IPC histórico del año {año_ipc_requerido} primero.'
                    )
            except (Contrato.DoesNotExist, ValueError):
                pass
        else:
            # Si no hay contrato seleccionado, intentar obtener el IPC del año anterior automáticamente
            año_ipc_requerido = int(año) - 1
            ipc_historico = validar_ipc_disponible(int(año))
            if ipc_historico:
                form.initial['ipc_historico'] = ipc_historico.id
            else:
                messages.warning(
                    request,
                    f'No se encontró el IPC del año {año_ipc_requerido} (requerido para aplicar en {año}). '
                    f'Por favor, agregue el IPC histórico del año {año_ipc_requerido} primero.'
                )
    
    context = {
        'form': form,
        'titulo': 'Calcular Ajuste por IPC',
        'user': request.user,
    }
    return render(request, 'gestion/ipc/calcular_form.html', context)


@login_required_custom
def confirmar_calculo_ipc(request):
    """Vista para confirmar el cálculo de IPC con canon manual"""
    if 'calculo_ipc_pendiente' not in request.session:
        messages.error(request, 'No hay cálculo pendiente de confirmación.')
        return redirect('gestion:calcular_ipc')
    
    datos = request.session['calculo_ipc_pendiente']
    contrato = get_object_or_404(Contrato, id=datos['contrato_id'])
    ipc_historico = get_object_or_404(IPCHistorico, id=datos['ipc_historico_id'])
    fecha_aplicacion_str = datos.get('fecha_aplicacion')
    if fecha_aplicacion_str:
        fecha_aplicacion = date.fromisoformat(fecha_aplicacion_str)
    else:
        año_aplicacion = datos.get('año_aplicacion')
        mes_aplicacion = datos.get('mes_aplicacion', 'ENERO')
        from gestion.utils_ipc import _mes_a_numero
        mes_num = _mes_a_numero(mes_aplicacion)
        fecha_aplicacion = date(año_aplicacion, mes_num, 1)
    canon_anterior = Decimal(datos['canon_anterior'])
    observaciones = datos.get('observaciones', '')
    aplicar_calculo = datos.get('aplicar_calculo', 'no')
    
    if request.method == 'POST':
        # Calcular el ajuste
        fuente_puntos_info = obtener_fuente_puntos_adicionales(contrato, fecha_aplicacion)
        puntos_adicionales = fuente_puntos_info['puntos']
        resultado = calcular_ajuste_ipc(
            canon_anterior,
            ipc_historico.valor_ipc,
            puntos_adicionales
        )
        
        # Determinar el estado según la respuesta
        estado_calculo = 'APLICADO' if aplicar_calculo == 'si' else 'PENDIENTE'
        
        # Obtener información del canon anterior
        canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
        if datos.get('canon_anterior_manual'):
            canon_info['fuente'] = 'Manual (Usuario)'
        
        # Crear el cálculo
        calculo = CalculoIPC.objects.create(
            contrato=contrato,
            año_aplicacion=fecha_aplicacion.year,
            fecha_aplicacion=fecha_aplicacion,
            ipc_historico=ipc_historico,
            canon_anterior=canon_anterior,
            canon_anterior_manual=True,
            fuente_canon_anterior=canon_info.get('fuente', 'Manual (Usuario)'),
            puntos_adicionales=puntos_adicionales,
            porcentaje_total_aplicar=resultado['porcentaje_total'],
            valor_incremento=resultado['valor_incremento'],
            nuevo_canon=resultado['nuevo_canon'],
            periodicidad_contrato=contrato.periodicidad_ipc,
            fecha_aumento_contrato=contrato.fecha_aumento_ipc,
            observaciones=observaciones,
            estado=estado_calculo,
            calculado_por=request.user.get_full_name() or request.user.username,
        )
        
        # Si se debe aplicar, registrar la aplicación
        if aplicar_calculo == 'si':
            calculo.aplicado_por = request.user.get_full_name() or request.user.username
            calculo.fecha_aplicacion_real = timezone.now()
            calculo.save()
            
            messages.success(request, f'Cálculo de IPC guardado y aplicado exitosamente! El ajuste ha sido registrado como aplicado.')
        else:
            messages.success(request, f'Cálculo de IPC guardado exitosamente! El cálculo quedó pendiente para aplicar después.')
        
        # Limpiar sesión
        del request.session['calculo_ipc_pendiente']
        
        return redirect('gestion:detalle_calculo_ipc', calculo_id=calculo.id)
    
    # Calcular valores para mostrar en la confirmación
    fuente_puntos_info = obtener_fuente_puntos_adicionales(contrato, fecha_aplicacion)
    puntos_adicionales = fuente_puntos_info['puntos']
    resultado = calcular_ajuste_ipc(
        canon_anterior,
        ipc_historico.valor_ipc,
        puntos_adicionales
    )
    canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
    if datos.get('canon_anterior_manual'):
        canon_info['fuente'] = 'Manual (Usuario)'
    
    context = {
        'contrato': contrato,
        'ipc_historico': ipc_historico,
        'fecha_aplicacion': fecha_aplicacion,
        'canon_anterior': canon_anterior,
        'puntos_adicionales': puntos_adicionales,
        'fuente_puntos': fuente_puntos_info,
        'fuente_canon': canon_info.get('fuente', 'Automático'),
        'resultado': resultado,
        'observaciones': observaciones,
        'aplicar_calculo': aplicar_calculo,
        'titulo': 'Confirmar Cálculo de IPC',
    }
    return render(request, 'gestion/ipc/confirmar_calculo.html', context)


@login_required_custom
def detalle_calculo_ipc(request, calculo_id):
    """Vista para ver el detalle de un cálculo de IPC"""
    calculo = get_object_or_404(CalculoIPC, id=calculo_id)
    
    # Obtener la fuente de los puntos adicionales
    fuente_puntos = obtener_fuente_puntos_adicionales(calculo.contrato, calculo.fecha_aplicacion)
    
    context = {
        'calculo': calculo,
        'fuente_puntos': fuente_puntos,
        'titulo': f'Cálculo IPC {calculo.fecha_aplicacion.strftime("%d/%m/%Y")} - {calculo.contrato.num_contrato}',
    }
    return render(request, 'gestion/ipc/calculo_detalle.html', context)


@login_required_custom
def editar_calculo_ipc(request, calculo_id):
    """Vista para editar un cálculo de IPC existente"""
    calculo = get_object_or_404(CalculoIPC, id=calculo_id)
    
    if request.method == 'POST':
        form = EditarCalculoIPCForm(request.POST, instance=calculo)
        if form.is_valid():
            # Obtener valores calculados del formulario
            porcentaje_total = form.cleaned_data.get('_porcentaje_total')
            valor_incremento = form.cleaned_data.get('_valor_incremento')
            nuevo_canon = form.cleaned_data.get('_nuevo_canon')
            
            # Actualizar campos calculados
            if porcentaje_total is not None:
                calculo.porcentaje_total_aplicar = porcentaje_total
            if valor_incremento is not None:
                calculo.valor_incremento = valor_incremento
            if nuevo_canon is not None:
                calculo.nuevo_canon = nuevo_canon
            
            # Guardar el cálculo
            calculo.save()
            
            messages.success(request, 'Cálculo de IPC actualizado exitosamente!')
            return redirect('gestion:detalle_calculo_ipc', calculo_id=calculo.id)
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = EditarCalculoIPCForm(instance=calculo)
    
    context = {
        'form': form,
        'calculo': calculo,
        'titulo': f'Editar Cálculo IPC {calculo.fecha_aplicacion.strftime("%d/%m/%Y")} - {calculo.contrato.num_contrato}',
    }
    return render(request, 'gestion/ipc/editar_calculo.html', context)


@admin_required
def eliminar_calculo_ipc(request, calculo_id):
    """Vista para eliminar un cálculo de IPC"""
    calculo = get_object_or_404(CalculoIPC, id=calculo_id)
    
    if request.method == 'POST':
        contrato_num = calculo.contrato.num_contrato
        fecha = calculo.fecha_aplicacion.strftime("%d/%m/%Y")
        calculo.delete()
        messages.success(request, f'Cálculo de IPC para el contrato {contrato_num} de la fecha {fecha} eliminado exitosamente!')
        # Redirigir a la vista de gestión de IPC para que se actualice la información
        return redirect('gestion:lista_ipc_historico')
    
    context = {
        'calculo': calculo,
        'titulo': f'Eliminar Cálculo IPC {calculo.fecha_aplicacion.strftime("%d/%m/%Y")} - {calculo.contrato.num_contrato}',
    }
    return render(request, 'gestion/ipc/eliminar_calculo.html', context)


@login_required_custom
def lista_calculos_ipc(request):
    """Lista todos los cálculos de IPC y Salario Mínimo realizados"""
    from gestion.models import CalculoSalarioMinimo
    
    # Obtener tipo de filtro del segmentador
    tipo_filtro = request.GET.get('tipo_calculo', '')
    tipo_contrato_filtro = request.GET.get('tipo_contrato_cliente_proveedor', '')
    
    # Filtros comunes
    contrato_id = request.GET.get('contrato')
    año = request.GET.get('año')
    estado_filtro = request.GET.get('estado_filtro', 'PENDIENTE')  # Por defecto mostrar pendientes
    
    # Obtener cálculos de IPC
    calculos_ipc = CalculoIPC.objects.all().select_related('contrato', 'ipc_historico', 'contrato__arrendatario', 'contrato__proveedor').order_by('-fecha_aplicacion', '-fecha_calculo')
    
    # Obtener cálculos de Salario Mínimo
    calculos_salario_minimo = CalculoSalarioMinimo.objects.all().select_related('contrato', 'salario_minimo_historico', 'contrato__arrendatario', 'contrato__proveedor').order_by('-fecha_aplicacion', '-fecha_calculo')
    
    # Aplicar filtros comunes a IPC
    if contrato_id:
        calculos_ipc = calculos_ipc.filter(contrato_id=contrato_id)
    if año:
        calculos_ipc = calculos_ipc.filter(año_aplicacion=int(año))
    
    # Aplicar filtro de estado (pendientes por defecto)
    if estado_filtro == 'PENDIENTE':
        calculos_ipc = calculos_ipc.filter(estado='PENDIENTE')
    elif estado_filtro == 'APLICADO':
        calculos_ipc = calculos_ipc.filter(estado='APLICADO')
    # Si es 'TODOS', no filtrar por estado
    
    # Aplicar filtros comunes a Salario Mínimo
    if contrato_id:
        calculos_salario_minimo = calculos_salario_minimo.filter(contrato_id=contrato_id)
    if año:
        calculos_salario_minimo = calculos_salario_minimo.filter(año_aplicacion=int(año))
    
    # Aplicar filtro de estado (pendientes por defecto)
    if estado_filtro == 'PENDIENTE':
        calculos_salario_minimo = calculos_salario_minimo.filter(estado='PENDIENTE')
    elif estado_filtro == 'APLICADO':
        calculos_salario_minimo = calculos_salario_minimo.filter(estado='APLICADO')
    # Si es 'TODOS', no filtrar por estado
    
    # Filtrar por tipo de contrato (Cliente/Proveedor)
    if tipo_contrato_filtro == 'CLIENTE':
        calculos_ipc = calculos_ipc.filter(contrato__tipo_contrato_cliente_proveedor='CLIENTE')
        calculos_salario_minimo = calculos_salario_minimo.filter(contrato__tipo_contrato_cliente_proveedor='CLIENTE')
    elif tipo_contrato_filtro == 'PROVEEDOR':
        calculos_ipc = calculos_ipc.filter(contrato__tipo_contrato_cliente_proveedor='PROVEEDOR')
        calculos_salario_minimo = calculos_salario_minimo.filter(contrato__tipo_contrato_cliente_proveedor='PROVEEDOR')
    
    # Filtrar según el segmentador de tipo de cálculo
    if tipo_filtro == 'IPC':
        calculos_salario_minimo = CalculoSalarioMinimo.objects.none()
    elif tipo_filtro == 'SALARIO_MINIMO':
        calculos_ipc = CalculoIPC.objects.none()
    # Si tipo_filtro está vacío o es 'TODOS', mostrar ambos
    
    context = {
        'calculos_ipc': calculos_ipc,
        'calculos_salario_minimo': calculos_salario_minimo,
        'tipo_filtro_activo': tipo_filtro,
        'tipo_contrato_filtro_activo': tipo_contrato_filtro,
        'estado_filtro_activo': estado_filtro,
        'titulo': 'Cálculos de Ajustes',
    }
    return render(request, 'gestion/ipc/calculos_lista.html', context)


@login_required_custom
def contratos_pendientes_ipc(request):
    """Lista los contratos que requieren ajuste por IPC"""
    contratos = obtener_contratos_pendientes_ajuste_ipc()
    
    context = {
        'contratos': contratos,
        'titulo': 'Contratos Pendientes de Ajuste por IPC',
    }
    return render(request, 'gestion/ipc/contratos_pendientes.html', context)


@login_required_custom
def obtener_canon_anterior_ajax(request):
    """Vista AJAX para obtener el canon anterior automáticamente"""
    if request.method == 'GET':
        contrato_id = request.GET.get('contrato_id')
        fecha_aplicacion_str = request.GET.get('fecha_aplicacion')
        
        if not contrato_id or not fecha_aplicacion_str:
            return JsonResponse({'error': 'Faltan parámetros'}, status=400)
        
        try:
            contrato = Contrato.objects.get(id=contrato_id)
            fecha_aplicacion = date.fromisoformat(fecha_aplicacion_str)
            
            canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
            
            if canon_info['canon']:
                # Convertir Decimal a float para JSON (sin formato)
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
            logger.error("Error en vista IPC", exc_info=True)
            return JsonResponse({'error': 'Error procesando la solicitud. Por favor, intente nuevamente.'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)
