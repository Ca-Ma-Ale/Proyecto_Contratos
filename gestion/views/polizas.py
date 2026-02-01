from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import PolizaForm
from gestion.models import Contrato, Poliza, SeguimientoPoliza, SeguimientoContrato, OtroSi, RenovacionAutomatica
from gestion.utils import calcular_fecha_vencimiento
from gestion.utils_otrosi import get_vista_vigente_contrato, get_polizas_vigentes, es_fecha_fuera_vigencia_contrato, get_polizas_requeridas_contrato
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion
from .utils import _construir_requisitos_poliza, _aplicar_polizas_vigentes_a_requisitos


def _obtener_requisitos_por_documento(contrato, documento_origen_id):
    """
    Obtiene los requisitos de pólizas según el documento origen seleccionado.
    
    Args:
        contrato: Instancia del modelo Contrato
        documento_origen_id: ID del documento origen ('CONTRATO', 'OTROSI_X', 'RENOVACION_X')
    
    Returns:
        Diccionario con los requisitos de pólizas
    """
    fecha_referencia = date.today()
    
    # Determinar fecha de referencia según documento origen
    if documento_origen_id.startswith('OTROSI_'):
        otrosi_id = int(documento_origen_id.split('_')[1])
        try:
            otrosi = OtroSi.objects.get(id=otrosi_id, contrato=contrato)
            if otrosi.effective_from:
                fecha_referencia = otrosi.effective_from
        except OtroSi.DoesNotExist:
            pass
    elif documento_origen_id.startswith('RENOVACION_'):
        renovacion_id = int(documento_origen_id.split('_')[1])
        try:
            renovacion = RenovacionAutomatica.objects.get(id=renovacion_id, contrato=contrato)
            if renovacion.effective_from:
                fecha_referencia = renovacion.effective_from
        except RenovacionAutomatica.DoesNotExist:
            pass
    
    # Obtener requisitos usando get_polizas_requeridas_contrato con la fecha de referencia correcta
    polizas_requeridas = get_polizas_requeridas_contrato(contrato, fecha_referencia, permitir_fuera_vigencia=True)
    
    # Construir estructura de requisitos
    vista_vigente = get_vista_vigente_contrato(contrato, fecha_referencia)
    # Asegurar que fecha_referencia esté en el diccionario vista_vigente
    if 'fecha_referencia' not in vista_vigente:
        vista_vigente['fecha_referencia'] = fecha_referencia
    requisitos = _construir_requisitos_poliza(contrato, vista_vigente, permitir_fuera_vigencia=True)
    
    return requisitos


