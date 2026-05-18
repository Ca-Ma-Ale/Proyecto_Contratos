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
from gestion.services.chain_validation import auditar_cambio as _auditar_cambio
from gestion.services.exportes import (
    ColumnaExportacion,
    ExportacionVaciaError,
    generar_excel_corporativo,
)
from gestion.forms import IPCHistoricoForm, CalculoIPCForm, EditarCalculoIPCForm
from gestion.models import IPCHistorico, CalculoIPC, Contrato
from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
from gestion.views.utils import _obtener_fecha_final_contrato, _respuesta_archivo_excel
from gestion.utils_ipc import (
    obtener_canon_base_para_ipc,
    calcular_ajuste_ipc,
    obtener_contratos_pendientes_ajuste_ipc,
    validar_ipc_disponible,
    obtener_ultimo_calculo_ipc_contrato,
    obtener_fuente_puntos_adicionales,
    calcular_proxima_fecha_aumento,
    obtener_ultimo_calculo_ajuste,
    obtener_configuracion_ajuste_efectiva,
    obtener_ultimo_calculo_desde_cache,
    requiere_revision_configuracion_ajuste,
    verificar_otrosi_vigente_para_fecha,
    verificar_calculo_existente_para_fecha,
    obtener_otrosi_para_legalizar,
)
from gestion.utils_formateo import limpiar_valor_numerico
from gestion.models import obtener_nombre_tipo_condicion_ipc, obtener_nombre_periodicidad_ipc


