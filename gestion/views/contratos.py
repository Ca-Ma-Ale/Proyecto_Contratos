from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import ContratoForm, FiltroExportacionContratosForm, FiltroListaContratosForm, FiltroRenovacionesAutomaticasForm
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion
from gestion.models import (
    Contrato,
    SeguimientoContrato,
    SeguimientoPoliza,
    obtener_nombre_tipo_condicion_ipc,
    obtener_nombre_periodicidad_ipc,
    MESES_CHOICES,
)
from gestion.services.exportes import (
    ColumnaExportacion,
    ExportacionVaciaError,
    generar_excel_corporativo,
)
from gestion.utils_otrosi import (
    get_ultimo_otrosi_que_modifico_campo,
    get_ultimo_otrosi_que_modifico_campo_hasta_fecha,
    get_vista_vigente_contrato,
    get_ultimo_otrosi_aprobado,
    get_otrosi_vigente,
)
from gestion.utils_ipc import obtener_ultimo_calculo_ipc_aplicado, obtener_ultimo_calculo_aplicado_hasta_fecha
from .utils import (
    obtener_configuracion_empresa,
    registrar_seguimientos_contrato_desde_formulario,
    _construir_requisitos_poliza,
    _obtener_fecha_final_contrato,
    _es_contrato_vencido,
    _respuesta_archivo_excel,
)

@login_required_custom
def nuevo_contrato(request):
    """Vista para crear un nuevo contrato con condiciones de póliza"""
    configuracion_empresa = obtener_configuracion_empresa()
    
    if request.method == 'POST':
        form = ContratoForm(request.POST)
        
        if form.is_valid():
            contrato = form.save(commit=False)
            guardar_con_auditoria(contrato, request.user, es_nuevo=True)
            contrato.save()

            registrar_seguimientos_contrato_desde_formulario(
                form,
                contrato,
                request.user.get_username() if request.user.is_authenticated else None
            )
            
            skip_auditoria = request.POST.get('skip_auditoria', 'false') == 'true'
            if not skip_auditoria:
                return redirect('gestion:auditoria_clausulas_contrato', contrato_id=contrato.id)
            
            messages.success(request, f'Contrato {contrato.num_contrato} creado exitosamente!')
            return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
        else:
            # Mostrar errores específicos del formulario
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ContratoForm()
        # Pre-llenar con datos de la empresa
        form.fields['nit_concedente'].initial = configuracion_empresa.nit_empresa
        form.fields['rep_legal_concedente'].initial = configuracion_empresa.representante_legal
    
    context = {
        'form': form,
        'titulo': 'Nuevo Contrato',
        'configuracion_empresa': configuracion_empresa,
        'seguimientos_contrato': [],
        'seguimientos_poliza_por_tipo': {
            'rce': [],
            'cumplimiento': [],
            'arrendamiento': [],
            'todo_riesgo': [],
            'otra': []
        }
    }
    return render(request, 'gestion/contratos/form.html', context)