@login_required_custom
def obtener_requisitos_documento(request, contrato_id):
    """Vista AJAX para obtener requisitos según documento origen seleccionado"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    documento_origen_id = request.GET.get('documento_origen', 'CONTRATO')
    
    requisitos = _obtener_requisitos_por_documento(contrato, documento_origen_id)
    
    # Convertir a formato JSON-friendly
    requisitos_json = {}
    try:
        for clave, valor in requisitos.items():
            if isinstance(valor, dict):
                fecha_inicio_str = None
                fecha_fin_str = None
                
                if valor.get('fecha_inicio'):
                    fecha_obj = valor.get('fecha_inicio')
                    if hasattr(fecha_obj, 'isoformat'):
                        fecha_inicio_str = fecha_obj.isoformat()
                    elif isinstance(fecha_obj, str):
                        fecha_inicio_str = fecha_obj
                
                if valor.get('fecha_fin'):
                    fecha_obj = valor.get('fecha_fin')
                    if hasattr(fecha_obj, 'isoformat'):
                        fecha_fin_str = fecha_obj.isoformat()
                    elif isinstance(fecha_obj, str):
                        fecha_fin_str = fecha_obj
                
                requisitos_json[clave] = {
                    'exigida': valor.get('exigida', False),
                    'valor': float(valor.get('valor', 0)) if valor.get('valor') else None,
                    'vigencia': valor.get('vigencia'),
                    'fecha_inicio': fecha_inicio_str,
                    'fecha_fin': fecha_fin_str,
                    'detalles': valor.get('detalles', {}),
                    'nombre': valor.get('nombre') if clave == 'otra' else None
                }
            else:
                requisitos_json[clave] = valor
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error al convertir requisitos a JSON: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse(requisitos_json)


@login_required_custom
def gestionar_polizas(request, contrato_id):
    """Vista para gestionar las pólizas de un contrato"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    vista_vigente = get_vista_vigente_contrato(contrato)
    vista_vigente['fecha_final_mostrar'] = (
        vista_vigente.get('fecha_final_actualizada')
        or contrato.fecha_final_actualizada
        or contrato.fecha_final_inicial
    )
    # Permitir gestionar pólizas incluso si el contrato aún no ha iniciado
    requisitos_contrato = _construir_requisitos_poliza(contrato, vista_vigente, permitir_fuera_vigencia=True)
    polizas_vigentes = get_polizas_vigentes(contrato)
    requisitos_contrato = _aplicar_polizas_vigentes_a_requisitos(requisitos_contrato, polizas_vigentes)
    requerimientos_poliza = contrato.requerimientos_poliza.all()
    polizas = contrato.polizas.all()
    
    # Auditoría de pólizas
    auditoria_polizas = []
    for poliza in polizas:
        validacion = poliza.cumple_requisitos_contrato()
        auditoria_polizas.append({
            'poliza': poliza,
            'validacion': validacion
        })
    
    # Verificar si faltan pólizas requeridas (usar requisitos_contrato que ya considera OtroSi vigente)
    pólizas_requeridas = []
    if requisitos_contrato['rce']['exigida']:
        pólizas_requeridas.append('RCE - Responsabilidad Civil')
    if requisitos_contrato['cumplimiento']['exigida']:
        pólizas_requeridas.append('Cumplimiento')
    if requisitos_contrato['arrendamiento']['exigida']:
        pólizas_requeridas.append('Poliza de Arrendamiento')
    if requisitos_contrato['todo_riesgo']['exigida']:
        pólizas_requeridas.append('Arrendamiento')
    if requisitos_contrato['otra']['exigida']:
        nombre_otra = requisitos_contrato['otra'].get('nombre') or 'Otra'
        pólizas_requeridas.append(nombre_otra)
    
    pólizas_aportadas_tipos = [p.tipo for p in polizas]
    pólizas_faltantes = [tipo for tipo in pólizas_requeridas if tipo not in pólizas_aportadas_tipos]
    
    # Verificar si el contrato aún no ha iniciado
    contrato_no_iniciado = es_fecha_fuera_vigencia_contrato(contrato, date.today())
    
    # Buscar Otros Sí futuros que modifiquen pólizas (para mostrar información al usuario)
    otrosi_futuro_polizas = None
    if contrato_no_iniciado:
        otrosi_futuro = OtroSi.objects.filter(
            contrato=contrato,
            estado='APROBADO',
            modifica_polizas=True,
            effective_from__gt=date.today()
        ).order_by('effective_from').first()
        
        if otrosi_futuro:
            otrosi_futuro_polizas = otrosi_futuro
    
    # Obtener seguimientos de pólizas
    polizas_con_seguimiento = polizas.prefetch_related('seguimientos').order_by('-fecha_vencimiento')
    seguimientos_poliza_generales = contrato.seguimientos_poliza.filter(
        poliza__isnull=True,
    ).order_by('-fecha_registro')
    
    context = {
        'contrato': contrato,
        'vista_vigente': vista_vigente,
        'requisitos_contrato': requisitos_contrato,
        'requerimientos_poliza': requerimientos_poliza,
        'polizas': polizas,
        'polizas_con_seguimiento': polizas_con_seguimiento,
        'seguimientos_poliza_generales': seguimientos_poliza_generales,
        'auditoria_polizas': auditoria_polizas,
        'pólizas_requeridas': pólizas_requeridas,
        'pólizas_faltantes': pólizas_faltantes,
        'contrato_no_iniciado': contrato_no_iniciado,
        'otrosi_futuro_polizas': otrosi_futuro_polizas,
        'titulo': f'Gestionar Pólizas - {contrato.num_contrato}'
    }
    return render(request, 'gestion/polizas/gestionar.html', context)




