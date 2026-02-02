from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import PolizaForm
from gestion.models import Contrato, Poliza, SeguimientoPoliza, SeguimientoContrato
from gestion.utils import calcular_fecha_vencimiento
from gestion.utils_otrosi import get_vista_vigente_contrato, get_polizas_vigentes, es_fecha_fuera_vigencia_contrato
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion
from .utils import _construir_requisitos_poliza, _aplicar_polizas_vigentes_a_requisitos

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
        from gestion.models import OtroSi
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
            poliza.contrato = contrato
            
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
        
        # Usar los datos guardados directamente
        if poliza.fecha_inicio_vigencia:
            fecha_inicio_vigencia = poliza.fecha_inicio_vigencia.strftime('%Y-%m-%d')
        else:
            fecha_inicio_vigencia = None
            
        # Calcular meses de cobertura basado en las fechas guardadas
        if poliza.fecha_inicio_vigencia and poliza.fecha_vencimiento:
            from datetime import date
            diff = poliza.fecha_vencimiento - poliza.fecha_inicio_vigencia
            meses_cobertura = round(diff.days / 30)  # Aproximación de 30 días por mes
        else:
            meses_cobertura = None
    
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
    """Vista para mostrar las inconsistencias de una póliza y permitir continuar"""
    poliza = get_object_or_404(Poliza, id=poliza_id)
    contrato = poliza.contrato
    
    # Obtener validación de la póliza
    validacion = poliza.cumple_requisitos_contrato()
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'continuar':
            # El usuario confirma continuar a pesar de las inconsistencias
            messages.warning(request, f'Póliza {poliza.numero_poliza} guardada con inconsistencias. Se recomienda revisar los requisitos del contrato.')
            return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)
        elif accion == 'corregir':
            # El usuario quiere corregir la póliza
            return redirect('gestion:editar_poliza', poliza_id=poliza.id)
    
    # Obtener requisitos del contrato usando la función que considera Otros Sí vigentes
    vista_vigente = get_vista_vigente_contrato(contrato)
    requisitos_contrato = _construir_requisitos_poliza(contrato, vista_vigente, permitir_fuera_vigencia=True)
    
    context = {
        'poliza': poliza,
        'contrato': contrato,
        'validacion': validacion,
        'requisitos_contrato': requisitos_contrato,
        'titulo': f'Validar Póliza - {poliza.numero_poliza}'
    }
    return render(request, 'gestion/polizas/validar.html', context)




@admin_required
def eliminar_poliza(request, poliza_id):
    """Vista para eliminar una póliza"""
    poliza = get_object_or_404(Poliza, id=poliza_id)
    contrato = poliza.contrato
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'confirmar':
            registrar_eliminacion(poliza, request.user)
            numero_poliza = poliza.numero_poliza
            poliza.delete()
            messages.success(request, f'✅ Póliza {numero_poliza} eliminada exitosamente!')
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
    """Vista para agregar un seguimiento de póliza desde la vista de gestionar pólizas"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        detalle = request.POST.get('detalle', '').strip()
        poliza_tipo = request.POST.get('poliza_tipo', '').strip()
        poliza_id = request.POST.get('poliza_id', '').strip()
        
        if detalle:
            poliza = None
            if poliza_id:
                try:
                    poliza = Poliza.objects.get(id=poliza_id, contrato=contrato)
                except Poliza.DoesNotExist:
                    pass
            
            SeguimientoPoliza.objects.create(
                contrato=contrato,
                poliza=poliza,
                poliza_tipo=poliza_tipo if poliza_tipo else None,
                detalle=detalle,
                registrado_por=request.user.get_username() if request.user.is_authenticated else None
            )
            messages.success(request, 'Seguimiento agregado correctamente.')
        else:
            messages.error(request, 'Debe ingresar contenido para registrar un seguimiento.')
        
        return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)
    
    return redirect('gestion:gestionar_polizas', contrato_id=contrato.id)


@login_required_custom
def agregar_seguimiento_contrato(request, contrato_id):
    """Vista para agregar un seguimiento de contrato desde la vista vigente"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        detalle = request.POST.get('detalle', '').strip()
        if detalle:
            SeguimientoContrato.objects.create(
                contrato=contrato,
                detalle=detalle,
                registrado_por=request.user.get_username() if request.user.is_authenticated else None
            )
            messages.success(request, 'Seguimiento agregado correctamente.')
        else:
            messages.error(request, 'Debe ingresar contenido para registrar un seguimiento.')
        
        return redirect('gestion:vista_vigente_contrato', contrato_id=contrato.id)
    
    return redirect('gestion:vista_vigente_contrato', contrato_id=contrato.id)