@login_required_custom
def editar_contrato(request, contrato_id):
    """Vista para editar un contrato existente con sus condiciones de póliza"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    requerimientos_poliza = contrato.requerimientos_poliza.all()
    polizas = contrato.polizas.all()
    
    if request.method == 'POST':
        form = ContratoForm(request.POST, instance=contrato)
        
        if form.is_valid():
            contrato = form.save(commit=False)
            guardar_con_auditoria(contrato, request.user, es_nuevo=False)
            contrato.save()

            registrar_seguimientos_contrato_desde_formulario(
                form,
                contrato,
                request.user.get_username() if request.user.is_authenticated else None
            )
            
            skip_auditoria = request.POST.get('skip_auditoria', 'false') == 'true'
            if not skip_auditoria:
                return redirect('gestion:auditoria_clausulas_contrato', contrato_id=contrato.id)
            
            messages.success(request, f'Contrato {contrato.num_contrato} actualizado exitosamente!')
            return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = ContratoForm(instance=contrato)
    
    seguimientos_poliza_queryset = contrato.seguimientos_poliza.filter(
        poliza__isnull=True
    ).order_by('-fecha_registro')

    mapa_tipos = {
        'RCE - Responsabilidad Civil': 'rce',
        'Cumplimiento': 'cumplimiento',
        'Poliza de Arrendamiento': 'arrendamiento',
        'Arrendamiento': 'todo_riesgo',
        'Otra': 'otra',
    }
    seguimientos_poliza_por_tipo = {clave: [] for clave in mapa_tipos.values()}

    for seguimiento in seguimientos_poliza_queryset:
        clave = mapa_tipos.get(seguimiento.poliza_tipo)
        if clave:
            seguimientos_poliza_por_tipo.setdefault(clave, []).append(seguimiento)
    
    context = {
        'form': form,
        'titulo': f'Editar Contrato {contrato.num_contrato}',
        'contrato': contrato,
        'requerimientos_poliza': requerimientos_poliza,
        'polizas': polizas,
        'seguimientos_contrato': contrato.seguimientos.all().order_by('-fecha_registro'),
        'seguimientos_poliza_por_tipo': seguimientos_poliza_por_tipo
    }
    return render(request, 'gestion/contratos/form.html', context)




@login_required_custom
def lista_contratos(request):
    """Vista para listar todos los contratos con filtros"""
    from datetime import date
    
    contratos = Contrato.objects.select_related('arrendatario', 'proveedor', 'local', 'tipo_contrato', 'tipo_servicio').order_by('-fecha_inicial_contrato')
    
    filtro_form = FiltroListaContratosForm(request.GET or None)
    
    fecha_actual = date.today()
    estado_vigencia = 'vigentes'
    
    tipo_filtro_activo = request.GET.get('tipo_contrato_cliente_proveedor', '')
    
    if filtro_form.is_valid():
        tipo_contrato_cliente_proveedor = filtro_form.cleaned_data.get('tipo_contrato_cliente_proveedor')
        tipo_contrato = filtro_form.cleaned_data.get('tipo_contrato')
        tipo_servicio = filtro_form.cleaned_data.get('tipo_servicio')
        buscar = filtro_form.cleaned_data.get('buscar')
        estado_vigencia = filtro_form.cleaned_data.get('estado_vigencia') or estado_vigencia
        
        if tipo_contrato_cliente_proveedor:
            contratos = contratos.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cliente_proveedor)
            tipo_filtro_activo = tipo_contrato_cliente_proveedor
        
        if tipo_contrato:
            contratos = contratos.filter(tipo_contrato=tipo_contrato)
        
        if tipo_servicio:
            contratos = contratos.filter(tipo_servicio=tipo_servicio)
        
        if buscar:
            contratos = contratos.filter(
                Q(arrendatario__razon_social__icontains=buscar) |
                Q(arrendatario__nit__icontains=buscar) |
                Q(proveedor__razon_social__icontains=buscar) |
                Q(proveedor__nit__icontains=buscar)
            )
    elif tipo_filtro_activo:
        contratos = contratos.filter(tipo_contrato_cliente_proveedor=tipo_filtro_activo)
    
    contratos_con_estado = []
    
    for contrato in contratos:
        # Verificar si hay un Otro Sí o Renovación Automática vigente primero
        otrosi_vigente_actual = get_otrosi_vigente(contrato, fecha_actual)
        
        # Obtener la fecha final vigente considerando el Otro Sí vigente
        fecha_final_vigente = _obtener_fecha_final_contrato(contrato, fecha_actual)
        
        # Determinar qué evento modificó la fecha final para mostrar en el badge
        evento_fecha_final_info = None
        if otrosi_vigente_actual:
            # Si hay un Otro Sí vigente, usar ese para el badge
            if hasattr(otrosi_vigente_actual, 'numero_otrosi'):
                evento_fecha_final_info = {
                    'tipo': 'OS',
                    'numero': getattr(otrosi_vigente_actual, 'numero_otrosi', 'N/A')
                }
            elif hasattr(otrosi_vigente_actual, 'numero_renovacion'):
                evento_fecha_final_info = {
                    'tipo': 'RA',
                    'numero': getattr(otrosi_vigente_actual, 'numero_renovacion', 'N/A')
                }
        else:
            # Si no hay Otro Sí vigente, buscar el último que modificó la fecha
            evento_fecha_final = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
                contrato,
                'nueva_fecha_final_actualizada',
                fecha_actual
            )
            if evento_fecha_final:
                if hasattr(evento_fecha_final, 'numero_otrosi'):
                    evento_fecha_final_info = {
                        'tipo': 'OS',
                        'numero': getattr(evento_fecha_final, 'numero_otrosi', 'N/A')
                    }
                elif hasattr(evento_fecha_final, 'numero_renovacion'):
                    evento_fecha_final_info = {
                        'tipo': 'RA',
                        'numero': getattr(evento_fecha_final, 'numero_renovacion', 'N/A')
                    }
        
        estado_vigente = False
        es_vencido = _es_contrato_vencido(contrato, fecha_actual)
        
        # Si hay un Otro Sí vigente, verificar su effective_to
        if otrosi_vigente_actual:
            if otrosi_vigente_actual.effective_to:
                # Si tiene effective_to, verificar que la fecha actual esté dentro del rango
                estado_vigente = otrosi_vigente_actual.effective_from <= fecha_actual <= otrosi_vigente_actual.effective_to
            else:
                # Si no tiene effective_to pero tiene nueva_fecha_final_actualizada, usar esa
                if otrosi_vigente_actual.nueva_fecha_final_actualizada:
                    estado_vigente = otrosi_vigente_actual.nueva_fecha_final_actualizada >= fecha_actual
                else:
                    # Si no tiene ninguna fecha, considerar vigente si está dentro del rango effective_from
                    estado_vigente = otrosi_vigente_actual.effective_from <= fecha_actual
        elif contrato.vigente:
            # Si no hay Otro Sí vigente pero el contrato está marcado como vigente
            if fecha_final_vigente:
                estado_vigente = fecha_final_vigente >= fecha_actual
            else:
                estado_vigente = True
        
        if estado_vigencia == 'vigentes' and not estado_vigente:
            continue
        if estado_vigencia == 'vencidos' and estado_vigente:
            continue
        
        contratos_con_estado.append({
            'contrato': contrato,
            'estado_vigente': estado_vigente,
            'es_vencido': es_vencido,
            'fecha_final_vigente': fecha_final_vigente,
            'evento_fecha_final': evento_fecha_final_info,
        })
    
    context = {
        'contratos_con_estado': contratos_con_estado,
        'filtro_form': filtro_form,
        'total_contratos': len(contratos_con_estado),
        'tipo_filtro_activo': tipo_filtro_activo,
    }
    return render(request, 'gestion/contratos/lista.html', context)




@login_required_custom
def detalle_contrato(request, contrato_id):
    """Vista para ver el detalle de un contrato"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    requerimientos_poliza = contrato.requerimientos_poliza.all()
    polizas = contrato.polizas.all()
    polizas = contrato.polizas.all()
    otrosi = contrato.otrosi.all()
    # Agregar información de restricciones de eliminación
    from gestion.utils_otrosi import tiene_otrosi_posteriores
    otrosi_lista = []
    for otrosi_item in otrosi:
        otrosi_item.tiene_posteriores = tiene_otrosi_posteriores(otrosi_item)
        otrosi_lista.append(otrosi_item)
    otrosi = otrosi_lista
    seguimientos_contrato = contrato.seguimientos.order_by('-fecha_registro')
    seguimientos_poliza_generales = contrato.seguimientos_poliza.filter(
        poliza__isnull=True,
    ).order_by('-fecha_registro')
    
    # Obtener el último Otrosí aprobado para mostrar fechas actualizadas
    ultimo_otrosi = get_ultimo_otrosi_aprobado(contrato)
    
    # Calcular estado vigente basado en el último Otro Sí vigente y fecha actual
    from datetime import date
    fecha_actual = date.today()
    estado_vigente = False
    
    # Obtener el Otro Sí vigente en la fecha actual (no solo el último aprobado)
    otrosi_vigente_actual = get_otrosi_vigente(contrato, fecha_actual)
    
    if otrosi_vigente_actual:
        # Hay un Otro Sí vigente, verificar su effective_to primero
        if otrosi_vigente_actual.effective_to:
            # Si tiene effective_to, verificar que la fecha actual esté dentro del rango
            estado_vigente = otrosi_vigente_actual.effective_from <= fecha_actual <= otrosi_vigente_actual.effective_to
        else:
            # Si no tiene effective_to pero tiene nueva_fecha_final_actualizada, usar esa
            fecha_final = otrosi_vigente_actual.nueva_fecha_final_actualizada or contrato.fecha_final_actualizada or contrato.fecha_final_inicial
            if fecha_final and fecha_final >= fecha_actual:
                estado_vigente = True
            elif fecha_final is None:
                estado_vigente = True
    elif contrato.vigente:
        # No hay Otro Sí vigente en la fecha actual, verificar solo la fecha final del contrato
        fecha_final = contrato.fecha_final_actualizada or contrato.fecha_final_inicial
        if fecha_final and fecha_final >= fecha_actual:
            estado_vigente = True
        elif fecha_final is None:
            estado_vigente = True
    
    def obtener_valor_y_otrosi(campo_otrosi, campo_contrato):
        """Obtiene valor y el Otro Sí que lo modificó"""
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo(contrato, campo_otrosi)
        if otrosi_modificador:
            valor_otrosi = getattr(otrosi_modificador, campo_otrosi, None)
            if valor_otrosi is not None and valor_otrosi != '':
                return valor_otrosi, otrosi_modificador
        valor_contrato = getattr(contrato, campo_contrato, None)
        return valor_contrato, None
    
    def obtener_fecha_poliza(campo_otrosi, campo_contrato):
        """Obtiene fecha del último otrosí que modificó este campo, sino del contrato"""
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo(contrato, campo_otrosi)
        if otrosi_modificador:
            fecha_otrosi = getattr(otrosi_modificador, campo_otrosi, None)
            if fecha_otrosi:
                return fecha_otrosi
        return getattr(contrato, campo_contrato, None)
    
    def obtener_valor_poliza(campo_otrosi, campo_contrato):
        """Obtiene valor numérico o string del último otrosí que modificó este campo, sino del contrato"""
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo(contrato, campo_otrosi)
        if otrosi_modificador:
            valor_otrosi = getattr(otrosi_modificador, campo_otrosi, None)
            if valor_otrosi is not None and valor_otrosi != '':
                return valor_otrosi
        return getattr(contrato, campo_contrato, None)
    
    def obtener_bool_poliza(campo_otrosi, campo_contrato):
        """Obtiene valor booleano del último otrosí que modificó este campo, sino del contrato"""
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo(contrato, campo_otrosi)
        if otrosi_modificador:
            valor_otrosi = getattr(otrosi_modificador, campo_otrosi, None)
            if valor_otrosi is not None:
                return valor_otrosi
        return getattr(contrato, campo_contrato, False)
    
    def obtener_valor_ipc(campo_otrosi, campo_contrato):
        """Obtiene valor IPC del último otrosí que modificó este campo, sino del contrato"""
        otrosi_modificador = get_ultimo_otrosi_que_modifico_campo(contrato, campo_otrosi)
        if otrosi_modificador:
            valor_otrosi = getattr(otrosi_modificador, campo_otrosi, None)
            if valor_otrosi is not None and valor_otrosi != '':
                return valor_otrosi
        return getattr(contrato, campo_contrato, None)
    
    # Fecha Final Actualizada: Si hay un Otro Sí vigente con effective_to, usar ese valor
    # Si no, usar nueva_fecha_final_actualizada del último Otro Sí que la modificó, sino del contrato
    otrosi_vigente_actual = get_otrosi_vigente(contrato, fecha_actual)
    fecha_final_actualizada = None
    otrosi_modificador_fecha_final = None
    
    if otrosi_vigente_actual:
        # Si el Otro Sí vigente tiene effective_to, usar ese valor (es la fecha final del contrato durante ese período)
        if otrosi_vigente_actual.effective_to:
            fecha_final_actualizada = otrosi_vigente_actual.effective_to
            otrosi_modificador_fecha_final = otrosi_vigente_actual
        # Si no tiene effective_to pero tiene nueva_fecha_final_actualizada, usar ese
        elif otrosi_vigente_actual.nueva_fecha_final_actualizada:
            fecha_final_actualizada = otrosi_vigente_actual.nueva_fecha_final_actualizada
            otrosi_modificador_fecha_final = otrosi_vigente_actual
    
    # Si no hay Otro Sí vigente o no tiene fecha final, buscar el último que modificó el campo
    if not fecha_final_actualizada:
        fecha_final_actualizada = obtener_fecha_poliza('nueva_fecha_final_actualizada', 'fecha_final_actualizada')
        if fecha_final_actualizada:
            otrosi_modificador_fecha_final = get_ultimo_otrosi_que_modifico_campo(contrato, 'nueva_fecha_final_actualizada')
    
    if not fecha_final_actualizada:
        fecha_final_actualizada = contrato.fecha_final_inicial
    
    # Fechas de vigencia de pólizas
    fecha_inicio_vigencia_rce = obtener_fecha_poliza('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce')
    fecha_fin_vigencia_rce = obtener_fecha_poliza('nuevo_fecha_fin_vigencia_rce', 'fecha_fin_vigencia_rce')
    fecha_inicio_vigencia_cumplimiento = obtener_fecha_poliza('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento')
    fecha_fin_vigencia_cumplimiento = obtener_fecha_poliza('nuevo_fecha_fin_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento')
    fecha_inicio_vigencia_arrendamiento = obtener_fecha_poliza('nuevo_fecha_inicio_vigencia_arrendamiento', 'fecha_inicio_vigencia_arrendamiento')
    fecha_fin_vigencia_arrendamiento = obtener_fecha_poliza('nuevo_fecha_fin_vigencia_arrendamiento', 'fecha_fin_vigencia_arrendamiento')
    fecha_inicio_vigencia_todo_riesgo = obtener_fecha_poliza('nuevo_fecha_inicio_vigencia_todo_riesgo', 'fecha_inicio_vigencia_todo_riesgo')
    fecha_fin_vigencia_todo_riesgo = obtener_fecha_poliza('nuevo_fecha_fin_vigencia_todo_riesgo', 'fecha_fin_vigencia_todo_riesgo')
    fecha_inicio_vigencia_otra_1 = obtener_fecha_poliza('nuevo_fecha_inicio_vigencia_otra_1', 'fecha_inicio_vigencia_otra_1')
    fecha_fin_vigencia_otra_1 = obtener_fecha_poliza('nuevo_fecha_fin_vigencia_otra_1', 'fecha_fin_vigencia_otra_1')
    
    # Valores económicos del último documento
    valor_canon_fijo = obtener_valor_poliza('nuevo_valor_canon', 'valor_canon_fijo')
    canon_minimo_garantizado = obtener_valor_poliza('nuevo_canon_minimo_garantizado', 'canon_minimo_garantizado')
    porcentaje_ventas = obtener_valor_poliza('nuevo_porcentaje_ventas', 'porcentaje_ventas')
    
    # Modalidad de pago del último documento que la modificó
    modalidad_pago_valor = obtener_valor_poliza('nueva_modalidad_pago', 'modalidad_pago')
    modalidad_pago_display = None
    if modalidad_pago_valor:
        modalidad_pago_display = dict(Contrato.MODALIDAD_CHOICES).get(modalidad_pago_valor, modalidad_pago_valor)
    elif contrato.modalidad_pago:
        modalidad_pago_display = contrato.get_modalidad_pago_display()
    
    def obtener_display_ipc(valor, choices_dict):
        """Obtiene el display de un valor IPC desde un diccionario de choices"""
        if valor:
            return dict(choices_dict).get(valor, valor)
        return None
    
    # Obtener valores IPC del último documento
    tipo_condicion_ipc_valor = obtener_valor_ipc('nuevo_tipo_condicion_ipc', 'tipo_condicion_ipc')
    puntos_adicionales_ipc = obtener_valor_ipc('nuevos_puntos_adicionales_ipc', 'puntos_adicionales_ipc')
    periodicidad_ipc_valor = obtener_valor_ipc('nueva_periodicidad_ipc', 'periodicidad_ipc')
    fecha_aumento_ipc_valor = obtener_valor_ipc('nueva_fecha_aumento_ipc', 'fecha_aumento_ipc')
    
    # Obtener displays de IPC
    tipo_condicion_ipc = tipo_condicion_ipc_valor
    tipo_condicion_ipc_display = obtener_nombre_tipo_condicion_ipc(tipo_condicion_ipc_valor) if tipo_condicion_ipc_valor else None
    periodicidad_ipc = periodicidad_ipc_valor
    periodicidad_ipc_display = obtener_nombre_periodicidad_ipc(periodicidad_ipc_valor) if periodicidad_ipc_valor else None
    fecha_aumento_ipc = fecha_aumento_ipc_valor
    fecha_aumento_ipc_display = fecha_aumento_ipc_valor.strftime('%d/%m/%Y') if fecha_aumento_ipc_valor else None
    
    # Construir condiciones IPC display
    condiciones_ipc_display = None
    if tipo_condicion_ipc_valor and puntos_adicionales_ipc is not None:
        tipo_display = tipo_condicion_ipc_display or tipo_condicion_ipc_valor
        condiciones_ipc_display = f"{tipo_display} + {puntos_adicionales_ipc} puntos"
    elif tipo_condicion_ipc_valor:
        condiciones_ipc_display = tipo_condicion_ipc_display or tipo_condicion_ipc_valor
    
    # Calcular fecha de aumento para periodicidad ANUAL
    fecha_aumento_anual = None
    fecha_aumento_anual_display = None
    
    if periodicidad_ipc == 'ANUAL' or contrato.periodicidad_ipc == 'ANUAL':
        # Si hay una nueva fecha de aumento IPC en el Otro Sí, usarla
        if fecha_aumento_ipc_valor:
            fecha_aumento_anual = fecha_aumento_ipc_valor
            fecha_aumento_anual_display = fecha_aumento_ipc_valor.strftime('%d/%m/%Y') if fecha_aumento_ipc_valor else None
        elif contrato.fecha_aumento_ipc:
            # Si el contrato tiene fecha de aumento IPC definida, usarla
            fecha_aumento_anual = contrato.fecha_aumento_ipc
            fecha_aumento_anual_display = contrato.fecha_aumento_ipc.strftime('%d/%m/%Y') if contrato.fecha_aumento_ipc else None
        else:
            # Por defecto, usar la fecha inicial del contrato
            if contrato.fecha_inicial_contrato:
                fecha_aumento_anual = contrato.fecha_inicial_contrato
                fecha_aumento_anual_display = contrato.fecha_inicial_contrato.strftime('%d/%m/%Y')
    
    # Valores de pólizas RCE
    exige_poliza_rce = obtener_bool_poliza('nuevo_exige_poliza_rce', 'exige_poliza_rce')
    valor_asegurado_rce = obtener_valor_poliza('nuevo_valor_asegurado_rce', 'valor_asegurado_rce')
    valor_propietario_locatario_ocupante_rce = obtener_valor_poliza('nuevo_valor_propietario_locatario_ocupante_rce', 'valor_propietario_locatario_ocupante_rce')
    valor_patronal_rce = obtener_valor_poliza('nuevo_valor_patronal_rce', 'valor_patronal_rce')
    valor_gastos_medicos_rce = obtener_valor_poliza('nuevo_valor_gastos_medicos_rce', 'valor_gastos_medicos_rce')
    valor_vehiculos_rce = obtener_valor_poliza('nuevo_valor_vehiculos_rce', 'valor_vehiculos_rce')
    valor_contratistas_rce = obtener_valor_poliza('nuevo_valor_contratistas_rce', 'valor_contratistas_rce')
    valor_perjuicios_extrapatrimoniales_rce = obtener_valor_poliza('nuevo_valor_perjuicios_extrapatrimoniales_rce', 'valor_perjuicios_extrapatrimoniales_rce')
    valor_dano_moral_rce = obtener_valor_poliza('nuevo_valor_dano_moral_rce', 'valor_dano_moral_rce')
    valor_lucro_cesante_rce = obtener_valor_poliza('nuevo_valor_lucro_cesante_rce', 'valor_lucro_cesante_rce')
    meses_vigencia_rce = obtener_valor_poliza('nuevo_meses_vigencia_rce', 'meses_vigencia_rce')
    
    # Valores de coberturas RCE para proveedores
    rce_cobertura_danos_materiales = obtener_valor_poliza('nuevo_rce_cobertura_danos_materiales', 'rce_cobertura_danos_materiales')
    rce_cobertura_lesiones_personales = obtener_valor_poliza('nuevo_rce_cobertura_lesiones_personales', 'rce_cobertura_lesiones_personales')
    rce_cobertura_muerte_terceros = obtener_valor_poliza('nuevo_rce_cobertura_muerte_terceros', 'rce_cobertura_muerte_terceros')
    rce_cobertura_danos_bienes_terceros = obtener_valor_poliza('nuevo_rce_cobertura_danos_bienes_terceros', 'rce_cobertura_danos_bienes_terceros')
    rce_cobertura_responsabilidad_patronal = obtener_valor_poliza('nuevo_rce_cobertura_responsabilidad_patronal', 'rce_cobertura_responsabilidad_patronal')
    rce_cobertura_responsabilidad_cruzada = obtener_valor_poliza('nuevo_rce_cobertura_responsabilidad_cruzada', 'rce_cobertura_responsabilidad_cruzada')
    rce_cobertura_danos_contratistas = obtener_valor_poliza('nuevo_rce_cobertura_danos_contratistas', 'rce_cobertura_danos_contratistas')
    rce_cobertura_danos_ejecucion_contrato = obtener_valor_poliza('nuevo_rce_cobertura_danos_ejecucion_contrato', 'rce_cobertura_danos_ejecucion_contrato')
    rce_cobertura_danos_predios_vecinos = obtener_valor_poliza('nuevo_rce_cobertura_danos_predios_vecinos', 'rce_cobertura_danos_predios_vecinos')
    rce_cobertura_gastos_medicos = obtener_valor_poliza('nuevo_rce_cobertura_gastos_medicos', 'rce_cobertura_gastos_medicos')
    rce_cobertura_gastos_defensa = obtener_valor_poliza('nuevo_rce_cobertura_gastos_defensa', 'rce_cobertura_gastos_defensa')
    rce_cobertura_perjuicios_patrimoniales = obtener_valor_poliza('nuevo_rce_cobertura_perjuicios_patrimoniales', 'rce_cobertura_perjuicios_patrimoniales')
    
    # Valores de póliza Cumplimiento
    exige_poliza_cumplimiento = obtener_bool_poliza('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento')
    valor_asegurado_cumplimiento = obtener_valor_poliza('nuevo_valor_asegurado_cumplimiento', 'valor_asegurado_cumplimiento')
    meses_vigencia_cumplimiento = obtener_valor_poliza('nuevo_meses_vigencia_cumplimiento', 'meses_vigencia_cumplimiento')
    valor_remuneraciones_cumplimiento = obtener_valor_poliza('nuevo_valor_remuneraciones_cumplimiento', 'valor_remuneraciones_cumplimiento')
    valor_servicios_publicos_cumplimiento = obtener_valor_poliza('nuevo_valor_servicios_publicos_cumplimiento', 'valor_servicios_publicos_cumplimiento')
    valor_iva_cumplimiento = obtener_valor_poliza('nuevo_valor_iva_cumplimiento', 'valor_iva_cumplimiento')
    valor_otros_cumplimiento = obtener_valor_poliza('nuevo_valor_otros_cumplimiento', 'valor_otros_cumplimiento')
    
    # Valores de amparos de cumplimiento para proveedores
    cumplimiento_amparo_cumplimiento_contrato = obtener_valor_poliza('nuevo_cumplimiento_amparo_cumplimiento_contrato', 'cumplimiento_amparo_cumplimiento_contrato')
    cumplimiento_amparo_buen_manejo_anticipo = obtener_valor_poliza('nuevo_cumplimiento_amparo_buen_manejo_anticipo', 'cumplimiento_amparo_buen_manejo_anticipo')
    cumplimiento_amparo_amortizacion_anticipo = obtener_valor_poliza('nuevo_cumplimiento_amparo_amortizacion_anticipo', 'cumplimiento_amparo_amortizacion_anticipo')
    cumplimiento_amparo_salarios_prestaciones = obtener_valor_poliza('nuevo_cumplimiento_amparo_salarios_prestaciones', 'cumplimiento_amparo_salarios_prestaciones')
    cumplimiento_amparo_aportes_seguridad_social = obtener_valor_poliza('nuevo_cumplimiento_amparo_aportes_seguridad_social', 'cumplimiento_amparo_aportes_seguridad_social')
    cumplimiento_amparo_calidad_servicio = obtener_valor_poliza('nuevo_cumplimiento_amparo_calidad_servicio', 'cumplimiento_amparo_calidad_servicio')
    cumplimiento_amparo_estabilidad_obra = obtener_valor_poliza('nuevo_cumplimiento_amparo_estabilidad_obra', 'cumplimiento_amparo_estabilidad_obra')
    cumplimiento_amparo_calidad_bienes = obtener_valor_poliza('nuevo_cumplimiento_amparo_calidad_bienes', 'cumplimiento_amparo_calidad_bienes')
    cumplimiento_amparo_multas = obtener_valor_poliza('nuevo_cumplimiento_amparo_multas', 'cumplimiento_amparo_multas')
    cumplimiento_amparo_clausula_penal = obtener_valor_poliza('nuevo_cumplimiento_amparo_clausula_penal', 'cumplimiento_amparo_clausula_penal')
    cumplimiento_amparo_sanciones_incumplimiento = obtener_valor_poliza('nuevo_cumplimiento_amparo_sanciones_incumplimiento', 'cumplimiento_amparo_sanciones_incumplimiento')
    
    # Valores de póliza Arrendamiento
    exige_poliza_arrendamiento = obtener_bool_poliza('nuevo_exige_poliza_arrendamiento', 'exige_poliza_arrendamiento')
    valor_asegurado_arrendamiento = obtener_valor_poliza('nuevo_valor_asegurado_arrendamiento', 'valor_asegurado_arrendamiento')
    meses_vigencia_arrendamiento = obtener_valor_poliza('nuevo_meses_vigencia_arrendamiento', 'meses_vigencia_arrendamiento')
    valor_remuneraciones_arrendamiento = obtener_valor_poliza('nuevo_valor_remuneraciones_arrendamiento', 'valor_remuneraciones_arrendamiento')
    valor_servicios_publicos_arrendamiento = obtener_valor_poliza('nuevo_valor_servicios_publicos_arrendamiento', 'valor_servicios_publicos_arrendamiento')
    valor_iva_arrendamiento = obtener_valor_poliza('nuevo_valor_iva_arrendamiento', 'valor_iva_arrendamiento')
    valor_otros_arrendamiento = obtener_valor_poliza('nuevo_valor_otros_arrendamiento', 'valor_otros_arrendamiento')
    
    # Valores de póliza Todo Riesgo
    exige_poliza_todo_riesgo = obtener_bool_poliza('nuevo_exige_poliza_todo_riesgo', 'exige_poliza_todo_riesgo')
    valor_asegurado_todo_riesgo = obtener_valor_poliza('nuevo_valor_asegurado_todo_riesgo', 'valor_asegurado_todo_riesgo')
    meses_vigencia_todo_riesgo = obtener_valor_poliza('nuevo_meses_vigencia_todo_riesgo', 'meses_vigencia_todo_riesgo')
    
    # Valores de otra póliza
    exige_poliza_otra_1 = obtener_bool_poliza('nuevo_exige_poliza_otra_1', 'exige_poliza_otra_1')
    nombre_poliza_otra_1 = obtener_valor_poliza('nuevo_nombre_poliza_otra_1', 'nombre_poliza_otra_1')
    valor_asegurado_otra_1 = obtener_valor_poliza('nuevo_valor_asegurado_otra_1', 'valor_asegurado_otra_1')
    meses_vigencia_otra_1 = obtener_valor_poliza('nuevo_meses_vigencia_otra_1', 'meses_vigencia_otra_1')
    
    if request.method == 'POST':
        detalle = request.POST.get('detalle_seguimiento', '').strip()
        if detalle:
            SeguimientoContrato.objects.create(
                contrato=contrato,
                detalle=detalle,
                registrado_por=request.user.get_username() if request.user.is_authenticated else None
            )
            messages.success(request, 'Seguimiento agregado correctamente.')
        else:
            messages.warning(request, 'Debe ingresar contenido para registrar un seguimiento.')
        return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
    
    # Crear diccionario de Otros Sí modificadores por campo para mostrar badges en el template
    otrosi_modificadores = {}
    # Agregar el modificador de fecha final si existe
    if otrosi_modificador_fecha_final:
        otrosi_modificadores['nueva_fecha_final_actualizada'] = otrosi_modificador_fecha_final
    
    campos_para_badge = [
        'nueva_fecha_final_actualizada', 'nueva_modalidad_pago', 'nuevo_valor_canon', 'nuevo_canon_minimo_garantizado',
        'nuevo_porcentaje_ventas', 'nuevo_tipo_condicion_ipc', 'nuevos_puntos_adicionales_ipc',
        'nueva_periodicidad_ipc', 'nueva_fecha_aumento_ipc',
        'nuevo_exige_poliza_rce', 'nuevo_valor_asegurado_rce', 'nuevo_valor_propietario_locatario_ocupante_rce',
        'nuevo_valor_patronal_rce', 'nuevo_valor_gastos_medicos_rce', 'nuevo_valor_vehiculos_rce',
        'nuevo_valor_contratistas_rce', 'nuevo_valor_perjuicios_extrapatrimoniales_rce',
        'nuevo_valor_dano_moral_rce', 'nuevo_valor_lucro_cesante_rce', 'nuevo_meses_vigencia_rce',
        'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
        # Coberturas RCE para proveedores
        'nuevo_rce_cobertura_danos_materiales', 'nuevo_rce_cobertura_lesiones_personales',
        'nuevo_rce_cobertura_muerte_terceros', 'nuevo_rce_cobertura_danos_bienes_terceros',
        'nuevo_rce_cobertura_responsabilidad_patronal', 'nuevo_rce_cobertura_responsabilidad_cruzada',
        'nuevo_rce_cobertura_danos_contratistas', 'nuevo_rce_cobertura_danos_ejecucion_contrato',
        'nuevo_rce_cobertura_danos_predios_vecinos', 'nuevo_rce_cobertura_gastos_medicos',
        'nuevo_rce_cobertura_gastos_defensa', 'nuevo_rce_cobertura_perjuicios_patrimoniales',
        'nuevo_exige_poliza_cumplimiento', 'nuevo_valor_asegurado_cumplimiento', 'nuevo_meses_vigencia_cumplimiento',
        'nuevo_valor_remuneraciones_cumplimiento', 'nuevo_valor_servicios_publicos_cumplimiento',
        'nuevo_valor_iva_cumplimiento', 'nuevo_valor_otros_cumplimiento',
        'nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento',
        # Amparos de cumplimiento para proveedores
        'nuevo_cumplimiento_amparo_cumplimiento_contrato', 'nuevo_cumplimiento_amparo_buen_manejo_anticipo',
        'nuevo_cumplimiento_amparo_amortizacion_anticipo', 'nuevo_cumplimiento_amparo_salarios_prestaciones',
        'nuevo_cumplimiento_amparo_aportes_seguridad_social', 'nuevo_cumplimiento_amparo_calidad_servicio',
        'nuevo_cumplimiento_amparo_estabilidad_obra', 'nuevo_cumplimiento_amparo_calidad_bienes',
        'nuevo_cumplimiento_amparo_multas', 'nuevo_cumplimiento_amparo_clausula_penal',
        'nuevo_cumplimiento_amparo_sanciones_incumplimiento',
        'nuevo_exige_poliza_arrendamiento', 'nuevo_valor_asegurado_arrendamiento', 'nuevo_meses_vigencia_arrendamiento',
        'nuevo_valor_remuneraciones_arrendamiento', 'nuevo_valor_servicios_publicos_arrendamiento',
        'nuevo_valor_iva_arrendamiento', 'nuevo_valor_otros_arrendamiento',
        'nuevo_fecha_inicio_vigencia_arrendamiento', 'nuevo_fecha_fin_vigencia_arrendamiento',
        'nuevo_exige_poliza_todo_riesgo', 'nuevo_valor_asegurado_todo_riesgo', 'nuevo_meses_vigencia_todo_riesgo',
        'nuevo_fecha_inicio_vigencia_todo_riesgo', 'nuevo_fecha_fin_vigencia_todo_riesgo',
        'nuevo_exige_poliza_otra_1', 'nuevo_nombre_poliza_otra_1', 'nuevo_valor_asegurado_otra_1',
        'nuevo_meses_vigencia_otra_1', 'nuevo_fecha_inicio_vigencia_otra_1', 'nuevo_fecha_fin_vigencia_otra_1'
    ]
    
    for campo in campos_para_badge:
        # No sobrescribir si ya existe (como para nueva_fecha_final_actualizada que ya se calculó arriba)
        if campo not in otrosi_modificadores:
            otrosi_mod = get_ultimo_otrosi_que_modifico_campo(contrato, campo)
            if otrosi_mod:
                otrosi_modificadores[campo] = otrosi_mod
    
    # Obtener el último cálculo IPC aplicado
    ultimo_calculo_ipc_aplicado = obtener_ultimo_calculo_ipc_aplicado(contrato)
    
    # Obtener el último cálculo aplicado (IPC o Salario Mínimo) para actualizar valores económicos
    ultimo_calculo_aplicado = obtener_ultimo_calculo_aplicado_hasta_fecha(contrato, date.today())
    
    # Actualizar valores económicos con el último cálculo aplicado si existe
    if ultimo_calculo_aplicado and ultimo_calculo_aplicado.nuevo_canon:
        # Verificar si hay Otro Sí que haya modificado estos campos después del cálculo
        otrosi_canon_min = otrosi_modificadores.get('nuevo_canon_minimo_garantizado')
        otrosi_canon = otrosi_modificadores.get('nuevo_valor_canon')
        
        # Si hay un cálculo aplicado, actualizar el canon según el tipo de contrato
        if contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
            # Para proveedores, actualizar "Valor mensual" (canon_minimo_garantizado)
            # Solo si no hay Otro Sí posterior o el cálculo es posterior al Otro Sí
            aplicar_calculo = False
            if not otrosi_canon_min:
                aplicar_calculo = True
            elif hasattr(otrosi_canon_min, 'fecha_aprobacion') and otrosi_canon_min.fecha_aprobacion:
                fecha_otrosi = otrosi_canon_min.fecha_aprobacion.date() if hasattr(otrosi_canon_min.fecha_aprobacion, 'date') else otrosi_canon_min.fecha_aprobacion
                aplicar_calculo = ultimo_calculo_aplicado.fecha_aplicacion >= fecha_otrosi
            else:
                aplicar_calculo = True
            
            if aplicar_calculo:
                canon_minimo_garantizado = ultimo_calculo_aplicado.nuevo_canon
        else:
            # Para arrendatarios, actualizar "Canon" (valor_canon_fijo)
            # Solo si no hay Otro Sí posterior o el cálculo es posterior al Otro Sí
            aplicar_calculo = False
            if not otrosi_canon:
                aplicar_calculo = True
            elif hasattr(otrosi_canon, 'fecha_aprobacion') and otrosi_canon.fecha_aprobacion:
                fecha_otrosi = otrosi_canon.fecha_aprobacion.date() if hasattr(otrosi_canon.fecha_aprobacion, 'date') else otrosi_canon.fecha_aprobacion
                aplicar_calculo = ultimo_calculo_aplicado.fecha_aplicacion >= fecha_otrosi
            else:
                aplicar_calculo = True
            
            if aplicar_calculo:
                valor_canon_fijo = ultimo_calculo_aplicado.nuevo_canon
    
    context = {
        'contrato': contrato,
        'requerimientos_poliza': requerimientos_poliza,
        'polizas': polizas,
        'polizas': polizas,
        'otrosi': otrosi,
        'seguimientos_contrato': seguimientos_contrato,
        'seguimientos_poliza_generales': seguimientos_poliza_generales,
        'ultimo_otrosi': ultimo_otrosi,
        'fecha_final_actualizada': fecha_final_actualizada,
        # Fechas de vigencia
        'fecha_inicio_vigencia_rce': fecha_inicio_vigencia_rce,
        'fecha_fin_vigencia_rce': fecha_fin_vigencia_rce,
        'fecha_inicio_vigencia_cumplimiento': fecha_inicio_vigencia_cumplimiento,
        'fecha_fin_vigencia_cumplimiento': fecha_fin_vigencia_cumplimiento,
        'fecha_inicio_vigencia_arrendamiento': fecha_inicio_vigencia_arrendamiento,
        'fecha_fin_vigencia_arrendamiento': fecha_fin_vigencia_arrendamiento,
        'fecha_inicio_vigencia_todo_riesgo': fecha_inicio_vigencia_todo_riesgo,
        'fecha_fin_vigencia_todo_riesgo': fecha_fin_vigencia_todo_riesgo,
        'fecha_inicio_vigencia_otra_1': fecha_inicio_vigencia_otra_1,
        'fecha_fin_vigencia_otra_1': fecha_fin_vigencia_otra_1,
        # Valores RCE
        'exige_poliza_rce': exige_poliza_rce,
        'valor_asegurado_rce': valor_asegurado_rce,
        'valor_propietario_locatario_ocupante_rce': valor_propietario_locatario_ocupante_rce,
        'valor_patronal_rce': valor_patronal_rce,
        'valor_gastos_medicos_rce': valor_gastos_medicos_rce,
        'valor_vehiculos_rce': valor_vehiculos_rce,
        'valor_contratistas_rce': valor_contratistas_rce,
        'valor_perjuicios_extrapatrimoniales_rce': valor_perjuicios_extrapatrimoniales_rce,
        'valor_dano_moral_rce': valor_dano_moral_rce,
        'valor_lucro_cesante_rce': valor_lucro_cesante_rce,
        'meses_vigencia_rce': meses_vigencia_rce,
        # Coberturas RCE para proveedores
        'rce_cobertura_danos_materiales': rce_cobertura_danos_materiales,
        'rce_cobertura_lesiones_personales': rce_cobertura_lesiones_personales,
        'rce_cobertura_muerte_terceros': rce_cobertura_muerte_terceros,
        'rce_cobertura_danos_bienes_terceros': rce_cobertura_danos_bienes_terceros,
        'rce_cobertura_responsabilidad_patronal': rce_cobertura_responsabilidad_patronal,
        'rce_cobertura_responsabilidad_cruzada': rce_cobertura_responsabilidad_cruzada,
        'rce_cobertura_danos_contratistas': rce_cobertura_danos_contratistas,
        'rce_cobertura_danos_ejecucion_contrato': rce_cobertura_danos_ejecucion_contrato,
        'rce_cobertura_danos_predios_vecinos': rce_cobertura_danos_predios_vecinos,
        'rce_cobertura_gastos_medicos': rce_cobertura_gastos_medicos,
        'rce_cobertura_gastos_defensa': rce_cobertura_gastos_defensa,
        'rce_cobertura_perjuicios_patrimoniales': rce_cobertura_perjuicios_patrimoniales,
        # Valores Cumplimiento
        'exige_poliza_cumplimiento': exige_poliza_cumplimiento,
        'valor_asegurado_cumplimiento': valor_asegurado_cumplimiento,
        'meses_vigencia_cumplimiento': meses_vigencia_cumplimiento,
        'valor_remuneraciones_cumplimiento': valor_remuneraciones_cumplimiento,
        'valor_servicios_publicos_cumplimiento': valor_servicios_publicos_cumplimiento,
        'valor_iva_cumplimiento': valor_iva_cumplimiento,
        'valor_otros_cumplimiento': valor_otros_cumplimiento,
        # Amparos de cumplimiento para proveedores
        'cumplimiento_amparo_cumplimiento_contrato': cumplimiento_amparo_cumplimiento_contrato,
        'cumplimiento_amparo_buen_manejo_anticipo': cumplimiento_amparo_buen_manejo_anticipo,
        'cumplimiento_amparo_amortizacion_anticipo': cumplimiento_amparo_amortizacion_anticipo,
        'cumplimiento_amparo_salarios_prestaciones': cumplimiento_amparo_salarios_prestaciones,
        'cumplimiento_amparo_aportes_seguridad_social': cumplimiento_amparo_aportes_seguridad_social,
        'cumplimiento_amparo_calidad_servicio': cumplimiento_amparo_calidad_servicio,
        'cumplimiento_amparo_estabilidad_obra': cumplimiento_amparo_estabilidad_obra,
        'cumplimiento_amparo_calidad_bienes': cumplimiento_amparo_calidad_bienes,
        'cumplimiento_amparo_multas': cumplimiento_amparo_multas,
        'cumplimiento_amparo_clausula_penal': cumplimiento_amparo_clausula_penal,
        'cumplimiento_amparo_sanciones_incumplimiento': cumplimiento_amparo_sanciones_incumplimiento,
        # Valores Arrendamiento
        'exige_poliza_arrendamiento': exige_poliza_arrendamiento,
        'valor_asegurado_arrendamiento': valor_asegurado_arrendamiento,
        'meses_vigencia_arrendamiento': meses_vigencia_arrendamiento,
        'valor_remuneraciones_arrendamiento': valor_remuneraciones_arrendamiento,
        'valor_servicios_publicos_arrendamiento': valor_servicios_publicos_arrendamiento,
        'valor_iva_arrendamiento': valor_iva_arrendamiento,
        'valor_otros_arrendamiento': valor_otros_arrendamiento,
        # Valores Todo Riesgo
        'exige_poliza_todo_riesgo': exige_poliza_todo_riesgo,
        'valor_asegurado_todo_riesgo': valor_asegurado_todo_riesgo,
        'meses_vigencia_todo_riesgo': meses_vigencia_todo_riesgo,
        # Valores Otra Póliza
        'exige_poliza_otra_1': exige_poliza_otra_1,
        'nombre_poliza_otra_1': nombre_poliza_otra_1,
        'valor_asegurado_otra_1': valor_asegurado_otra_1,
        'meses_vigencia_otra_1': meses_vigencia_otra_1,
        # Valores económicos
        'valor_canon_fijo': valor_canon_fijo,
        'canon_minimo_garantizado': canon_minimo_garantizado,
        'ultimo_calculo_aplicado': ultimo_calculo_aplicado,
        'porcentaje_ventas': porcentaje_ventas,
        'modalidad_pago': modalidad_pago_valor,
        'modalidad_pago_display': modalidad_pago_display,
        # Valores IPC
        'tipo_condicion_ipc': tipo_condicion_ipc,
        'tipo_condicion_ipc_display': tipo_condicion_ipc_display,
        'puntos_adicionales_ipc': puntos_adicionales_ipc,
        'periodicidad_ipc': periodicidad_ipc,
        'periodicidad_ipc_display': periodicidad_ipc_display,
        'fecha_aumento_ipc': fecha_aumento_ipc,
        'fecha_aumento_ipc_display': fecha_aumento_ipc_display,
        'condiciones_ipc_display': condiciones_ipc_display,
        'fecha_aumento_anual': fecha_aumento_anual,
        'fecha_aumento_anual_display': fecha_aumento_anual_display,
        'estado_vigente': estado_vigente,
        'otrosi_modificadores': otrosi_modificadores,
        'ultimo_calculo_ipc_aplicado': ultimo_calculo_ipc_aplicado
    }
    return render(request, 'gestion/contratos/detalle.html', context)