@login_required_custom
def nueva_poliza(request, contrato_id):
    """Vista para agregar una nueva póliza a un contrato"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    vista_vigente = get_vista_vigente_contrato(contrato)
    fecha_vista_final = vista_vigente.get('fecha_final_actualizada') or contrato.fecha_final_actualizada or contrato.fecha_final_inicial
    vista_vigente['fecha_final_mostrar'] = fecha_vista_final
    
    # Determinar fecha de inicio: último otro sí o fecha inicial del contrato
    # TODO: Implementar lógica de otro sí cuando esté disponible
    fecha_inicio_default = contrato.fecha_inicial_contrato
    
    # Permitir gestionar pólizas incluso si el contrato aún no ha iniciado
    requisitos_contrato = _construir_requisitos_poliza(contrato, vista_vigente, permitir_fuera_vigencia=True)
    polizas_vigentes = get_polizas_vigentes(contrato)
    requisitos_contrato = _aplicar_polizas_vigentes_a_requisitos(requisitos_contrato, polizas_vigentes)
    
    if request.method == 'POST':
        form = PolizaForm(request.POST, contrato=contrato, es_edicion=False)
        
        if not form.is_valid():
            # Mostrar errores al usuario
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
        else:
            # El formulario ya maneja la asignación del documento origen y colchón en su método save()
            poliza = form.save(commit=False)
            # Asignar contrato ANTES de cualquier operación que lo necesite
            poliza.contrato = contrato
            
            # Recalcular fecha_vencimiento_real si tiene colchón (ahora que contrato está asignado)
            if hasattr(poliza, 'tiene_colchon') and poliza.tiene_colchon and poliza.contrato:
                from datetime import date
                try:
                    from gestion.services.alertas import _obtener_fecha_final_contrato
                    fecha_final = _obtener_fecha_final_contrato(poliza.contrato, date.today())
                    if fecha_final:
                        poliza.fecha_vencimiento_real = fecha_final
                except Exception:
                    pass
            
            # Manejar campos adicionales del formulario
            meses_cobertura = request.POST.get('meses_cobertura')
            fecha_inicio_vigencia = request.POST.get('fecha_inicio_vigencia')
            
            # Si se proporcionó fecha de inicio y meses, calcular fecha de vencimiento
            if fecha_inicio_vigencia and meses_cobertura:
                from datetime import datetime
                try:
                    fecha_inicio = datetime.strptime(fecha_inicio_vigencia, '%Y-%m-%d').date()
                    meses = int(meses_cobertura)
                    # Calcular fecha de vencimiento usando función centralizada
                    poliza.fecha_vencimiento = calcular_fecha_vencimiento(fecha_inicio, meses)
                    poliza.fecha_inicio_vigencia = fecha_inicio
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error("Error al calcular fecha de vencimiento de póliza", exc_info=True)
                    messages.error(request, 'Error al calcular fecha de vencimiento. Por favor, intente nuevamente.')
            
            try:
                guardar_con_auditoria(poliza, request.user, es_nuevo=True)
                # El método save() del formulario ya guarda la póliza con todos los campos
                poliza.save()
                
                # Validar si cumple con los requisitos del contrato
                validacion = poliza.cumple_requisitos_contrato()
                if validacion['cumple']:
                    messages.success(request, f'Póliza {poliza.numero_poliza} agregada exitosamente y cumple con los requisitos del contrato!')
                    return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)
                else:
                    # Si no cumple, redirigir a vista de validación
                    messages.warning(request, f'Póliza guardada pero no cumple todos los requisitos. Por favor revise.')
                    return redirect('gestion:validar_poliza', poliza_id=poliza.id)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error("Error al guardar póliza", exc_info=True)
                messages.error(request, 'Error al guardar la póliza. Por favor, intente nuevamente o contacte al administrador.')
    else:
        form = PolizaForm(contrato=contrato, es_edicion=False)
        
        # Establecer fecha de inicio por defecto
        form.initial['fecha_inicio_vigencia'] = fecha_inicio_default
        
        # Obtener requisitos iniciales según documento origen por defecto
        documento_origen_default = form.fields['documento_origen'].initial or 'CONTRATO'
        requisitos_contrato = _obtener_requisitos_por_documento(contrato, documento_origen_default)
    
    context = {
        'form': form,
        'contrato': contrato,
        'vista_vigente': vista_vigente,
        'requisitos_contrato': requisitos_contrato,
        'fecha_inicio_vigencia': fecha_inicio_default.strftime('%Y-%m-%d') if fecha_inicio_default else None,
        'titulo': f'Nueva Póliza - {contrato.num_contrato}'
    }
    return render(request, 'gestion/polizas/form.html', context)




@login_required_custom
def editar_poliza(request, poliza_id):
    """Vista para editar una póliza existente"""
    poliza = get_object_or_404(Poliza, id=poliza_id)
    contrato = poliza.contrato
    
    vista_vigente = get_vista_vigente_contrato(contrato)
    fecha_vista_final = vista_vigente.get('fecha_final_actualizada') or contrato.fecha_final_actualizada or contrato.fecha_final_inicial
    vista_vigente['fecha_final_mostrar'] = fecha_vista_final
    
    # Permitir gestionar pólizas incluso si el contrato aún no ha iniciado
    requisitos_contrato = _construir_requisitos_poliza(contrato, vista_vigente, permitir_fuera_vigencia=True)
    polizas_vigentes = get_polizas_vigentes(contrato)
    requisitos_contrato = _aplicar_polizas_vigentes_a_requisitos(requisitos_contrato, polizas_vigentes)
    
    # Inicializar variables para ambos casos (GET y POST)
    meses_cobertura = None
    fecha_inicio_vigencia = None
    
    if request.method == 'POST':
        form = PolizaForm(request.POST, instance=poliza, contrato=contrato, es_edicion=True)
        if form.is_valid():
            # El formulario ya maneja la asignación del documento origen y colchón en su método save()
            poliza = form.save(commit=False)
            
            # Recalcular fecha_vencimiento_real si tiene colchón
            if hasattr(poliza, 'tiene_colchon') and poliza.tiene_colchon and poliza.contrato:
                from datetime import date
                try:
                    from gestion.services.alertas import _obtener_fecha_final_contrato
                    fecha_final = _obtener_fecha_final_contrato(poliza.contrato, date.today())
                    if fecha_final:
                        poliza.fecha_vencimiento_real = fecha_final
                except Exception:
                    pass
            
            # Manejar campos adicionales del formulario
            meses_cobertura = request.POST.get('meses_cobertura')
            
            # Si se proporcionó fecha de inicio y meses, calcular fecha de vencimiento
            if poliza.fecha_inicio_vigencia and meses_cobertura:
                meses = int(meses_cobertura)
                # Calcular fecha de vencimiento usando función centralizada
                poliza.fecha_vencimiento = calcular_fecha_vencimiento(poliza.fecha_inicio_vigencia, meses)
            
            guardar_con_auditoria(poliza, request.user, es_nuevo=False)
            # El método save() del formulario ya guarda la póliza con todos los campos
            poliza.save()
            
            # Validar si cumple con los requisitos del contrato
            validacion = poliza.cumple_requisitos_contrato()
            if validacion['cumple']:
                messages.success(request, f'Póliza {poliza.numero_poliza} actualizada exitosamente y cumple con los requisitos del contrato!')
                return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)
            else:
                # Si no cumple, redirigir a vista de validación (igual que en nueva_poliza)
                messages.warning(request, f'Póliza actualizada pero no cumple todos los requisitos. Por favor revise.')
                return redirect('gestion:validar_poliza', poliza_id=poliza.id)
    else:
        form = PolizaForm(instance=poliza, contrato=contrato, es_edicion=True)
        
        # Obtener requisitos según documento origen actual de la póliza
        if poliza.otrosi:
            documento_origen_id = f'OTROSI_{poliza.otrosi.id}'
        elif poliza.renovacion_automatica:
            documento_origen_id = f'RENOVACION_{poliza.renovacion_automatica.id}'
        else:
            documento_origen_id = 'CONTRATO'
        
        requisitos_contrato = _obtener_requisitos_por_documento(contrato, documento_origen_id)
        
        # Usar los datos guardados directamente
        if poliza.fecha_inicio_vigencia:
            fecha_inicio_vigencia = poliza.fecha_inicio_vigencia.strftime('%Y-%m-%d')
            if poliza.fecha_vencimiento and poliza.fecha_inicio_vigencia:
                from dateutil.relativedelta import relativedelta
                delta = relativedelta(poliza.fecha_vencimiento, poliza.fecha_inicio_vigencia)
                meses_cobertura = delta.years * 12 + delta.months
    
    context = {
        'form': form,
        'poliza': poliza,
        'contrato': contrato,
        'vista_vigente': vista_vigente,
        'requisitos_contrato': requisitos_contrato,
        'meses_cobertura': meses_cobertura,
        'fecha_inicio_vigencia': fecha_inicio_vigencia,
        'titulo': f'Editar Póliza - {poliza.numero_poliza}'
    }
    return render(request, 'gestion/polizas/form.html', context)


@login_required_custom
def validar_poliza(request, poliza_id):
    """Vista para validar una póliza y mostrar inconsistencias"""
    poliza = get_object_or_404(Poliza, id=poliza_id)
    contrato = poliza.contrato
    
    vista_vigente = get_vista_vigente_contrato(contrato)
    requisitos_contrato = _construir_requisitos_poliza(contrato, vista_vigente, permitir_fuera_vigencia=True)
    
    validacion = poliza.cumple_requisitos_contrato()
    
    context = {
        'poliza': poliza,
        'contrato': contrato,
        'validacion': validacion,
        'requisitos_contrato': requisitos_contrato,
        'titulo': f'Validar Póliza - {poliza.numero_poliza}'
    }
    return render(request, 'gestion/polizas/validar.html', context)


@admin_required
@login_required_custom
def eliminar_poliza(request, poliza_id):
    """Vista para eliminar una póliza"""
    poliza = get_object_or_404(Poliza, id=poliza_id)
    contrato = poliza.contrato
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'confirmar':
            numero = poliza.numero_poliza
            registrar_eliminacion(poliza, request.user)
            poliza.delete()
            messages.success(request, f'Póliza {numero} eliminada exitosamente.')
            return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)
        elif accion == 'cancelar':
            return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)
    
    context = {
        'poliza': poliza,
        'contrato': contrato,
        'titulo': f'Eliminar Póliza - {poliza.numero_poliza}'
    }
    return render(request, 'gestion/polizas/eliminar.html', context)


@login_required_custom
def agregar_seguimiento_poliza(request, contrato_id):
    """Vista para agregar un seguimiento de póliza"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        poliza_id = request.POST.get('poliza_id')
        poliza_tipo = request.POST.get('poliza_tipo')
        detalle = request.POST.get('detalle', '')
        fecha_registro = request.POST.get('fecha_registro')
        
        if not fecha_registro:
            fecha_registro = date.today()
        else:
            from datetime import datetime
            fecha_registro = datetime.strptime(fecha_registro, '%Y-%m-%d').date()
        
        poliza = None
        if poliza_id:
            try:
                poliza = Poliza.objects.get(id=poliza_id, contrato=contrato)
            except Poliza.DoesNotExist:
                pass
        
        seguimiento = SeguimientoPoliza.objects.create(
            contrato=contrato,
            poliza=poliza,
            poliza_tipo=poliza_tipo if not poliza else None,
            detalle=detalle,
            fecha_registro=fecha_registro
        )
        
        guardar_con_auditoria(seguimiento, request.user, es_nuevo=True)
        seguimiento.save()
        
        messages.success(request, 'Seguimiento de póliza agregado exitosamente.')
        return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)
    
    return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)


@login_required_custom
def agregar_seguimiento_contrato(request, contrato_id):
    """Vista para agregar un seguimiento de contrato"""
    from gestion.models import SeguimientoContrato
    
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        detalle = request.POST.get('detalle_seguimiento', '').strip()
        if detalle:
            seguimiento = SeguimientoContrato.objects.create(
                contrato=contrato,
                detalle=detalle,
                registrado_por=request.user.get_username() if request.user.is_authenticated else None
            )
            guardar_con_auditoria(seguimiento, request.user, es_nuevo=True)
            seguimiento.save()
            messages.success(request, 'Seguimiento de contrato agregado exitosamente.')
        else:
            messages.warning(request, 'Debe ingresar contenido para registrar un seguimiento.')
        return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
    
    return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