@login_required_custom
def lista_ipc_historico(request):
    """Lista todos los contratos con acción de calcular IPC"""
    fecha_actual = date.today()
    
    tipo_filtro_activo = request.GET.get('tipo_contrato_cliente_proveedor', '')
    estado_filtro = request.GET.get('estado_filtro', 'PENDIENTE')
    mostrar_al_dia = request.GET.get('mostrar_al_dia', '') == '1'
    
    # Obtener todos los contratos activos — prefetch otrosi Y renovaciones para evitar N+1
    contratos = Contrato.objects.filter(vigente=True).select_related(
        'arrendatario', 'proveedor', 'local', 'tipo_contrato', 'tipo_servicio'
    ).prefetch_related('otrosi', 'renovaciones_automaticas').order_by('num_contrato')

    # Filtrar por tipo de contrato si se especifica
    if tipo_filtro_activo:
        contratos = contratos.filter(tipo_contrato_cliente_proveedor=tipo_filtro_activo)

    # Materializar queryset una sola vez
    contratos_list = list(contratos)

    # Bulk-fetch último CalculoIPC y CalculoSalarioMinimo por contrato (2 queries en total)
    from gestion.models import CalculoSalarioMinimo
    contrato_ids = [c.id for c in contratos_list]

    _ultimos_ipc = {}
    for c in CalculoIPC.objects.filter(
        contrato_id__in=contrato_ids
    ).order_by('contrato_id', '-fecha_aplicacion', '-fecha_calculo'):
        if c.contrato_id not in _ultimos_ipc:
            _ultimos_ipc[c.contrato_id] = c

    _ultimos_sm = {}
    for c in CalculoSalarioMinimo.objects.filter(
        contrato_id__in=contrato_ids
    ).order_by('contrato_id', '-fecha_aplicacion', '-fecha_calculo'):
        if c.contrato_id not in _ultimos_sm:
            _ultimos_sm[c.contrato_id] = c

    # Preparar información de cada contrato (sin queries adicionales por contrato)
    contratos_info = []
    for contrato in contratos_list:
        fecha_final = _obtener_fecha_final_contrato(contrato, fecha_actual)

        # Obtener fecha de aumento IPC considerando otrosí
        config_ajuste = obtener_configuracion_ajuste_efectiva(
            contrato, fecha_actual
        )
        fecha_aumento_ipc = config_ajuste['fecha_aumento_ipc']

        # Obtener tipo_condicion_ipc efectivo considerando otrosí
        tipo_condicion_ipc = config_ajuste['tipo_condicion_ipc']

        # Excluir contratos sin ajuste IPC configurado, a menos que ya tengan un
        # cálculo APLICADO — esos deben aparecer con badge de revisión.
        if not tipo_condicion_ipc:
            _u = _ultimos_ipc.get(contrato.id)
            if not (_u and _u.estado == 'APLICADO'):
                continue

        # Obtener periodicidad_ipc efectiva considerando otrosí
        periodicidad_ipc = config_ajuste['periodicidad_ipc']

        # Calcular próxima fecha de aumento usando caché de cálculos (sin queries)
        ultimo_ipc_c = _ultimos_ipc.get(contrato.id)
        ultimo_sm_c = _ultimos_sm.get(contrato.id)
        proxima_fecha_aumento = calcular_proxima_fecha_aumento(
            contrato, fecha_actual, _calculos_cache=(ultimo_ipc_c, ultimo_sm_c)
        )

        # Determinar último cálculo desde caché (evita 2 queries adicionales)
        ultimo_calculo = obtener_ultimo_calculo_desde_cache(
            ultimo_ipc_c, ultimo_sm_c
        )

        requiere_revision_ipc = requiere_revision_configuracion_ajuste(
            ultimo_calculo,
            **config_ajuste,
        )

        contratos_info.append({
            'contrato': contrato,
            'fecha_final': fecha_final,
            'fecha_aumento_ipc': fecha_aumento_ipc,
            'proxima_fecha_aumento': proxima_fecha_aumento,
            'ultimo_calculo': ultimo_calculo,
            'tipo_condicion_ipc': tipo_condicion_ipc,
            'tipo_condicion_ipc_display': obtener_nombre_tipo_condicion_ipc(tipo_condicion_ipc) if tipo_condicion_ipc else None,
            'periodicidad_ipc': periodicidad_ipc,
            'periodicidad_ipc_display': obtener_nombre_periodicidad_ipc(periodicidad_ipc) if periodicidad_ipc else None,
            'requiere_revision_ipc': requiere_revision_ipc,
        })
    
    # Marcar "al día" primero (sobre todos los contratos) para que el filtro PENDIENTE lo use
    for info in contratos_info:
        ultimo = info['ultimo_calculo']
        proxima = info['proxima_fecha_aumento']
        info['es_al_dia'] = (
            ultimo is not None
            and getattr(ultimo, 'estado', None) == 'APLICADO'
            and ultimo.fecha_aplicacion.year == fecha_actual.year
            and proxima is not None
            and proxima.year > fecha_actual.year
        )

    count_al_dia = sum(1 for info in contratos_info if info['es_al_dia'])

    # Filtrar por estado
    if estado_filtro == 'PENDIENTE':
        # Pendiente = no al día (IPC no aplicado en el año actual con próxima fecha cubierta)
        contratos_info = [info for info in contratos_info if not info['es_al_dia']]
    elif estado_filtro == 'APLICADO':
        contratos_info = [
            info for info in contratos_info
            if info['ultimo_calculo'] and info['ultimo_calculo'].estado == 'APLICADO'
        ]
    # 'TODOS': no filtrar por estado

    # En TODOS/APLICADO, ocultar al día por defecto salvo que el usuario lo pida
    if estado_filtro != 'PENDIENTE' and not mostrar_al_dia:
        contratos_info = [info for info in contratos_info if not info['es_al_dia']]

    # Ordenar por próxima fecha de aumento: vencidos primero (más antiguos al tope),
    # luego futuros de más próximo a más lejano. Sin fecha al final.
    contratos_info.sort(key=lambda x: (
        x['proxima_fecha_aumento'] is None,
        x['proxima_fecha_aumento'] if x['proxima_fecha_aumento'] is not None else date.max,
    ))

    context = {
        'contratos_info': contratos_info,
        'titulo': 'Gestión de IPC - Contratos',
        'fecha_actual': fecha_actual,
        'tipo_filtro_activo': tipo_filtro_activo,
        'estado_filtro_activo': estado_filtro,
        'mostrar_al_dia': mostrar_al_dia,
        'count_al_dia': count_al_dia,
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
    # Obtener contrato_id y año disponibles en GET y POST
    if request.method == 'POST':
        contrato_id = request.POST.get('contrato')
        año = request.POST.get('año_aplicacion', date.today().year)
    else:
        contrato_id = request.GET.get('contrato')
        año = request.GET.get('año', date.today().year)

    if request.method == 'POST':
        form = CalculoIPCForm(request.POST, user=request.user, contrato_initial=request.POST.get('contrato'))
        accion = request.POST.get('accion', 'calcular')  # 'calcular' o 'guardar'
        
        # Manejar confirmación de legalización (lee desde sesión, no requiere form válido)
        if accion == 'confirmar_legalizacion':
            datos = request.session.get('legalizacion_ipc_pendiente')
            if not datos:
                messages.error(request, 'No hay legalización pendiente de confirmación.')
                return redirect('gestion:calcular_ipc')

            valor_elegido = request.POST.get('valor_elegido')
            if valor_elegido not in ('otrosi', 'ipc'):
                messages.error(request, 'Debe seleccionar qué valor registrar.')
                return redirect('gestion:calcular_ipc')

            contrato = get_object_or_404(Contrato, id=datos['contrato_id'])
            ipc_historico = get_object_or_404(IPCHistorico, id=datos['ipc_historico_id'])
            otrosi = get_object_or_404(
                __import__('gestion.models', fromlist=['OtroSi']).OtroSi,
                id=datos['otrosi_id'],
                contrato=contrato,
                estado='APROBADO'
            )

            canon_anterior = Decimal(datos['canon_anterior'])
            canon_otrosi = Decimal(datos['canon_otrosi'])
            nuevo_canon_ipc = Decimal(datos['nuevo_canon_ipc'])
            puntos_adicionales = Decimal(datos['puntos_adicionales'])
            fuente_canon_anterior = datos['fuente_canon_anterior']

            if valor_elegido == 'otrosi':
                nuevo_canon_final = canon_otrosi
            else:
                nuevo_canon_final = nuevo_canon_ipc

            valor_incremento = nuevo_canon_final - canon_anterior
            if canon_anterior > 0:
                porcentaje_total = ((nuevo_canon_final / canon_anterior) - Decimal('1')) * Decimal('100')
            else:
                porcentaje_total = Decimal('0')

            otrosi_effective_from = date.fromisoformat(datos['otrosi_effective_from'])
            label_valor = 'Otro Sí' if valor_elegido == 'otrosi' else 'Cálculo IPC'
            observaciones_legalizacion = (
                f'Legalizado vía Otro Sí versión {otrosi.version} '
                f'(effective_from: {otrosi_effective_from.strftime("%d/%m/%Y")}). '
                f'Valor registrado: {label_valor}.'
            )

            from gestion.models import OtroSi
            _cfg_leg = obtener_configuracion_ajuste_efectiva(contrato, otrosi_effective_from)
            calculo = CalculoIPC.objects.create(
                contrato=contrato,
                año_aplicacion=otrosi_effective_from.year,
                fecha_aplicacion=otrosi_effective_from,
                ipc_historico=ipc_historico,
                canon_anterior=canon_anterior.quantize(Decimal('0.01')),
                canon_anterior_manual=False,
                fuente_canon_anterior=fuente_canon_anterior,
                puntos_adicionales=puntos_adicionales,
                porcentaje_total_aplicar=porcentaje_total.quantize(Decimal('0.01')),
                valor_incremento=valor_incremento.quantize(Decimal('0.01')),
                nuevo_canon=nuevo_canon_final.quantize(Decimal('0.01')),
                periodicidad_contrato=_cfg_leg.get('periodicidad_ipc') or contrato.periodicidad_ipc,
                fecha_aumento_contrato=_cfg_leg.get('fecha_aumento_ipc') or contrato.fecha_aumento_ipc,
                observaciones=observaciones_legalizacion,
                estado='APLICADO',
                otrosi_referencia=otrosi,
                legalizado_via_otrosi=True,
                calculado_por=request.user.get_full_name() or request.user.username,
                aplicado_por=request.user.get_full_name() or request.user.username,
                fecha_aplicacion_real=timezone.now(),
            )

            del request.session['legalizacion_ipc_pendiente']
            messages.success(
                request,
                f'Ajuste por IPC legalizado exitosamente mediante el Otro Sí versión {otrosi.version}. '
                f'Nuevo canon registrado: ${nuevo_canon_final:,.2f}'
            )
            return redirect('gestion:detalle_calculo_ipc', calculo_id=calculo.id)

        # Mostrar comparativa de valores antes de confirmar legalización
        if accion == 'ver_comparativa':
            from gestion.models import OtroSi
            contrato_id_post = request.POST.get('contrato')
            ipc_historico_id_post = request.POST.get('ipc_historico')
            otrosi_id = request.POST.get('otrosi_id')

            if not otrosi_id:
                messages.error(request, 'Debe seleccionar un Otro Sí para legalizar.')
                return redirect(
                    f"{reverse('gestion:calcular_ipc')}?contrato={contrato_id_post or ''}"
                )

            contrato_leg = get_object_or_404(Contrato, id=contrato_id_post)
            ipc_historico_leg = get_object_or_404(IPCHistorico, id=ipc_historico_id_post)

            try:
                otrosi_sel = OtroSi.objects.get(id=otrosi_id, contrato=contrato_leg, estado='APROBADO')
            except OtroSi.DoesNotExist:
                messages.error(request, 'El Otro Sí seleccionado no es válido.')
                return redirect('gestion:calcular_ipc')

            # Canon base calculado para la fecha del Otro Sí
            canon_info_leg = obtener_canon_base_para_ipc(contrato_leg, otrosi_sel.effective_from)
            canon_base = canon_info_leg['canon']
            fuente_canon = canon_info_leg.get('fuente', 'Automático')

            # Puntos adicionales vigentes para esa fecha
            fuente_puntos_leg = obtener_fuente_puntos_adicionales(contrato_leg, otrosi_sel.effective_from)
            puntos_adicionales_leg = fuente_puntos_leg['puntos']

            # Canon del Otro Sí
            canon_otrosi = otrosi_sel.nuevo_valor_canon or otrosi_sel.nuevo_canon_minimo_garantizado

            if canon_base and canon_base > 0:
                porcentaje_real = ((canon_otrosi / canon_base) - Decimal('1')) * Decimal('100')
            else:
                porcentaje_real = Decimal('0')

            # Cálculo teórico por IPC
            resultado_ipc_leg = calcular_ajuste_ipc(
                canon_base, ipc_historico_leg.valor_ipc, puntos_adicionales_leg
            )
            nuevo_canon_ipc = resultado_ipc_leg['nuevo_canon']
            porcentaje_ipc = resultado_ipc_leg['porcentaje_total']

            request.session['legalizacion_ipc_pendiente'] = {
                'contrato_id': contrato_leg.id,
                'ipc_historico_id': ipc_historico_leg.id,
                'otrosi_id': otrosi_sel.id,
                'otrosi_effective_from': otrosi_sel.effective_from.isoformat(),
                'canon_anterior': str(canon_base),
                'canon_otrosi': str(canon_otrosi),
                'nuevo_canon_ipc': str(nuevo_canon_ipc),
                'puntos_adicionales': str(puntos_adicionales_leg),
                'fuente_canon_anterior': fuente_canon,
                'porcentaje_real': str(porcentaje_real.quantize(Decimal('0.0001'))),
                'porcentaje_ipc': str(porcentaje_ipc),
            }

            context = {
                'titulo': 'Legalizar Ajuste IPC vía Otro Sí',
                'contrato': contrato_leg,
                'otrosi': otrosi_sel,
                'ipc_historico': ipc_historico_leg,
                'canon_anterior': canon_base,
                'fuente_canon': fuente_canon,
                'canon_otrosi': canon_otrosi,
                'porcentaje_real': porcentaje_real,
                'nuevo_canon_ipc': nuevo_canon_ipc,
                'porcentaje_ipc': porcentaje_ipc,
                'puntos_adicionales': puntos_adicionales_leg,
                'user': request.user,
            }
            return render(request, 'gestion/ipc/comparativa_legalizacion.html', context)

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
            
            # Verificar si existe un Otro Sí vigente que modifica el canon para esta fecha
            otrosi_info = verificar_otrosi_vigente_para_fecha(contrato, fecha_aplicacion)
            
            # Calcular el ajuste
            resultado = calcular_ajuste_ipc(
                canon_anterior,
                ipc_historico.valor_ipc,
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
                # Obtener información del canon anterior
                canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
                if canon_anterior_manual:
                    canon_info['fuente'] = 'Manual (Usuario)'
                
                # Obtener la fuente de los puntos adicionales
                fuente_puntos = obtener_fuente_puntos_adicionales(contrato, fecha_aplicacion)
                
                # Verificar si hay otro sí vigente con valor diferente
                alerta_otrosi = None
                continuar_desde_advertencia = request.POST.get('continuar_desde_advertencia')
                
                if otrosi_info['existe'] and otrosi_info['valor_canon']:
                    # Calcular el valor original antes del ajuste
                    resultado_original = calcular_ajuste_ipc(
                        canon_anterior,
                        ipc_historico.valor_ipc,
                        puntos_adicionales
                    )
                    valor_calculado_original = resultado_original['nuevo_canon']
                    valor_otrosi = otrosi_info['valor_canon']
                    
                    if abs(valor_calculado_original - valor_otrosi) > Decimal('0.01'):  # Tolerancia de 1 centavo
                        alerta_otrosi = {
                            'existe': True,
                            'otrosi': otrosi_info['otrosi'],
                            'valor_otrosi': valor_otrosi,
                            'valor_calculado': valor_calculado_original,
                            'diferencia': abs(valor_calculado_original - valor_otrosi),
                        }
                        
                        # Si no viene desde la advertencia, mostrar el template de advertencia
                        if not continuar_desde_advertencia:
                            context = {
                                'alerta_otrosi': alerta_otrosi,
                                'contrato': contrato,
                                'fecha_aplicacion': fecha_aplicacion,
                                'ipc_historico': ipc_historico,
                                'canon_anterior': canon_anterior,
                                'canon_anterior_manual': canon_anterior_manual,
                                'observaciones': observaciones,
                                'titulo': 'Advertencia - Otro Sí Vigente',
                            }
                            return render(request, 'gestion/ipc/advertencia_otrosi.html', context)
                
                # Si viene desde la advertencia, mostrar mensaje informativo
                if continuar_desde_advertencia and alerta_otrosi:
                    messages.success(
                        request,
                        f'✅ Valor ajustado automáticamente: Se utilizará ${alerta_otrosi["valor_otrosi"]:,.2f} '
                        f'del Otro Sí {alerta_otrosi["otrosi"].numero_otrosi} en lugar del valor calculado '
                        f'(${alerta_otrosi["valor_calculado"]:,.2f}).'
                    )
                
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
                    'alerta_otrosi': alerta_otrosi,
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
                        'alerta_otrosi': alerta_otrosi,
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
                
                # Preparar observaciones: agregar nota si se usó valor de Otro Sí
                observaciones_finales = observaciones
                if otrosi_info['existe'] and otrosi_info['valor_canon']:
                    valor_calculado_original = calcular_ajuste_ipc(
                        canon_anterior,
                        ipc_historico.valor_ipc,
                        puntos_adicionales
                    )['nuevo_canon']
                    if abs(valor_calculado_original - otrosi_info['valor_canon']) > Decimal('0.01'):
                        nota_otrosi = f"\n[Valor ajustado por Otro Sí {otrosi_info['otrosi'].numero_otrosi}: ${otrosi_info['valor_canon']:,.2f} (Cálculo IPC: ${valor_calculado_original:,.2f})]"
                        observaciones_finales = (observaciones + nota_otrosi) if observaciones else nota_otrosi.strip()
                
                _cfg_calc = obtener_configuracion_ajuste_efectiva(contrato, fecha_aplicacion)
                calculo = CalculoIPC.objects.create(
                    contrato=contrato,
                    año_aplicacion=fecha_aplicacion.year,
                    fecha_aplicacion=fecha_aplicacion,
                    ipc_historico=ipc_historico,
                    canon_anterior=Decimal(str(canon_anterior)).quantize(Decimal('0.01')),
                    canon_anterior_manual=canon_anterior_manual,
                    fuente_canon_anterior=canon_info.get('fuente', 'Automático'),
                    puntos_adicionales=puntos_adicionales,
                    porcentaje_total_aplicar=Decimal(str(resultado['porcentaje_total'])).quantize(Decimal('0.01')),
                    valor_incremento=Decimal(str(resultado['valor_incremento'])).quantize(Decimal('0.01')),
                    nuevo_canon=Decimal(str(resultado['nuevo_canon'])).quantize(Decimal('0.01')),
                    periodicidad_contrato=_cfg_calc.get('periodicidad_ipc') or contrato.periodicidad_ipc,
                    fecha_aumento_contrato=_cfg_calc.get('fecha_aumento_ipc') or contrato.fecha_aumento_ipc,
                    observaciones=observaciones_finales,
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
    
    # Detectar OtroSís disponibles para legalizar (solo cuando hay contrato)
    otrosi_legalizables = None
    hay_otrosi_para_legalizar = False
    if contrato_id:
        try:
            contrato_obj = Contrato.objects.get(id=contrato_id)
            año_buscar = int(año)
            otrosi_legalizables = obtener_otrosi_para_legalizar(contrato_obj, año_buscar)
            hay_otrosi_para_legalizar = otrosi_legalizables.exists()
        except (Contrato.DoesNotExist, ValueError):
            pass

    context = {
        'form': form,
        'titulo': 'Calcular Ajuste por IPC',
        'user': request.user,
        'otrosi_legalizables': otrosi_legalizables,
        'hay_otrosi_para_legalizar': hay_otrosi_para_legalizar,
        'año_aplicacion': año,
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
                nota_otrosi = f"\n[Valor ajustado por Otro Sí {otrosi_info['otrosi'].numero_otrosi}: ${valor_otrosi:,.2f} (Cálculo IPC: ${valor_calculado_original:,.2f})]"
                observaciones = (observaciones + nota_otrosi) if observaciones else nota_otrosi.strip()
        
        # Crear el cálculo
        _cfg_manual = obtener_configuracion_ajuste_efectiva(contrato, fecha_aplicacion)
        calculo = CalculoIPC.objects.create(
            contrato=contrato,
            año_aplicacion=fecha_aplicacion.year,
            fecha_aplicacion=fecha_aplicacion,
            ipc_historico=ipc_historico,
            canon_anterior=canon_anterior.quantize(Decimal('0.01')),
            canon_anterior_manual=True,
            fuente_canon_anterior=canon_info.get('fuente', 'Manual (Usuario)'),
            puntos_adicionales=puntos_adicionales,
            porcentaje_total_aplicar=Decimal(str(resultado['porcentaje_total'])).quantize(Decimal('0.01')),
            valor_incremento=Decimal(str(resultado['valor_incremento'])).quantize(Decimal('0.01')),
            nuevo_canon=Decimal(str(resultado['nuevo_canon'])).quantize(Decimal('0.01')),
            periodicidad_contrato=_cfg_manual.get('periodicidad_ipc') or contrato.periodicidad_ipc,
            fecha_aumento_contrato=_cfg_manual.get('fecha_aumento_ipc') or contrato.fecha_aumento_ipc,
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



@admin_required
def eliminar_calculo_ipc(request, calculo_id):
    """Vista para eliminar un cálculo de IPC"""
    from gestion.models import DependenciaDocumento
    calculo = get_object_or_404(CalculoIPC, id=calculo_id)

    # ── Efecto Cadena: informar qué bloqueos se liberarán ────────────────────
    bloqueos_a_liberar = list(
        DependenciaDocumento.objects.filter(
            bloqueador_tipo='CALCULO_IPC',
            bloqueador_id=calculo.pk,
        ).values('campo_bloqueado', 'label_campo', 'bloqueado_tipo', 'bloqueado_id')
    )

    if request.method == 'POST':
        contrato_num = calculo.contrato.num_contrato
        fecha = calculo.fecha_aplicacion.strftime('%d/%m/%Y')

        # Auditar eliminación
        _auditar_cambio(
            tipo_documento='CONTRATO',
            documento_id=calculo.contrato_id,
            documento_descripcion=f"Contrato {contrato_num}",
            nombre_campo='calculo_ipc_eliminado',
            valor_anterior=f'CalculoIPC #{calculo.pk} — {fecha} — ${calculo.nuevo_canon:,.0f}',
            valor_nuevo=None,
            modificado_por=request.user.get_username(),
            causa_tipo='ELIMINACION_OTROSI',  # reutilizamos causa más cercana
            causa_descripcion=f'Cálculo IPC eliminado. Liberados {len(bloqueos_a_liberar)} bloqueo(s).',
            ip_origen=request.META.get('REMOTE_ADDR'),
        )

        # post_delete signal libera automáticamente las DependenciaDocumento
        calculo.delete()
        msg = f'Cálculo de IPC para el contrato {contrato_num} de la fecha {fecha} eliminado exitosamente!'
        if bloqueos_a_liberar:
            msg += f' Se liberaron {len(bloqueos_a_liberar)} bloqueo(s) de campos.'
        messages.success(request, msg)
        return redirect('gestion:lista_ipc_historico')

    context = {
        'calculo': calculo,
        'titulo': f'Eliminar Cálculo IPC {calculo.fecha_aplicacion.strftime("%d/%m/%Y")} - {calculo.contrato.num_contrato}',
        'bloqueos_a_liberar': bloqueos_a_liberar,
    }
    return render(request, 'gestion/ipc/eliminar_calculo.html', context)


def _obtener_querysets_calculos_ajustes(filtros):
    from gestion.models import CalculoSalarioMinimo

    tipo_filtro = filtros.get('tipo_calculo', '')
    tipo_contrato_filtro = filtros.get('tipo_contrato_cliente_proveedor', '')
    contrato_id = filtros.get('contrato')
    año = filtros.get('año')
    estado = filtros.get('estado')

    calculos_ipc = CalculoIPC.objects.select_related(
        'contrato', 'ipc_historico', 'contrato__arrendatario', 'contrato__proveedor'
    ).order_by('-fecha_aplicacion', '-fecha_calculo')
    calculos_salario_minimo = CalculoSalarioMinimo.objects.select_related(
        'contrato', 'salario_minimo_historico', 'contrato__arrendatario', 'contrato__proveedor'
    ).order_by('-fecha_aplicacion', '-fecha_calculo')

    if contrato_id:
        calculos_ipc = calculos_ipc.filter(contrato_id=contrato_id)
        calculos_salario_minimo = calculos_salario_minimo.filter(contrato_id=contrato_id)

    if año:
        calculos_salario_minimo = calculos_salario_minimo.filter(año_aplicacion=int(año))
        calculos_ipc = calculos_ipc.filter(año_aplicacion=int(año))

    if estado:
        calculos_ipc = calculos_ipc.filter(estado=estado)
        calculos_salario_minimo = calculos_salario_minimo.filter(estado=estado)

    if tipo_contrato_filtro == 'CLIENTE':
        calculos_ipc = calculos_ipc.filter(contrato__tipo_contrato_cliente_proveedor='CLIENTE')
        calculos_salario_minimo = calculos_salario_minimo.filter(contrato__tipo_contrato_cliente_proveedor='CLIENTE')
    elif tipo_contrato_filtro == 'PROVEEDOR':
        calculos_ipc = calculos_ipc.filter(contrato__tipo_contrato_cliente_proveedor='PROVEEDOR')
        calculos_salario_minimo = calculos_salario_minimo.filter(contrato__tipo_contrato_cliente_proveedor='PROVEEDOR')

    if tipo_filtro == 'IPC':
        calculos_salario_minimo = CalculoSalarioMinimo.objects.none()
    elif tipo_filtro == 'SALARIO_MINIMO':
        calculos_ipc = CalculoIPC.objects.none()

    return calculos_ipc, calculos_salario_minimo


def _contratos_para_filtro_calculos():
    return Contrato.objects.filter(
        Q(calculos_ipc__isnull=False) | Q(calculos_salario_minimo__isnull=False)
    ).distinct().order_by('num_contrato')


@login_required_custom
def lista_calculos_ipc(request):
    """Lista todos los cálculos de IPC y Salario Mínimo realizados"""
    calculos_ipc, calculos_salario_minimo = _obtener_querysets_calculos_ajustes(request.GET)
    tipo_filtro = request.GET.get('tipo_calculo', '')
    tipo_contrato_filtro = request.GET.get('tipo_contrato_cliente_proveedor', '')

    context = {
        'calculos_ipc': calculos_ipc,
        'calculos_salario_minimo': calculos_salario_minimo,
        'contratos_filtro': _contratos_para_filtro_calculos(),
        'tipo_filtro_activo': tipo_filtro,
        'tipo_contrato_filtro_activo': tipo_contrato_filtro,
        'titulo': 'Cálculos de Ajustes',
    }
    return render(request, 'gestion/ipc/calculos_lista.html', context)


def _fila_exportacion_calculo_ajuste(calculo, tipo, indicador):
    return (
        tipo,
        calculo.contrato.num_contrato,
        calculo.contrato.obtener_nombre_tercero(),
        calculo.contrato.get_tipo_contrato_cliente_proveedor_display(),
        calculo.fecha_aplicacion.strftime('%d/%m/%Y'),
        calculo.año_aplicacion,
        float(indicador),
        float(calculo.canon_anterior),
        float(calculo.valor_incremento),
        float(calculo.nuevo_canon),
        calculo.get_estado_display(),
        timezone.localtime(calculo.fecha_calculo).strftime('%d/%m/%Y %H:%M'),
    )


def _filas_exportacion_calculos_ajustes(calculos_ipc, calculos_salario_minimo):
    filas = [
        _fila_exportacion_calculo_ajuste(
            calculo, 'IPC', calculo.ipc_historico.valor_ipc
        )
        for calculo in calculos_ipc
    ]
    filas.extend(
        _fila_exportacion_calculo_ajuste(
            calculo, 'Salario Mínimo', calculo.porcentaje_total_aplicar
        )
        for calculo in calculos_salario_minimo
    )
    return sorted(filas, key=lambda fila: (fila[4], fila[11]), reverse=True)


@login_required_custom
def exportar_calculos_ajustes_excel(request):
    """Exporta a Excel los cálculos de IPC y Salario Mínimo con los filtros activos."""
    calculos_ipc, calculos_salario_minimo = _obtener_querysets_calculos_ajustes(request.GET)
    columnas = [
        ColumnaExportacion('Tipo', ancho=18),
        ColumnaExportacion('Contrato', ancho=34),
        ColumnaExportacion('Tercero', ancho=42),
        ColumnaExportacion('Tipo Contrato', ancho=18),
        ColumnaExportacion('Fecha Aplicación', ancho=18),
        ColumnaExportacion('Año', ancho=12, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Indicador (%)', ancho=16, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Canon Anterior', ancho=18, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Incremento', ancho=18, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Nuevo Canon', ancho=18, es_numerica=True, alineacion='right'),
        ColumnaExportacion('Estado', ancho=16),
        ColumnaExportacion('Fecha Cálculo', ancho=20),
    ]
    registros = _filas_exportacion_calculos_ajustes(
        calculos_ipc, calculos_salario_minimo
    )

    try:
        archivo = generar_excel_corporativo(
            nombre_hoja='Cálculos Ajustes',
            columnas=columnas,
            registros=registros,
        )
    except ExportacionVaciaError as error:
        messages.warning(request, str(error))
        return redirect('gestion:lista_calculos_ipc')

    return _respuesta_archivo_excel(archivo, 'calculos_ajustes')


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
        except ValueError:
            return JsonResponse({'error': 'Fecha inválida'}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Error en vista IPC", exc_info=True)
            return JsonResponse({'error': 'Error procesando la solicitud. Por favor, intente nuevamente.'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required_custom
def otrosi_legalizables_ipc_ajax(request):
    """Retorna JSON con los OtroSí legalizables para un contrato y año dados (para IPC)."""
    contrato_id = request.GET.get('contrato_id')
    fecha_str = request.GET.get('fecha')

    if not contrato_id or not fecha_str:
        return JsonResponse({'otrosi': [], 'hay_otrosi': False})

    try:
        contrato = Contrato.objects.get(id=contrato_id)
        año = date.fromisoformat(fecha_str).year
        otrosi_qs = obtener_otrosi_para_legalizar(contrato, año)
        otrosi_list = [
            {
                'pk': os.pk,
                'version': os.version,
                'effective_from': os.effective_from.strftime('%d/%m/%Y'),
                'nuevo_valor_canon': str(os.nuevo_valor_canon) if os.nuevo_valor_canon else None,
                'nuevo_canon_minimo_garantizado': str(os.nuevo_canon_minimo_garantizado) if os.nuevo_canon_minimo_garantizado else None,
            }
            for os in otrosi_qs
        ]
        return JsonResponse({'otrosi': otrosi_list, 'hay_otrosi': bool(otrosi_list), 'año': año})
    except (Contrato.DoesNotExist, ValueError):
        return JsonResponse({'otrosi': [], 'hay_otrosi': False})


@login_required_custom
def ipc_historico_por_anio_ajax(request):
    """
    Retorna el registro de IPCHistorico correspondiente al año anterior a la fecha dada.
    Ej: si fecha_aplicacion es 2025-03-01, retorna el IPC del año 2024.
    """
    fecha_str = request.GET.get('fecha_aplicacion')
    if not fecha_str:
        return JsonResponse({'encontrado': False})

    try:
        año_aplicacion = date.fromisoformat(fecha_str).year
        año_ipc = año_aplicacion - 1
        ipc = IPCHistorico.objects.get(año=año_ipc)
        return JsonResponse({
            'encontrado': True,
            'id': ipc.id,
            'año': ipc.año,
            'valor_ipc': str(ipc.valor_ipc),
            'label': str(ipc),
        })
    except IPCHistorico.DoesNotExist:
        año_ipc = date.fromisoformat(fecha_str).year - 1
        return JsonResponse({'encontrado': False, 'año_requerido': año_ipc})
    except ValueError:
        return JsonResponse({'encontrado': False})