@admin_required
def eliminar_contrato(request, contrato_id):
    """Vista para eliminar un contrato"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        # Registrar eliminación antes de eliminar
        registrar_eliminacion(contrato, request.user)
        
        # Eliminar pólizas relacionadas primero
        polizas_count = contrato.polizas.count()
        for poliza in contrato.polizas.all():
            registrar_eliminacion(poliza, request.user)
        contrato.polizas.all().delete()
        
        # Eliminar otros sí relacionados
        otrosi_count = contrato.otrosi.count()
        for otrosi in contrato.otrosi.all():
            registrar_eliminacion(otrosi, request.user)
        contrato.otrosi.all().delete()
        
        # Eliminar el contrato
        num_contrato = contrato.num_contrato
        
        # Crear mensaje consolidado
        mensaje_eliminacion = f'Contrato {num_contrato} eliminado exitosamente'
        if polizas_count > 0 or otrosi_count > 0:
            mensaje_eliminacion += ' junto con '
            elementos = []
            if polizas_count > 0:
                elementos.append(f'{polizas_count} póliza(s)')
            if otrosi_count > 0:
                elementos.append(f'{otrosi_count} Otro Sí')
            mensaje_eliminacion += ' y '.join(elementos) + ' relacionado(s).'
        else:
            mensaje_eliminacion += '.'
        
        contrato.delete()
        messages.success(request, mensaje_eliminacion)
        
        return redirect('gestion:lista_contratos')
    
    context = {
        'contrato': contrato,
        'titulo': f'Eliminar Contrato {contrato.num_contrato}'
    }
    return render(request, 'gestion/contratos/eliminar.html', context)


def procesar_polizas_del_formulario(request, contrato):
    """Procesa las pólizas enviadas desde el formulario dinámico"""
    polizas_creadas = 0
    
    # Buscar campos de polizas en el request
    i = 0
    while True:
        tipo_key = f'poliza_{i}_tipo'
        valor_key = f'poliza_{i}_valor'
        vigencia_key = f'poliza_{i}_vigencia'
        
        if tipo_key in request.POST:
            tipo = request.POST.get(tipo_key)
            valor = request.POST.get(valor_key)
            vigencia = request.POST.get(vigencia_key)
            
            if tipo and valor and vigencia:
                try:
                    # Limpiar valor de formato
                    import re
                    valor_limpio = re.sub(r'[^\d]', '', valor)
                    
                    # Crear la poliza
                    poliza = Poliza.objects.create(
                        contrato=contrato,
                        tipo=tipo,
                        numero_poliza=f'AUTO-{contrato.num_contrato}-{i+1}',
                        valor_asegurado=float(valor_limpio),
                        fecha_vencimiento=date.today() + timedelta(days=30 * int(vigencia)),
                        estado_aportado='No Aportada',
                        aseguradora='Por definir',
                        cobertura=f'Cobertura {tipo}',
                        condiciones=f'Condiciones para {tipo}',
                        garantias=f'Garantias para {tipo}'
                    )
                    polizas_creadas += 1
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error("Error al crear póliza automática", exc_info=True)
            
            i += 1
        else:
            break
    
    if polizas_creadas > 0:
        messages.info(request, f'Se crearon {polizas_creadas} polizas requeridas para el contrato.')


# ============================================================================
# VISTAS DE MÓDULO OTRO SÍ
# ============================================================================



@login_required_custom
def vista_vigente_contrato(request, contrato_id):
    """Muestra la vista vigente del contrato (merge de base + Otro Sí vigente)"""
    from datetime import date
    
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    # Permitir "time travel" con parámetro de fecha
    fecha_param = request.GET.get('fecha')
    if fecha_param:
        try:
            from datetime import datetime
            fecha_referencia = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except:
            fecha_referencia = date.today()
            messages.warning(request, 'Fecha inválida, mostrando vista actual.')
    else:
        fecha_referencia = date.today()
    
    vista_vigente = get_vista_vigente_contrato(contrato, fecha_referencia)
    vista_disponible = vista_vigente.get('vista_disponible', True)

    if not vista_disponible:
        mensaje = vista_vigente.get('mensaje_sin_vigencia') or 'No existe información vigente para la fecha seleccionada.'
        messages.info(request, mensaje)
        requisitos_polizas = None
    else:
        requisitos_polizas = _construir_requisitos_poliza(contrato, vista_vigente)
    
    # Obtener todos los Otro Sí para el selector de fechas
    otrosis = contrato.otrosi.filter(estado='APROBADO').order_by('-effective_from')
    seguimientos_contrato = contrato.seguimientos.order_by('-fecha_registro')
    polizas_con_seguimiento = contrato.polizas.prefetch_related('seguimientos').order_by('-fecha_vencimiento')
    seguimientos_poliza_generales = contrato.seguimientos_poliza.filter(
        poliza__isnull=True,
    ).order_by('-fecha_registro')
    
    # Obtener el último cálculo IPC aplicado
    ultimo_calculo_ipc_aplicado = obtener_ultimo_calculo_ipc_aplicado(contrato)
    
    # Obtener alertas de IPC y Salario Mínimo para este contrato
    alertas_ipc = []
    alertas_salario_minimo = []
    if contrato.tipo_condicion_ipc == 'IPC':
        from gestion.services.alertas import obtener_alertas_ipc
        todas_alertas_ipc = obtener_alertas_ipc(fecha_referencia, contrato.tipo_contrato_cliente_proveedor)
        alertas_ipc = [a for a in todas_alertas_ipc if a.contrato.id == contrato.id]
    elif contrato.tipo_condicion_ipc == 'SALARIO_MINIMO':
        from gestion.services.alertas import obtener_alertas_salario_minimo
        todas_alertas_sm = obtener_alertas_salario_minimo(fecha_referencia, contrato.tipo_contrato_cliente_proveedor)
        alertas_salario_minimo = [a for a in todas_alertas_sm if a.contrato.id == contrato.id]
    
    context = {
        'contrato': contrato,
        'vista_vigente': vista_vigente,
        'fecha_referencia': fecha_referencia,
        'otrosis': otrosis,
        'seguimientos_contrato': seguimientos_contrato,
        'polizas_con_seguimiento': polizas_con_seguimiento,
        'seguimientos_poliza_generales': seguimientos_poliza_generales,
        'requisitos_polizas': requisitos_polizas,
        'ultimo_calculo_ipc_aplicado': ultimo_calculo_ipc_aplicado,
        'alertas_ipc': alertas_ipc,
        'alertas_salario_minimo': alertas_salario_minimo,
        'titulo': f'Vista Vigente - Contrato {contrato.num_contrato}'
    }
    return render(request, 'gestion/contratos/vista_vigente.html', context)

@login_required_custom
def exportar_contratos(request):
    """Vista para exportar contratos con filtros avanzados"""
    fecha_actual = timezone.now().date()
    
    if request.method == 'POST':
        form = FiltroExportacionContratosForm(request.POST)
        
        if form.is_valid():
            queryset = Contrato.objects.select_related(
                'arrendatario', 'proveedor', 'local', 'tipo_contrato', 'tipo_servicio'
            ).prefetch_related('otrosi').all()
            
            estado = form.cleaned_data.get('estado')
            tipo_contrato_cliente_proveedor = form.cleaned_data.get('tipo_contrato_cliente_proveedor')
            tipo_contrato = form.cleaned_data.get('tipo_contrato')
            fecha_inicio_desde = form.cleaned_data.get('fecha_inicio_desde')
            fecha_inicio_hasta = form.cleaned_data.get('fecha_inicio_hasta')
            fecha_final_desde = form.cleaned_data.get('fecha_final_desde')
            fecha_final_hasta = form.cleaned_data.get('fecha_final_hasta')
            arrendatario = form.cleaned_data.get('arrendatario')
            local = form.cleaned_data.get('local')
            modalidad_pago = form.cleaned_data.get('modalidad_pago')
            prorroga_automatica = form.cleaned_data.get('prorroga_automatica')
            
            if tipo_contrato_cliente_proveedor:
                queryset = queryset.filter(tipo_contrato_cliente_proveedor=tipo_contrato_cliente_proveedor)
            
            if tipo_contrato:
                queryset = queryset.filter(tipo_contrato=tipo_contrato)
            
            if fecha_inicio_desde:
                queryset = queryset.filter(fecha_inicial_contrato__gte=fecha_inicio_desde)
            
            if fecha_inicio_hasta:
                queryset = queryset.filter(fecha_inicial_contrato__lte=fecha_inicio_hasta)
            
            if fecha_final_desde:
                queryset = queryset.filter(
                    Q(fecha_final_actualizada__gte=fecha_final_desde) |
                    Q(fecha_final_actualizada__isnull=True, fecha_final_inicial__gte=fecha_final_desde)
                )
            
            if fecha_final_hasta:
                queryset = queryset.filter(
                    Q(fecha_final_actualizada__lte=fecha_final_hasta) |
                    Q(fecha_final_actualizada__isnull=True, fecha_final_inicial__lte=fecha_final_hasta)
                )
            
            if arrendatario:
                queryset = queryset.filter(arrendatario=arrendatario)
            
            if local:
                queryset = queryset.filter(local=local)
            
            if modalidad_pago:
                queryset = queryset.filter(modalidad_pago=modalidad_pago)
            
            if prorroga_automatica:
                if prorroga_automatica == 'si':
                    queryset = queryset.filter(prorroga_automatica=True)
                elif prorroga_automatica == 'no':
                    queryset = queryset.filter(prorroga_automatica=False)
            
            contratos_lista = list(queryset)
            
            if estado:
                contratos_filtrados = []
                for contrato in contratos_lista:
                    es_vencido = _es_contrato_vencido(contrato, fecha_actual)
                    if estado == 'vigentes' and not es_vencido:
                        contratos_filtrados.append(contrato)
                    elif estado == 'vencidos' and es_vencido:
                        contratos_filtrados.append(contrato)
                contratos_lista = contratos_filtrados
            
            if not contratos_lista:
                messages.warning(request, 'No hay contratos que coincidan con los filtros seleccionados.')
                return redirect('gestion:exportar_contratos')
            
            columnas = [
                ColumnaExportacion('Número Contrato', ancho=22),
                ColumnaExportacion('Tipo Contrato (Cliente/Proveedor)', ancho=30),
                ColumnaExportacion('Tipo Contrato (Cliente)', ancho=25),
                ColumnaExportacion('Tipo Servicio (Proveedor)', ancho=25),
                ColumnaExportacion('Tercero', ancho=35),
                ColumnaExportacion('NIT Tercero', ancho=18),
                ColumnaExportacion('Local', ancho=30),
                ColumnaExportacion('Ubicación Local', ancho=30),
                ColumnaExportacion('Área (m²)', ancho=15, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Objeto y Destinación', ancho=40),
                ColumnaExportacion('Fecha Firma', ancho=18, alineacion='center'),
                ColumnaExportacion('Fecha Inicial', ancho=18, alineacion='center'),
                ColumnaExportacion('Fecha Final Inicial', ancho=20, alineacion='center'),
                ColumnaExportacion('Fecha Final Actualizada', ancho=22, alineacion='center'),
                ColumnaExportacion('Duración Inicial (Meses)', ancho=22, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Estado', ancho=15),
                ColumnaExportacion('Prórroga Automática', ancho=20),
                ColumnaExportacion('Días Preaviso', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Terminación Anticipada (Días)', ancho=28, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Modalidad Pago', ancho=25),
                ColumnaExportacion('Canon Fijo', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Canon Mínimo Garantizado / Valor Mensual', ancho=35, es_numerica=True, alineacion='right'),
                ColumnaExportacion('% Ventas', ancho=15, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Reporta Ventas', ancho=18),
                ColumnaExportacion('Día Límite Reporte Ventas', ancho=28, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Cobra Servicios Públicos', ancho=28),
                ColumnaExportacion('Tiene Cláusula SARLAFT', ancho=25),
                ColumnaExportacion('Tiene Cláusula Protección de Datos', ancho=35),
                ColumnaExportacion('Interés Mora', ancho=25),
                ColumnaExportacion('Tipo Condición IPC', ancho=25),
                ColumnaExportacion('Puntos Adicionales IPC', ancho=25, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Periodicidad IPC', ancho=20),
                ColumnaExportacion('Mes Aumento IPC', ancho=20),
                ColumnaExportacion('Tiene Periodo Gracia', ancho=22),
                ColumnaExportacion('Fecha Inicio Periodo Gracia', ancho=30, alineacion='center'),
                ColumnaExportacion('Fecha Fin Periodo Gracia', ancho=28, alineacion='center'),
                ColumnaExportacion('Condición Gracia', ancho=35),
                ColumnaExportacion('Exige Póliza RCE', ancho=20),
                ColumnaExportacion('Valor Asegurado RCE', ancho=25, es_numerica=True, alineacion='right'),
                ColumnaExportacion('PLO RCE', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Patronal RCE', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Gastos Médicos RCE', ancho=22, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Vehículos RCE', ancho=18, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Contratistas RCE', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Perjuicios Extrapatrimoniales RCE', ancho=35, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Daño Moral RCE', ancho=20, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Lucro Cesante RCE', ancho=22, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Meses Vigencia RCE', ancho=22, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Inicio Vigencia RCE', ancho=28, alineacion='center'),
                ColumnaExportacion('Fecha Fin Vigencia RCE', ancho=25, alineacion='center'),
                ColumnaExportacion('Exige Póliza Cumplimiento', ancho=30),
                ColumnaExportacion('Valor Asegurado Cumplimiento', ancho=32, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Remuneraciones Cumplimiento', ancho=30, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Servicios Públicos Cumplimiento', ancho=35, es_numerica=True, alineacion='right'),
                ColumnaExportacion('IVA Cumplimiento', ancho=25, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Cuota Admin Cumplimiento', ancho=30, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Meses Vigencia Cumplimiento', ancho=30, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Inicio Vigencia Cumplimiento', ancho=35, alineacion='center'),
                ColumnaExportacion('Fecha Fin Vigencia Cumplimiento', ancho=32, alineacion='center'),
                ColumnaExportacion('Exige Póliza Arrendamiento', ancho=32),
                ColumnaExportacion('Valor Asegurado Arrendamiento', ancho=35, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Remuneraciones Arrendamiento', ancho=33, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Servicios Públicos Arrendamiento', ancho=38, es_numerica=True, alineacion='right'),
                ColumnaExportacion('IVA Arrendamiento', ancho=28, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Cuota Admin Arrendamiento', ancho=33, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Meses Vigencia Arrendamiento', ancho=33, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Inicio Vigencia Arrendamiento', ancho=38, alineacion='center'),
                ColumnaExportacion('Fecha Fin Vigencia Arrendamiento', ancho=35, alineacion='center'),
                ColumnaExportacion('Exige Póliza Todo Riesgo', ancho=28),
                ColumnaExportacion('Valor Asegurado Todo Riesgo', ancho=32, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Meses Vigencia Todo Riesgo', ancho=30, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Inicio Vigencia Todo Riesgo', ancho=35, alineacion='center'),
                ColumnaExportacion('Fecha Fin Vigencia Todo Riesgo', ancho=32, alineacion='center'),
                ColumnaExportacion('Exige Otras Pólizas', ancho=22),
                ColumnaExportacion('Nombre Otras Pólizas', ancho=28),
                ColumnaExportacion('Valor Asegurado Otras Pólizas', ancho=32, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Meses Vigencia Otras Pólizas', ancho=30, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Fecha Inicio Vigencia Otras Pólizas', ancho=38, alineacion='center'),
                ColumnaExportacion('Fecha Fin Vigencia Otras Pólizas', ancho=35, alineacion='center'),
                ColumnaExportacion('Cláusula Penal Incumplimiento', ancho=32, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Penalidad Terminación Anticipada', ancho=35, es_numerica=True, alineacion='right'),
                ColumnaExportacion('Multa Mora No Restitución', ancho=28, es_numerica=True, alineacion='right'),
                ColumnaExportacion('NIT Concedente', ancho=20),
                ColumnaExportacion('Representante Legal Concedente', ancho=35),
                ColumnaExportacion('Marca Comercial', ancho=25),
                ColumnaExportacion('Supervisor Concedente', ancho=28),
                ColumnaExportacion('Supervisor Contraparte', ancho=30),
                ColumnaExportacion('Otrosí Modificador Fecha Final', ancho=35),
            ]
            
            registros = []
            for contrato in contratos_lista:
                fecha_final = _obtener_fecha_final_contrato(contrato, fecha_actual)
                es_vencido = _es_contrato_vencido(contrato, fecha_actual)
                estado_texto = 'Vencido' if es_vencido else 'Vigente'
                
                # Usar efecto cadena para obtener fecha final vigente hasta fecha_actual
                otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
                    contrato, 'nueva_fecha_final_actualizada', fecha_actual
                )
                if otrosi_modificador:
                    if hasattr(otrosi_modificador, 'numero_otrosi'):
                        otrosi_numero = otrosi_modificador.numero_otrosi
                    elif hasattr(otrosi_modificador, 'numero_renovacion'):
                        otrosi_numero = otrosi_modificador.numero_renovacion
                    else:
                        otrosi_numero = str(otrosi_modificador)
                else:
                    otrosi_numero = 'Contrato Original'
                
                tercero = contrato.obtener_tercero()
                nombre_tercero = tercero.razon_social if tercero else None
                nit_tercero = tercero.nit if tercero else None
                tipo_contrato_nombre = str(contrato.tipo_contrato) if contrato.tipo_contrato else None
                tipo_servicio_nombre = str(contrato.tipo_servicio) if contrato.tipo_servicio else None
                local_nombre = contrato.local.nombre_comercial_stand if contrato.local else None
                local_ubicacion = contrato.local.ubicacion if contrato.local else None
                local_area = float(contrato.local.total_area_m2) if contrato.local and contrato.local.total_area_m2 else None
                
                registros.append((
                    contrato.num_contrato,
                    contrato.get_tipo_contrato_cliente_proveedor_display(),
                    tipo_contrato_nombre,
                    tipo_servicio_nombre,
                    nombre_tercero,
                    nit_tercero,
                    local_nombre,
                    local_ubicacion,
                    local_area,
                    contrato.objeto_destinacion or None,
                    contrato.fecha_firma or None,
                    contrato.fecha_inicial_contrato or None,
                    contrato.fecha_final_inicial or None,
                    contrato.fecha_final_actualizada or None,
                    contrato.duracion_inicial_meses,
                    estado_texto,
                    'Sí' if contrato.prorroga_automatica else 'No',
                    contrato.dias_preaviso_no_renovacion or None,
                    contrato.dias_terminacion_anticipada or None,
                    contrato.get_modalidad_pago_display() if contrato.modalidad_pago else None,
                    float(contrato.valor_canon_fijo) if contrato.valor_canon_fijo else None,
                    float(contrato.canon_minimo_garantizado) if contrato.canon_minimo_garantizado else None,
                    float(contrato.porcentaje_ventas) if contrato.porcentaje_ventas else None,
                    'Sí' if contrato.reporta_ventas else 'No',
                    contrato.dia_limite_reporte_ventas or None,
                    'Sí' if contrato.cobra_servicios_publicos_aparte else 'No',
                    'Sí' if contrato.tiene_clausula_sarlaft else 'No',
                    'Sí' if contrato.tiene_clausula_proteccion_datos else 'No',
                    contrato.interes_mora_pagos or None,
                    contrato.get_tipo_condicion_ipc_display() if contrato.tipo_condicion_ipc else None,
                    float(contrato.puntos_adicionales_ipc) if contrato.puntos_adicionales_ipc else None,
                    contrato.get_periodicidad_ipc_display() if contrato.periodicidad_ipc else None,
                    contrato.fecha_aumento_ipc.strftime('%d/%m/%Y') if contrato.fecha_aumento_ipc else None,
                    'Sí' if contrato.tiene_periodo_gracia else 'No',
                    contrato.fecha_inicio_periodo_gracia or None,
                    contrato.fecha_fin_periodo_gracia or None,
                    contrato.condicion_gracia or None,
                    'Sí' if contrato.exige_poliza_rce else 'No',
                    float(contrato.valor_asegurado_rce) if contrato.valor_asegurado_rce else None,
                    float(contrato.valor_propietario_locatario_ocupante_rce) if contrato.valor_propietario_locatario_ocupante_rce else None,
                    float(contrato.valor_patronal_rce) if contrato.valor_patronal_rce else None,
                    float(contrato.valor_gastos_medicos_rce) if contrato.valor_gastos_medicos_rce else None,
                    float(contrato.valor_vehiculos_rce) if contrato.valor_vehiculos_rce else None,
                    float(contrato.valor_contratistas_rce) if contrato.valor_contratistas_rce else None,
                    float(contrato.valor_perjuicios_extrapatrimoniales_rce) if contrato.valor_perjuicios_extrapatrimoniales_rce else None,
                    float(contrato.valor_dano_moral_rce) if contrato.valor_dano_moral_rce else None,
                    float(contrato.valor_lucro_cesante_rce) if contrato.valor_lucro_cesante_rce else None,
                    contrato.meses_vigencia_rce or None,
                    contrato.fecha_inicio_vigencia_rce or None,
                    contrato.fecha_fin_vigencia_rce or None,
                    'Sí' if contrato.exige_poliza_cumplimiento else 'No',
                    float(contrato.valor_asegurado_cumplimiento) if contrato.valor_asegurado_cumplimiento else None,
                    float(contrato.valor_remuneraciones_cumplimiento) if contrato.valor_remuneraciones_cumplimiento else None,
                    float(contrato.valor_servicios_publicos_cumplimiento) if contrato.valor_servicios_publicos_cumplimiento else None,
                    float(contrato.valor_iva_cumplimiento) if contrato.valor_iva_cumplimiento else None,
                    float(contrato.valor_otros_cumplimiento) if contrato.valor_otros_cumplimiento else None,
                    contrato.meses_vigencia_cumplimiento or None,
                    contrato.fecha_inicio_vigencia_cumplimiento or None,
                    contrato.fecha_fin_vigencia_cumplimiento or None,
                    'Sí' if contrato.exige_poliza_arrendamiento else 'No',
                    float(contrato.valor_asegurado_arrendamiento) if contrato.valor_asegurado_arrendamiento else None,
                    float(contrato.valor_remuneraciones_arrendamiento) if contrato.valor_remuneraciones_arrendamiento else None,
                    float(contrato.valor_servicios_publicos_arrendamiento) if contrato.valor_servicios_publicos_arrendamiento else None,
                    float(contrato.valor_iva_arrendamiento) if contrato.valor_iva_arrendamiento else None,
                    float(contrato.valor_otros_arrendamiento) if contrato.valor_otros_arrendamiento else None,
                    contrato.meses_vigencia_arrendamiento or None,
                    contrato.fecha_inicio_vigencia_arrendamiento or None,
                    contrato.fecha_fin_vigencia_arrendamiento or None,
                    'Sí' if contrato.exige_poliza_todo_riesgo else 'No',
                    float(contrato.valor_asegurado_todo_riesgo) if contrato.valor_asegurado_todo_riesgo else None,
                    contrato.meses_vigencia_todo_riesgo or None,
                    contrato.fecha_inicio_vigencia_todo_riesgo or None,
                    contrato.fecha_fin_vigencia_todo_riesgo or None,
                    'Sí' if contrato.exige_poliza_otra_1 else 'No',
                    contrato.nombre_poliza_otra_1 or None,
                    float(contrato.valor_asegurado_otra_1) if contrato.valor_asegurado_otra_1 else None,
                    contrato.meses_vigencia_otra_1 or None,
                    contrato.fecha_inicio_vigencia_otra_1 or None,
                    contrato.fecha_fin_vigencia_otra_1 or None,
                    float(contrato.clausula_penal_incumplimiento) if contrato.clausula_penal_incumplimiento else None,
                    float(contrato.penalidad_terminacion_anticipada) if contrato.penalidad_terminacion_anticipada else None,
                    float(contrato.multa_mora_no_restitucion) if contrato.multa_mora_no_restitucion else None,
                    contrato.nit_concedente,
                    contrato.rep_legal_concedente,
                    contrato.marca_comercial or None,
                    contrato.supervisor_concedente or None,
                    contrato.supervisor_contraparte or None,
                    otrosi_numero,
                ))
            
            try:
                archivo = generar_excel_corporativo(
                    nombre_hoja='Contratos',
                    columnas=columnas,
                    registros=registros,
                )
            except ExportacionVaciaError as error:
                messages.warning(request, str(error))
                return redirect('gestion:exportar_contratos')
            
            return _respuesta_archivo_excel(archivo, 'contratos_exportados')
    else:
        form = FiltroExportacionContratosForm()
    
    total_contratos = Contrato.objects.count()
    context = {
        'form': form,
        'total_contratos': total_contratos,
    }
    return render(request, 'gestion/exportaciones/contratos.html', context)


@login_required_custom
def autorizar_renovacion_automatica(request, contrato_id):
    """Vista para autorizar renovación automática de un contrato"""
    from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
    from gestion.forms_renovacion_automatica import RenovacionAutomaticaForm
    from gestion.services.alertas import obtener_alertas_renovacion_automatica
    from datetime import date
    
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if not contrato.prorroga_automatica:
        messages.error(request, 'Este contrato no tiene prórroga automática activa.')
        return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
    
    fecha_actual = date.today()
    fecha_final_actual = _obtener_fecha_final_contrato(contrato, fecha_actual)
    
    if not fecha_final_actual:
        messages.error(request, 'No se puede determinar la fecha final del contrato.')
        return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
    
    # Inicializar valores_iniciales_polizas para evitar UnboundLocalError
    valores_iniciales_polizas = {}
    
    if request.method == 'POST':
        form = RenovacionAutomaticaForm(request.POST, contrato=contrato, contrato_id=contrato.id)
        
        if form.is_valid():
            renovacion = form.save(commit=False)
            renovacion.contrato = contrato
            
            usar_duracion_inicial_str = form.cleaned_data.get('usar_duracion_inicial', 'si')
            usar_duracion_inicial = usar_duracion_inicial_str == 'si'
            meses_renovacion = form.cleaned_data.get('meses_renovacion')
            
            if usar_duracion_inicial:
                meses_renovacion = contrato.duracion_inicial_meses
            
            if not meses_renovacion:
                messages.error(request, 'Debe especificar el número de meses para la renovación.')
                return redirect('gestion:autorizar_renovacion_automatica', contrato_id=contrato.id)
            
            from gestion.utils import calcular_fecha_vencimiento
            from datetime import timedelta
            
            nueva_fecha_final = calcular_fecha_vencimiento(fecha_final_actual, meses_renovacion)
            fecha_inicio_renovacion = fecha_final_actual + timedelta(days=1)
            
            renovacion.fecha_inicio_nueva_vigencia = fecha_inicio_renovacion
            renovacion.nueva_fecha_final_actualizada = nueva_fecha_final
            renovacion.meses_renovacion = meses_renovacion
            renovacion.usar_duracion_inicial = usar_duracion_inicial
            renovacion.fecha_renovacion = fecha_actual
            renovacion.fecha_final_anterior = fecha_final_actual
            renovacion.estado = 'APROBADO'
            renovacion.effective_from = fecha_inicio_renovacion
            
            # Establecer descripción si no se proporcionó
            if not renovacion.descripcion:
                renovacion.descripcion = f'Renovación automática por {meses_renovacion} meses. Autorizada por {request.user.get_username()}.'
            
            # Establecer observaciones si no se proporcionaron
            if not renovacion.observaciones:
                renovacion.observaciones = f'Renovación automática por {meses_renovacion} meses. Autorizada por {request.user.get_username()}.'
            
            from gestion.utils_auditoria import guardar_con_auditoria
            guardar_con_auditoria(renovacion, request.user, es_nuevo=True)
            
            renovacion.fecha_aprobacion = timezone.now()
            renovacion.aprobado_por = request.user.get_username()
            renovacion.save()
            
            # IMPORTANTE: NO modificar los campos de pólizas del contrato base.
            # Los valores de pólizas deben estar solo en la renovación automática
            # y obtenerse mediante el efecto cadena en get_polizas_requeridas_contrato.
            # Esto permite que la vista vigente muestre correctamente el estado histórico
            # del contrato según la fecha de referencia seleccionada.
            
            # Actualizar solo campos de control de renovación automática
            contrato.ultima_renovacion_automatica_por = request.user.get_username()
            contrato.fecha_ultima_renovacion_automatica = timezone.now().date()
            # NO incrementar total_renovaciones_automaticas, se calcula dinámicamente
            contrato.save()
            
            messages.success(
                request,
                f'Renovación automática autorizada exitosamente. El contrato ha sido extendido hasta {renovacion.nueva_fecha_final_actualizada.strftime("%d de %B de %Y")}.'
            )
            return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form, prefijo_emoji='❌ ')
    else:
        form = RenovacionAutomaticaForm(contrato=contrato)
        
        # Obtener el último OtroSi aprobado previo (sin importar fecha de vigencia)
        # Esto es para inicializar el formulario con los valores correctos
        from gestion.models import OtroSi, RenovacionAutomatica
        
        ultimo_otrosi_previo = OtroSi.objects.filter(
            contrato=contrato,
            estado='APROBADO'
        ).order_by('-fecha_creacion', '-version').first()
        
        # Obtener la última Renovación Automática aprobada previa
        ultima_renovacion_previo = RenovacionAutomatica.objects.filter(
            contrato=contrato,
            estado='APROBADO'
        ).order_by('-fecha_creacion', '-version').first()
        
        # Determinar cuál es el más reciente (comparar por fecha_creacion)
        evento_base = None
        if ultimo_otrosi_previo and ultima_renovacion_previo:
            if ultimo_otrosi_previo.fecha_creacion >= ultima_renovacion_previo.fecha_creacion:
                evento_base = ultimo_otrosi_previo
            else:
                evento_base = ultima_renovacion_previo
        elif ultimo_otrosi_previo:
            evento_base = ultimo_otrosi_previo
        elif ultima_renovacion_previo:
            evento_base = ultima_renovacion_previo
        
        # Preparar valores iniciales de pólizas para JavaScript
        valores_iniciales_polizas = {}
        if evento_base and getattr(evento_base, 'modifica_polizas', False):
            # Usar valores del último evento aprobado que modifica pólizas
            otrosi_base = evento_base
        else:
            # Usar valores del contrato inicial
            otrosi_base = None
        
        # Función auxiliar para obtener valor inicial
        def obtener_valor_inicial(campo_evento, campo_contrato):
            if otrosi_base:
                valor = getattr(otrosi_base, campo_evento, None)
                if valor is not None:
                    return valor
            valor_contrato = getattr(contrato, campo_contrato, None)
            return valor_contrato
        
        # RCE
        if contrato.exige_poliza_rce or (otrosi_base and otrosi_base.nuevo_exige_poliza_rce):
            valores_rce = {
                'exige': obtener_valor_inicial('nuevo_exige_poliza_rce', 'exige_poliza_rce') or False,
                'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_rce', 'valor_asegurado_rce') or ''),
                'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_rce', 'meses_vigencia_rce') or '',
                'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce') or ''),
                'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_rce', 'fecha_fin_vigencia_rce') or ''),
            }
            
            if contrato.tipo_contrato_cliente_proveedor == 'CLIENTE':
                valores_rce.update({
                    'valor_plo': str(obtener_valor_inicial('nuevo_valor_propietario_locatario_ocupante_rce', 'valor_propietario_locatario_ocupante_rce') or ''),
                    'valor_patronal': str(obtener_valor_inicial('nuevo_valor_patronal_rce', 'valor_patronal_rce') or ''),
                    'valor_gastos_medicos': str(obtener_valor_inicial('nuevo_valor_gastos_medicos_rce', 'valor_gastos_medicos_rce') or ''),
                    'valor_vehiculos': str(obtener_valor_inicial('nuevo_valor_vehiculos_rce', 'valor_vehiculos_rce') or ''),
                    'valor_contratistas': str(obtener_valor_inicial('nuevo_valor_contratistas_rce', 'valor_contratistas_rce') or ''),
                    'valor_perjuicios': str(obtener_valor_inicial('nuevo_valor_perjuicios_extrapatrimoniales_rce', 'valor_perjuicios_extrapatrimoniales_rce') or ''),
                    'valor_dano_moral': str(obtener_valor_inicial('nuevo_valor_dano_moral_rce', 'valor_dano_moral_rce') or ''),
                    'valor_lucro_cesante': str(obtener_valor_inicial('nuevo_valor_lucro_cesante_rce', 'valor_lucro_cesante_rce') or ''),
                })
            elif contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
                valores_rce.update({
                    'rce_cobertura_danos_materiales': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_materiales', 'rce_cobertura_danos_materiales') or ''),
                    'rce_cobertura_lesiones_personales': str(obtener_valor_inicial('nuevo_rce_cobertura_lesiones_personales', 'rce_cobertura_lesiones_personales') or ''),
                    'rce_cobertura_muerte_terceros': str(obtener_valor_inicial('nuevo_rce_cobertura_muerte_terceros', 'rce_cobertura_muerte_terceros') or ''),
                    'rce_cobertura_danos_bienes_terceros': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_bienes_terceros', 'rce_cobertura_danos_bienes_terceros') or ''),
                    'rce_cobertura_responsabilidad_patronal': str(obtener_valor_inicial('nuevo_rce_cobertura_responsabilidad_patronal', 'rce_cobertura_responsabilidad_patronal') or ''),
                    'rce_cobertura_responsabilidad_cruzada': str(obtener_valor_inicial('nuevo_rce_cobertura_responsabilidad_cruzada', 'rce_cobertura_responsabilidad_cruzada') or ''),
                    'rce_cobertura_danos_contratistas': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_contratistas', 'rce_cobertura_danos_contratistas') or ''),
                    'rce_cobertura_danos_ejecucion_contrato': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_ejecucion_contrato', 'rce_cobertura_danos_ejecucion_contrato') or ''),
                    'rce_cobertura_danos_predios_vecinos': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_predios_vecinos', 'rce_cobertura_danos_predios_vecinos') or ''),
                    'rce_cobertura_gastos_medicos': str(obtener_valor_inicial('nuevo_rce_cobertura_gastos_medicos', 'rce_cobertura_gastos_medicos') or ''),
                    'rce_cobertura_gastos_defensa': str(obtener_valor_inicial('nuevo_rce_cobertura_gastos_defensa', 'rce_cobertura_gastos_defensa') or ''),
                    'rce_cobertura_perjuicios_patrimoniales': str(obtener_valor_inicial('nuevo_rce_cobertura_perjuicios_patrimoniales', 'rce_cobertura_perjuicios_patrimoniales') or ''),
                })
            
            valores_iniciales_polizas['rce'] = valores_rce
        
        # Cumplimiento
        if contrato.exige_poliza_cumplimiento or (otrosi_base and otrosi_base.nuevo_exige_poliza_cumplimiento):
            valores_cumplimiento = {
                'exige': obtener_valor_inicial('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento') or False,
                'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_cumplimiento', 'valor_asegurado_cumplimiento') or ''),
                'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_cumplimiento', 'meses_vigencia_cumplimiento') or '',
                'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento') or ''),
                'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento') or ''),
            }
            
            if contrato.tipo_contrato_cliente_proveedor == 'CLIENTE':
                valor_remuneraciones = obtener_valor_inicial('nuevo_valor_remuneraciones_cumplimiento', 'valor_remuneraciones_cumplimiento')
                valores_cumplimiento.update({
                    'valor_remuneraciones': str(valor_remuneraciones or ''),
                    'valor_servicios_publicos': str(obtener_valor_inicial('nuevo_valor_servicios_publicos_cumplimiento', 'valor_servicios_publicos_cumplimiento') or ''),
                    'valor_iva': str(obtener_valor_inicial('nuevo_valor_iva_cumplimiento', 'valor_iva_cumplimiento') or ''),
                    'valor_otros': str(obtener_valor_inicial('nuevo_valor_otros_cumplimiento', 'valor_otros_cumplimiento') or ''),
                })
            elif contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
                valores_cumplimiento.update({
                    'cumplimiento_amparo_cumplimiento_contrato': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_cumplimiento_contrato', 'cumplimiento_amparo_cumplimiento_contrato') or ''),
                    'cumplimiento_amparo_buen_manejo_anticipo': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_buen_manejo_anticipo', 'cumplimiento_amparo_buen_manejo_anticipo') or ''),
                    'cumplimiento_amparo_amortizacion_anticipo': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_amortizacion_anticipo', 'cumplimiento_amparo_amortizacion_anticipo') or ''),
                    'cumplimiento_amparo_salarios_prestaciones': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_salarios_prestaciones', 'cumplimiento_amparo_salarios_prestaciones') or ''),
                    'cumplimiento_amparo_aportes_seguridad_social': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_aportes_seguridad_social', 'cumplimiento_amparo_aportes_seguridad_social') or ''),
                    'cumplimiento_amparo_calidad_servicio': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_calidad_servicio', 'cumplimiento_amparo_calidad_servicio') or ''),
                    'cumplimiento_amparo_estabilidad_obra': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_estabilidad_obra', 'cumplimiento_amparo_estabilidad_obra') or ''),
                    'cumplimiento_amparo_calidad_bienes': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_calidad_bienes', 'cumplimiento_amparo_calidad_bienes') or ''),
                    'cumplimiento_amparo_multas': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_multas', 'cumplimiento_amparo_multas') or ''),
                    'cumplimiento_amparo_clausula_penal': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_clausula_penal', 'cumplimiento_amparo_clausula_penal') or ''),
                    'cumplimiento_amparo_sanciones_incumplimiento': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_sanciones_incumplimiento', 'cumplimiento_amparo_sanciones_incumplimiento') or ''),
                })
            
            valores_iniciales_polizas['cumplimiento'] = valores_cumplimiento
        
        # Arrendamiento
        if contrato.exige_poliza_arrendamiento or (otrosi_base and otrosi_base.nuevo_exige_poliza_arrendamiento):
            valores_iniciales_polizas['arrendamiento'] = {
                'exige': obtener_valor_inicial('nuevo_exige_poliza_arrendamiento', 'exige_poliza_arrendamiento') or False,
                'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_arrendamiento', 'valor_asegurado_arrendamiento') or ''),
                'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_arrendamiento', 'meses_vigencia_arrendamiento') or '',
                'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_arrendamiento', 'fecha_inicio_vigencia_arrendamiento') or ''),
                'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_arrendamiento', 'fecha_fin_vigencia_arrendamiento') or ''),
                'valor_remuneraciones': str(obtener_valor_inicial('nuevo_valor_remuneraciones_arrendamiento', 'valor_remuneraciones_arrendamiento') or ''),
                'valor_servicios_publicos': str(obtener_valor_inicial('nuevo_valor_servicios_publicos_arrendamiento', 'valor_servicios_publicos_arrendamiento') or ''),
                'valor_iva': str(obtener_valor_inicial('nuevo_valor_iva_arrendamiento', 'valor_iva_arrendamiento') or ''),
                'valor_otros': str(obtener_valor_inicial('nuevo_valor_otros_arrendamiento', 'valor_otros_arrendamiento') or ''),
            }
        
        # Todo Riesgo
        if contrato.exige_poliza_todo_riesgo or (otrosi_base and otrosi_base.nuevo_exige_poliza_todo_riesgo):
            valores_iniciales_polizas['todo_riesgo'] = {
                'exige': obtener_valor_inicial('nuevo_exige_poliza_todo_riesgo', 'exige_poliza_todo_riesgo') or False,
                'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_todo_riesgo', 'valor_asegurado_todo_riesgo') or ''),
                'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_todo_riesgo', 'meses_vigencia_todo_riesgo') or '',
                'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_todo_riesgo', 'fecha_inicio_vigencia_todo_riesgo') or ''),
                'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_todo_riesgo', 'fecha_fin_vigencia_todo_riesgo') or ''),
            }
        
        # Otras Pólizas
        if contrato.exige_poliza_otra_1 or (otrosi_base and otrosi_base.nuevo_exige_poliza_otra_1):
            valores_iniciales_polizas['otra'] = {
                'exige': obtener_valor_inicial('nuevo_exige_poliza_otra_1', 'exige_poliza_otra_1') or False,
                'nombre': obtener_valor_inicial('nuevo_nombre_poliza_otra_1', 'nombre_poliza_otra_1') or '',
                'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_otra_1', 'valor_asegurado_otra_1') or ''),
                'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_otra_1', 'meses_vigencia_otra_1') or '',
                'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_otra_1', 'fecha_inicio_vigencia_otra_1') or ''),
                'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_otra_1', 'fecha_fin_vigencia_otra_1') or ''),
            }
    
    dias_restantes = (fecha_final_actual - fecha_actual).days if fecha_final_actual >= fecha_actual else (fecha_actual - fecha_final_actual).days * -1
    dias_abs = abs(dias_restantes) if dias_restantes < 0 else dias_restantes
    
    # Convertir valores_iniciales_polizas a JSON para evitar problemas con True/False de Python
    import json
    valores_iniciales_polizas_json = json.dumps(valores_iniciales_polizas)
    
    context = {
        'contrato': contrato,
        'form': form,
        'fecha_final_actual': fecha_final_actual,
        'dias_restantes': dias_restantes,
        'dias_abs': dias_abs,
        'duracion_inicial_meses': contrato.duracion_inicial_meses,
        'valores_iniciales_polizas': valores_iniciales_polizas,
        'valores_iniciales_polizas_json': valores_iniciales_polizas_json,
    }
    return render(request, 'gestion/contratos/autorizar_renovacion_automatica.html', context)


@login_required_custom
def gestion_renovaciones_automaticas(request):
    """Vista para gestionar renovaciones automáticas pendientes y existentes"""
    from gestion.services.alertas import obtener_alertas_renovacion_automatica
    from gestion.models import RenovacionAutomatica
    from datetime import date
    from django.db.models import Q
    
    fecha_actual = date.today()
    filtro_form = FiltroRenovacionesAutomaticasForm(request.GET or None)
    
    alertas = obtener_alertas_renovacion_automatica(fecha_referencia=fecha_actual)
    
    alertas_con_dias_abs = []
    for alerta in alertas:
        # Aplicar filtros si el formulario es válido
        if filtro_form.is_valid():
            tipo_contrato_cliente_proveedor = filtro_form.cleaned_data.get('tipo_contrato_cliente_proveedor')
            tipo_contrato = filtro_form.cleaned_data.get('tipo_contrato')
            tipo_servicio = filtro_form.cleaned_data.get('tipo_servicio')
            buscar = filtro_form.cleaned_data.get('buscar')
            
            # Filtrar por tipo de contrato (Cliente/Proveedor)
            if tipo_contrato_cliente_proveedor and alerta.contrato.tipo_contrato_cliente_proveedor != tipo_contrato_cliente_proveedor:
                continue
            
            # Filtrar por tipo de contrato (para clientes)
            if tipo_contrato and alerta.contrato.tipo_contrato != tipo_contrato:
                continue
            
            # Filtrar por tipo de servicio (para proveedores)
            if tipo_servicio and alerta.contrato.tipo_servicio != tipo_servicio:
                continue
            
            # Filtrar por búsqueda de texto
            if buscar:
                tercero = alerta.contrato.obtener_tercero()
                if tercero:
                    if buscar.lower() not in tercero.razon_social.lower() and buscar.lower() not in (tercero.nit or '').lower():
                        continue
                else:
                    continue
        
        dias_abs = abs(alerta.dias_restantes) if alerta.dias_restantes < 0 else alerta.dias_restantes
        alertas_con_dias_abs.append({
            'alerta': alerta,
            'dias_abs': dias_abs,
        })
    
    renovaciones_existentes = RenovacionAutomatica.objects.select_related('contrato', 'contrato__arrendatario', 'contrato__proveedor', 'contrato__local', 'contrato__tipo_servicio', 'contrato__tipo_contrato', 'contrato__tipo_servicio').order_by('-fecha_aprobacion', '-effective_from', '-version')
    
    # Aplicar filtros a renovaciones existentes
    if filtro_form.is_valid():
        tipo_contrato_cliente_proveedor = filtro_form.cleaned_data.get('tipo_contrato_cliente_proveedor')
        tipo_contrato = filtro_form.cleaned_data.get('tipo_contrato')
        tipo_servicio = filtro_form.cleaned_data.get('tipo_servicio')
        buscar = filtro_form.cleaned_data.get('buscar')
        
        if tipo_contrato_cliente_proveedor:
            renovaciones_existentes = renovaciones_existentes.filter(contrato__tipo_contrato_cliente_proveedor=tipo_contrato_cliente_proveedor)
        
        if tipo_contrato:
            renovaciones_existentes = renovaciones_existentes.filter(contrato__tipo_contrato=tipo_contrato)
        
        if tipo_servicio:
            renovaciones_existentes = renovaciones_existentes.filter(contrato__tipo_servicio=tipo_servicio)
        
        if buscar:
            renovaciones_existentes = renovaciones_existentes.filter(
                Q(contrato__arrendatario__razon_social__icontains=buscar) |
                Q(contrato__arrendatario__nit__icontains=buscar) |
                Q(contrato__proveedor__razon_social__icontains=buscar) |
                Q(contrato__proveedor__nit__icontains=buscar)
            )
    
    tipo_filtro_activo = request.GET.get('tipo_contrato_cliente_proveedor', '')
    
    context = {
        'alertas_con_dias_abs': alertas_con_dias_abs,
        'renovaciones_existentes': renovaciones_existentes,
        'total_alertas': len(alertas_con_dias_abs),
        'fecha_actual': fecha_actual,
        'tipo_filtro': tipo_filtro_activo,
        'filtro_form': filtro_form,
    }
    return render(request, 'gestion/renovaciones_automaticas/lista.html', context)


@login_required_custom
def editar_renovacion_automatica(request, renovacion_id):
    """Vista para editar una renovación automática existente"""
    from gestion.forms_renovacion_automatica import RenovacionAutomaticaForm
    from gestion.models import RenovacionAutomatica
    from gestion.utils_auditoria import guardar_con_auditoria
    from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
    from datetime import date
    
    renovacion = get_object_or_404(RenovacionAutomatica, id=renovacion_id)
    contrato = renovacion.contrato
    
    fecha_actual = date.today()
    
    if request.method == 'POST':
        form = RenovacionAutomaticaForm(request.POST, instance=renovacion, contrato=contrato, contrato_id=contrato.id)
        
        if form.is_valid():
            renovacion = form.save(commit=False)
            guardar_con_auditoria(renovacion, request.user, es_nuevo=False)
            renovacion.save()
            
            messages.success(request, f'Renovación automática {renovacion.numero_renovacion} actualizada exitosamente.')
            return redirect('gestion:gestion_renovaciones_automaticas')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form, prefijo_emoji='❌ ')
    else:
        form = RenovacionAutomaticaForm(instance=renovacion, contrato=contrato, contrato_id=contrato.id)
    
    otrosi_modificador = get_ultimo_otrosi_que_modifico_campo_hasta_fecha(
        contrato, 'nueva_fecha_final_actualizada', fecha_actual
    )
    
    def obtener_valor_inicial(campo_evento, campo_contrato):
        if otrosi_modificador and hasattr(otrosi_modificador, 'modifica_polizas') and otrosi_modificador.modifica_polizas:
            valor = getattr(otrosi_modificador, campo_evento, None)
            if valor is not None:
                return valor
        return getattr(contrato, campo_contrato, None)
    
    valores_iniciales_polizas = {}
    if contrato.exige_poliza_rce or (otrosi_modificador and hasattr(otrosi_modificador, 'nuevo_exige_poliza_rce') and otrosi_modificador.nuevo_exige_poliza_rce):
        valores_rce = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_rce', 'exige_poliza_rce') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_rce', 'valor_asegurado_rce') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_rce', 'meses_vigencia_rce'),
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_rce', 'fecha_fin_vigencia_rce') or ''),
        }
        
        if contrato.tipo_contrato_cliente_proveedor == 'CLIENTE':
            valores_rce.update({
                'valor_plo': str(obtener_valor_inicial('nuevo_valor_propietario_locatario_ocupante_rce', 'valor_propietario_locatario_ocupante_rce') or ''),
                'valor_patronal': str(obtener_valor_inicial('nuevo_valor_patronal_rce', 'valor_patronal_rce') or ''),
                'valor_gastos_medicos': str(obtener_valor_inicial('nuevo_valor_gastos_medicos_rce', 'valor_gastos_medicos_rce') or ''),
                'valor_vehiculos': str(obtener_valor_inicial('nuevo_valor_vehiculos_rce', 'valor_vehiculos_rce') or ''),
                'valor_contratistas': str(obtener_valor_inicial('nuevo_valor_contratistas_rce', 'valor_contratistas_rce') or ''),
                'valor_perjuicios': str(obtener_valor_inicial('nuevo_valor_perjuicios_extrapatrimoniales_rce', 'valor_perjuicios_extrapatrimoniales_rce') or ''),
                'valor_dano_moral': str(obtener_valor_inicial('nuevo_valor_dano_moral_rce', 'valor_dano_moral_rce') or ''),
                'valor_lucro_cesante': str(obtener_valor_inicial('nuevo_valor_lucro_cesante_rce', 'valor_lucro_cesante_rce') or ''),
            })
        elif contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
            valores_rce.update({
                'rce_cobertura_danos_materiales': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_materiales', 'rce_cobertura_danos_materiales') or ''),
                'rce_cobertura_lesiones_personales': str(obtener_valor_inicial('nuevo_rce_cobertura_lesiones_personales', 'rce_cobertura_lesiones_personales') or ''),
                'rce_cobertura_muerte_terceros': str(obtener_valor_inicial('nuevo_rce_cobertura_muerte_terceros', 'rce_cobertura_muerte_terceros') or ''),
                'rce_cobertura_danos_bienes_terceros': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_bienes_terceros', 'rce_cobertura_danos_bienes_terceros') or ''),
                'rce_cobertura_responsabilidad_patronal': str(obtener_valor_inicial('nuevo_rce_cobertura_responsabilidad_patronal', 'rce_cobertura_responsabilidad_patronal') or ''),
                'rce_cobertura_responsabilidad_cruzada': str(obtener_valor_inicial('nuevo_rce_cobertura_responsabilidad_cruzada', 'rce_cobertura_responsabilidad_cruzada') or ''),
                'rce_cobertura_danos_contratistas': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_contratistas', 'rce_cobertura_danos_contratistas') or ''),
                'rce_cobertura_danos_ejecucion_contrato': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_ejecucion_contrato', 'rce_cobertura_danos_ejecucion_contrato') or ''),
                'rce_cobertura_danos_predios_vecinos': str(obtener_valor_inicial('nuevo_rce_cobertura_danos_predios_vecinos', 'rce_cobertura_danos_predios_vecinos') or ''),
                'rce_cobertura_gastos_medicos': str(obtener_valor_inicial('nuevo_rce_cobertura_gastos_medicos', 'rce_cobertura_gastos_medicos') or ''),
                'rce_cobertura_gastos_defensa': str(obtener_valor_inicial('nuevo_rce_cobertura_gastos_defensa', 'rce_cobertura_gastos_defensa') or ''),
                'rce_cobertura_perjuicios_patrimoniales': str(obtener_valor_inicial('nuevo_rce_cobertura_perjuicios_patrimoniales', 'rce_cobertura_perjuicios_patrimoniales') or ''),
            })
        
        valores_iniciales_polizas['rce'] = valores_rce
    
    if contrato.exige_poliza_cumplimiento or (otrosi_modificador and hasattr(otrosi_modificador, 'nuevo_exige_poliza_cumplimiento') and otrosi_modificador.nuevo_exige_poliza_cumplimiento):
        valores_cumplimiento = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_cumplimiento', 'valor_asegurado_cumplimiento') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_cumplimiento', 'meses_vigencia_cumplimiento'),
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento') or ''),
        }
        
        if contrato.tipo_contrato_cliente_proveedor == 'CLIENTE':
            valor_remuneraciones = obtener_valor_inicial('nuevo_valor_remuneraciones_cumplimiento', 'valor_remuneraciones_cumplimiento')
            valores_cumplimiento.update({
                'valor_remuneraciones': str(valor_remuneraciones or ''),
                'valor_servicios_publicos': str(obtener_valor_inicial('nuevo_valor_servicios_publicos_cumplimiento', 'valor_servicios_publicos_cumplimiento') or ''),
                'valor_iva': str(obtener_valor_inicial('nuevo_valor_iva_cumplimiento', 'valor_iva_cumplimiento') or ''),
                'valor_otros': str(obtener_valor_inicial('nuevo_valor_otros_cumplimiento', 'valor_otros_cumplimiento') or ''),
            })
        elif contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
            valores_cumplimiento.update({
                'cumplimiento_amparo_cumplimiento_contrato': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_cumplimiento_contrato', 'cumplimiento_amparo_cumplimiento_contrato') or ''),
                'cumplimiento_amparo_buen_manejo_anticipo': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_buen_manejo_anticipo', 'cumplimiento_amparo_buen_manejo_anticipo') or ''),
                'cumplimiento_amparo_amortizacion_anticipo': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_amortizacion_anticipo', 'cumplimiento_amparo_amortizacion_anticipo') or ''),
                'cumplimiento_amparo_salarios_prestaciones': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_salarios_prestaciones', 'cumplimiento_amparo_salarios_prestaciones') or ''),
                'cumplimiento_amparo_aportes_seguridad_social': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_aportes_seguridad_social', 'cumplimiento_amparo_aportes_seguridad_social') or ''),
                'cumplimiento_amparo_calidad_servicio': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_calidad_servicio', 'cumplimiento_amparo_calidad_servicio') or ''),
                'cumplimiento_amparo_estabilidad_obra': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_estabilidad_obra', 'cumplimiento_amparo_estabilidad_obra') or ''),
                'cumplimiento_amparo_calidad_bienes': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_calidad_bienes', 'cumplimiento_amparo_calidad_bienes') or ''),
                'cumplimiento_amparo_multas': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_multas', 'cumplimiento_amparo_multas') or ''),
                'cumplimiento_amparo_clausula_penal': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_clausula_penal', 'cumplimiento_amparo_clausula_penal') or ''),
                'cumplimiento_amparo_sanciones_incumplimiento': str(obtener_valor_inicial('nuevo_cumplimiento_amparo_sanciones_incumplimiento', 'cumplimiento_amparo_sanciones_incumplimiento') or ''),
            })
        
        valores_iniciales_polizas['cumplimiento'] = valores_cumplimiento
    
    if contrato.exige_poliza_arrendamiento or (otrosi_modificador and hasattr(otrosi_modificador, 'nuevo_exige_poliza_arrendamiento') and otrosi_modificador.nuevo_exige_poliza_arrendamiento):
        valores_iniciales_polizas['arrendamiento'] = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_arrendamiento', 'exige_poliza_arrendamiento') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_arrendamiento', 'valor_asegurado_arrendamiento') or ''),
            'valor_remuneraciones': str(obtener_valor_inicial('nuevo_valor_remuneraciones_arrendamiento', 'valor_remuneraciones_arrendamiento') or ''),
            'valor_servicios_publicos': str(obtener_valor_inicial('nuevo_valor_servicios_publicos_arrendamiento', 'valor_servicios_publicos_arrendamiento') or ''),
            'valor_iva': str(obtener_valor_inicial('nuevo_valor_iva_arrendamiento', 'valor_iva_arrendamiento') or ''),
            'valor_otros': str(obtener_valor_inicial('nuevo_valor_otros_arrendamiento', 'valor_otros_arrendamiento') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_arrendamiento', 'meses_vigencia_arrendamiento'),
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_arrendamiento', 'fecha_inicio_vigencia_arrendamiento') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_arrendamiento', 'fecha_fin_vigencia_arrendamiento') or ''),
        }
    
    if contrato.exige_poliza_todo_riesgo or (otrosi_modificador and hasattr(otrosi_modificador, 'nuevo_exige_poliza_todo_riesgo') and otrosi_modificador.nuevo_exige_poliza_todo_riesgo):
        valores_iniciales_polizas['todo_riesgo'] = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_todo_riesgo', 'exige_poliza_todo_riesgo') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_todo_riesgo', 'valor_asegurado_todo_riesgo') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_todo_riesgo', 'meses_vigencia_todo_riesgo'),
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_todo_riesgo', 'fecha_inicio_vigencia_todo_riesgo') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_todo_riesgo', 'fecha_fin_vigencia_todo_riesgo') or ''),
        }
    
    if contrato.exige_poliza_otra_1 or (otrosi_modificador and hasattr(otrosi_modificador, 'nuevo_exige_poliza_otra_1') and otrosi_modificador.nuevo_exige_poliza_otra_1):
        valores_iniciales_polizas['otra'] = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_otra_1', 'exige_poliza_otra_1') or False,
            'nombre': obtener_valor_inicial('nuevo_nombre_poliza_otra_1', 'nombre_poliza_otra_1') or '',
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_otra_1', 'valor_asegurado_otra_1') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_otra_1', 'meses_vigencia_otra_1'),
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_otra_1', 'fecha_inicio_vigencia_otra_1') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_otra_1', 'fecha_fin_vigencia_otra_1') or ''),
        }
    
    context = {
        'renovacion': renovacion,
        'contrato': contrato,
        'form': form,
        'valores_iniciales_polizas': valores_iniciales_polizas,
    }
    return render(request, 'gestion/renovaciones_automaticas/editar.html', context)


@login_required_custom
def anular_renovacion_automatica(request, renovacion_id):
    """Vista para eliminar una renovación automática"""
    from gestion.models import RenovacionAutomatica
    
    renovacion = get_object_or_404(RenovacionAutomatica, id=renovacion_id)
    contrato = renovacion.contrato
    numero_renovacion = renovacion.numero_renovacion
    
    if request.method == 'POST':
        if request.POST.get('accion') == 'confirmar':
            renovacion.delete()
            messages.success(request, f'✅ Renovación Automática {numero_renovacion} eliminada exitosamente.')
            return redirect('gestion:gestion_renovaciones_automaticas')
        else:
            messages.info(request, 'Eliminación de renovación automática cancelada.')
            return redirect('gestion:gestion_renovaciones_automaticas')
    
    context = {
        'renovacion': renovacion,
        'contrato': contrato,
        'titulo': f'Eliminar Renovación Automática {numero_renovacion}',
    }
    return render(request, 'gestion/renovaciones_automaticas/anular.html', context)


@admin_required
@login_required_custom
def editar_seguimiento_contrato(request, seguimiento_id):
    """Vista para editar un seguimiento de contrato"""
    seguimiento = get_object_or_404(SeguimientoContrato, id=seguimiento_id)
    contrato = seguimiento.contrato
    
    if request.method == 'POST':
        detalle = request.POST.get('detalle', '').strip()
        if detalle:
            seguimiento.detalle = detalle
            seguimiento.save()
            messages.success(request, 'Seguimiento actualizado correctamente.')
            return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
        else:
            messages.error(request, 'El detalle del seguimiento no puede estar vacío.')
    
    context = {
        'seguimiento': seguimiento,
        'contrato': contrato,
        'titulo': 'Editar Seguimiento de Contrato'
    }
    return render(request, 'gestion/seguimientos/editar_contrato.html', context)


@admin_required
@login_required_custom
def eliminar_seguimiento_contrato(request, seguimiento_id):
    """Vista para eliminar un seguimiento de contrato"""
    seguimiento = get_object_or_404(SeguimientoContrato, id=seguimiento_id)
    contrato = seguimiento.contrato
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'confirmar':
            seguimiento.delete()
            messages.success(request, 'Seguimiento eliminado correctamente.')
            return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
        elif accion == 'cancelar':
            return redirect('gestion:detalle_contrato', contrato_id=contrato.id)
    
    context = {
        'seguimiento': seguimiento,
        'contrato': contrato,
        'titulo': 'Eliminar Seguimiento de Contrato'
    }
    return render(request, 'gestion/seguimientos/eliminar_contrato.html', context)


@admin_required
@login_required_custom
def editar_seguimiento_poliza(request, seguimiento_id):
    """Vista para editar un seguimiento de póliza"""
    seguimiento = get_object_or_404(SeguimientoPoliza, id=seguimiento_id)
    contrato = seguimiento.contrato
    
    if not contrato and seguimiento.poliza:
        contrato = seguimiento.poliza.contrato
    
    if request.method == 'POST':
        detalle = request.POST.get('detalle', '').strip()
        if detalle:
            seguimiento.detalle = detalle
            seguimiento.save()
            messages.success(request, 'Seguimiento de póliza actualizado correctamente.')
            if contrato:
                return redirect('gestion:vista_vigente_contrato', contrato_id=contrato.id)
            elif seguimiento.poliza:
                return redirect('gestion:gestionar_polizas', contrato_id=seguimiento.poliza.contrato.id)
            else:
                messages.error(request, 'No se pudo determinar el contrato asociado.')
                return redirect('gestion:lista_contratos')
        else:
            messages.error(request, 'El detalle del seguimiento no puede estar vacío.')
    
    context = {
        'seguimiento': seguimiento,
        'contrato': contrato,
        'titulo': 'Editar Seguimiento de Póliza'
    }
    return render(request, 'gestion/seguimientos/editar_poliza.html', context)


@admin_required
@login_required_custom
def eliminar_seguimiento_poliza(request, seguimiento_id):
    """Vista para eliminar un seguimiento de póliza"""
    seguimiento = get_object_or_404(SeguimientoPoliza, id=seguimiento_id)
    contrato = seguimiento.contrato
    
    if not contrato and seguimiento.poliza:
        contrato = seguimiento.poliza.contrato
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'confirmar':
            seguimiento.delete()
            messages.success(request, 'Seguimiento de póliza eliminado correctamente.')
            if contrato:
                return redirect('gestion:vista_vigente_contrato', contrato_id=contrato.id)
            elif seguimiento.poliza:
                return redirect('gestion:gestionar_polizas', contrato_id=seguimiento.poliza.contrato.id)
            else:
                messages.error(request, 'No se pudo determinar el contrato asociado.')
                return redirect('gestion:lista_contratos')
        elif accion == 'cancelar':
            if contrato:
                return redirect('gestion:vista_vigente_contrato', contrato_id=contrato.id)
            elif seguimiento.poliza:
                return redirect('gestion:gestionar_polizas', contrato_id=seguimiento.poliza.contrato.id)
            else:
                return redirect('gestion:lista_contratos')
    
    context = {
        'seguimiento': seguimiento,
        'contrato': contrato,
        'titulo': 'Eliminar Seguimiento de Póliza'
    }
    return render(request, 'gestion/seguimientos/eliminar_poliza.html', context)




