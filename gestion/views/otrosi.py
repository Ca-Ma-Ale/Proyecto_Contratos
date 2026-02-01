import json

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from gestion.decorators import admin_required, login_required_custom
from gestion.models import Contrato
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion

from gestion.utils_otrosi import (
    get_otrosi_vigente,
    get_condiciones_polizas_vigentes,
    get_vista_vigente_contrato,
    get_polizas_requeridas_contrato,
)
from .utils import _construir_requisitos_poliza

@login_required_custom
def lista_otrosi(request, contrato_id):
    """Lista todos los Otro Sí de un contrato"""
    import json
    contrato = get_object_or_404(Contrato, id=contrato_id)
    otrosis = contrato.otrosi.all().order_by('-effective_from', '-version')
    
    # Obtener el Otro Sí vigente
    otrosi_vigente = get_otrosi_vigente(contrato)
    
    # Preparar datos JSON de todos los otros sí para JavaScript
    # Y agregar información de restricciones directamente a cada objeto
    from gestion.utils_otrosi import tiene_otrosi_posteriores
    otrosis_data = []
    otrosis_lista = []
    for otrosi in otrosis:
        cambios = otrosi.get_cambios_resumen()
        tiene_posteriores = tiene_otrosi_posteriores(otrosi)
        # Agregar atributo temporal al objeto
        otrosi.tiene_posteriores = tiene_posteriores
        otrosis_lista.append(otrosi)
        otrosis_data.append({
            'id': otrosi.id,
            'numero': otrosi.numero_otrosi,
            'version': otrosi.version,
            'tipo': otrosi.get_tipo_display(),
            'vigencia': str(otrosi.effective_from),
            'cambios': cambios,
            'es_vigente': otrosi == otrosi_vigente
        })
    
    context = {
        'contrato': contrato,
        'otrosis': otrosis_lista,
        'otrosi_vigente': otrosi_vigente,
        'otrosis_data_json': json.dumps(otrosis_data),
        'titulo': f'Otro Sí - Contrato {contrato.num_contrato}'
    }
    return render(request, 'gestion/otrosi/lista.html', context)




@login_required_custom
def nuevo_otrosi(request, contrato_id):
    """Crea un nuevo Otro Sí para un contrato"""
    from gestion.forms_otrosi import OtroSiForm
    from gestion.models import OtroSi
    
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    # Obtener el último OtroSi aprobado previo (sin importar fecha de vigencia)
    # Esto es para inicializar el formulario con los valores correctos
    ultimo_otrosi_previo = OtroSi.objects.filter(
        contrato=contrato,
        estado='APROBADO'
    ).order_by('-fecha_creacion', '-version').first()
    
    # Obtener condiciones de pólizas: del último OtroSi previo si modifica pólizas, sino del contrato
    if ultimo_otrosi_previo and ultimo_otrosi_previo.modifica_polizas:
        from datetime import date
        polizas_requeridas = get_polizas_requeridas_contrato(contrato, ultimo_otrosi_previo.effective_from)
        fuente_condiciones = 'otrosi_previo'
        otrosi_vigente_actual = ultimo_otrosi_previo
    else:
        condiciones_polizas = get_condiciones_polizas_vigentes(contrato)
        polizas_requeridas = condiciones_polizas['polizas']
        fuente_condiciones = 'contrato_base'
        otrosi_vigente_actual = None
    
    if request.method == 'POST':
        continuar_desde_advertencia = request.POST.get('continuar_desde_advertencia')
        
        # Si viene desde la advertencia, restaurar datos del formulario desde la sesión
        if continuar_desde_advertencia and 'otrosi_pendiente_advertencia' in request.session:
            datos_sesion = request.session['otrosi_pendiente_advertencia']
            # Crear un nuevo QueryDict con los datos guardados
            from django.http import QueryDict
            form_data = QueryDict(mutable=True)
            form_data_dict = datos_sesion.get('form_data', {})
            for key, value in form_data_dict.items():
                if isinstance(value, list):
                    for v in value:
                        form_data.appendlist(key, v)
                else:
                    form_data[key] = value
            form_data['continuar_desde_advertencia'] = '1'
            form = OtroSiForm(form_data, contrato=contrato, contrato_id=contrato_id)
            del request.session['otrosi_pendiente_advertencia']
        else:
            form = OtroSiForm(request.POST, contrato=contrato, contrato_id=contrato_id)
        
        if form.is_valid():
            otrosi = form.save(commit=False)
            otrosi.contrato = contrato
            
            # Verificar si el otro sí modifica el canon y si existe un cálculo de IPC/Salario Mínimo
            if (otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado) and not continuar_desde_advertencia:
                from gestion.utils_ipc import verificar_calculo_existente_para_fecha
                from decimal import Decimal
                
                # Obtener el nuevo valor del canon del otro sí
                nuevo_valor_canon = otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado
                
                # Verificar cálculos existentes para la fecha de vigencia del otro sí
                fecha_verificacion = otrosi.effective_from
                calculo_info = verificar_calculo_existente_para_fecha(contrato, fecha_verificacion)
                
                # Si no hay cálculo para la fecha exacta, buscar por año
                if not calculo_info['existe']:
                    from datetime import date
                    año_verificacion = fecha_verificacion.year
                    # Buscar cualquier cálculo aplicado en ese año
                    from gestion.models import CalculoIPC, CalculoSalarioMinimo
                    calculo_ipc = CalculoIPC.objects.filter(
                        contrato=contrato,
                        año_aplicacion=año_verificacion,
                        estado='APLICADO'
                    ).order_by('-fecha_aplicacion').first()
                    calculo_sm = CalculoSalarioMinimo.objects.filter(
                        contrato=contrato,
                        año_aplicacion=año_verificacion,
                        estado='APLICADO'
                    ).order_by('-fecha_aplicacion').first()
                    
                    # Determinar cuál cálculo usar (el más reciente si hay ambos)
                    calculo_existente = None
                    tipo_calculo = None
                    if calculo_ipc and calculo_sm:
                        calculo_existente = calculo_ipc if calculo_ipc.fecha_aplicacion >= calculo_sm.fecha_aplicacion else calculo_sm
                        tipo_calculo = 'IPC' if calculo_existente == calculo_ipc else 'Salario Mínimo'
                    elif calculo_ipc:
                        calculo_existente = calculo_ipc
                        tipo_calculo = 'IPC'
                    elif calculo_sm:
                        calculo_existente = calculo_sm
                        tipo_calculo = 'Salario Mínimo'
                else:
                    calculo_existente = calculo_info['calculo']
                    tipo_calculo = calculo_info['tipo']
                
                # Si hay un cálculo existente y el valor es diferente, mostrar advertencia
                if calculo_existente and calculo_existente.estado == 'APLICADO':
                    valor_calculo = calculo_existente.nuevo_canon
                    diferencia = abs(valor_calculo - nuevo_valor_canon)
                    
                    if diferencia > Decimal('0.01'):  # Tolerancia de 1 centavo
                        # Guardar datos del formulario en la sesión para continuar después
                        # Convertir QueryDict a dict mutable
                        form_data_dict = {}
                        for key in request.POST.keys():
                            values = request.POST.getlist(key)
                            if len(values) == 1:
                                form_data_dict[key] = values[0]
                            else:
                                form_data_dict[key] = values
                        
                        request.session['otrosi_pendiente_advertencia'] = {
                            'form_data': form_data_dict,
                            'contrato_id': contrato.id,
                            'es_edicion': False,
                        }
                        
                        context = {
                            'otrosi': otrosi,
                            'contrato': contrato,
                            'calculo_existente': calculo_existente,
                            'tipo_calculo': tipo_calculo,
                            'nuevo_valor_canon': nuevo_valor_canon,
                            'diferencia': diferencia,
                            'es_edicion': False,
                            'titulo': 'Advertencia - Cálculo Existente',
                        }
                        return render(request, 'gestion/otrosi/advertencia_calculo_existente.html', context)
            
            guardar_con_auditoria(otrosi, request.user, es_nuevo=True)
            otrosi.save()
            
            # Si el Otro Sí modifica el canon, actualizar cálculos existentes inmediatamente
            # Esto asegura que la base de datos se actualice cuando se detecta el cálculo existente
            if otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado:
                from gestion.utils_ipc import actualizar_calculos_por_otrosi
                resultado_actualizacion = actualizar_calculos_por_otrosi(
                    otrosi.contrato,
                    otrosi,
                    request.user
                )
                
                if resultado_actualizacion['actualizados'] > 0:
                    detalles_str = ', '.join([
                        f"{d['tipo']} ({d['fecha'].strftime('%d/%m/%Y')})"
                        for d in resultado_actualizacion['detalles']
                    ])
                    if otrosi.estado == 'APROBADO':
                        messages.success(
                            request,
                            f'✅ Otro Sí {otrosi.numero_otrosi} creado exitosamente! '
                            f'Se actualizaron automáticamente {resultado_actualizacion["actualizados"]} cálculo(s) de ajuste: {detalles_str}.'
                        )
                    else:
                        messages.success(
                            request,
                            f'✅ Otro Sí {otrosi.numero_otrosi} creado exitosamente! '
                            f'Cuando se apruebe este Otro Sí, se actualizarán automáticamente {resultado_actualizacion["actualizados"]} cálculo(s) de ajuste: {detalles_str}.'
                        )
                else:
                    messages.success(request, f'✅ Otro Sí {otrosi.numero_otrosi} creado exitosamente!')
            else:
                messages.success(request, f'✅ Otro Sí {otrosi.numero_otrosi} creado exitosamente!')
            
            # Los valores de pólizas ya se guardan en los campos nuevo_* del OtroSi mediante el formulario
            # No necesitamos procesar condiciones adicionales
            
            return redirect('gestion:detalle_otrosi', otrosi_id=otrosi.id)
        else:
            # Agregar mensajes de error específicos
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
            
            if not form.errors:
                messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = OtroSiForm(contrato=contrato, contrato_id=contrato_id)
        # Pre-llenar fecha de Otro Sí con hoy
        from datetime import date
        form.fields['fecha_otrosi'].initial = date.today()
        form.fields['effective_from'].initial = date.today()
    
    # Preparar datos de condiciones de pólizas para el template
    condiciones_para_template = []
    for tipo, config in polizas_requeridas.items():
        condiciones_para_template.append({
            'tipo': tipo,
            'tipo_key': tipo.replace(' ', '').replace('-', '').lower(),
            'config': config,
            'fuente': fuente_condiciones,
        })
    
    # Preparar valores iniciales de pólizas para JavaScript
    valores_iniciales_polizas = {}
    if ultimo_otrosi_previo and ultimo_otrosi_previo.modifica_polizas:
        # Usar valores del último OtroSi aprobado
        otrosi_base = ultimo_otrosi_previo
    else:
        # Usar valores del contrato inicial
        otrosi_base = None
    
    # Función auxiliar para obtener valor inicial
    def obtener_valor_inicial(campo_otrosi, campo_contrato):
        if otrosi_base:
            valor = getattr(otrosi_base, campo_otrosi, None)
            if valor is not None:
                return valor
        return getattr(contrato, campo_contrato, None)
    
    # RCE
    if contrato.exige_poliza_rce or (otrosi_base and otrosi_base.nuevo_exige_poliza_rce):
        valores_iniciales_polizas['rce'] = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_rce', 'exige_poliza_rce') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_rce', 'valor_asegurado_rce') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_rce', 'meses_vigencia_rce') or '',
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_rce', 'fecha_fin_vigencia_rce') or ''),
            'valor_plo': str(obtener_valor_inicial('nuevo_valor_propietario_locatario_ocupante_rce', 'valor_propietario_locatario_ocupante_rce') or ''),
            'valor_patronal': str(obtener_valor_inicial('nuevo_valor_patronal_rce', 'valor_patronal_rce') or ''),
            'valor_gastos_medicos': str(obtener_valor_inicial('nuevo_valor_gastos_medicos_rce', 'valor_gastos_medicos_rce') or ''),
            'valor_vehiculos': str(obtener_valor_inicial('nuevo_valor_vehiculos_rce', 'valor_vehiculos_rce') or ''),
            'valor_contratistas': str(obtener_valor_inicial('nuevo_valor_contratistas_rce', 'valor_contratistas_rce') or ''),
            'valor_perjuicios': str(obtener_valor_inicial('nuevo_valor_perjuicios_extrapatrimoniales_rce', 'valor_perjuicios_extrapatrimoniales_rce') or ''),
            'valor_dano_moral': str(obtener_valor_inicial('nuevo_valor_dano_moral_rce', 'valor_dano_moral_rce') or ''),
            'valor_lucro_cesante': str(obtener_valor_inicial('nuevo_valor_lucro_cesante_rce', 'valor_lucro_cesante_rce') or ''),
        }
    
    # Cumplimiento
    if contrato.exige_poliza_cumplimiento or (otrosi_base and otrosi_base.nuevo_exige_poliza_cumplimiento):
        valores_iniciales_polizas['cumplimiento'] = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_cumplimiento', 'valor_asegurado_cumplimiento') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_cumplimiento', 'meses_vigencia_cumplimiento') or '',
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento') or ''),
            'valor_remuneraciones': str(obtener_valor_inicial('nuevo_valor_remuneraciones_cumplimiento', 'valor_remuneraciones_cumplimiento') or ''),
            'valor_servicios_publicos': str(obtener_valor_inicial('nuevo_valor_servicios_publicos_cumplimiento', 'valor_servicios_publicos_cumplimiento') or ''),
            'valor_iva': str(obtener_valor_inicial('nuevo_valor_iva_cumplimiento', 'valor_iva_cumplimiento') or ''),
            'valor_otros': str(obtener_valor_inicial('nuevo_valor_otros_cumplimiento', 'valor_otros_cumplimiento') or ''),
        }
    
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
    
    # Obtener modalidad de pago actual (del último otro sí aprobado o del contrato)
    from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo
    otrosi_modalidad = get_ultimo_otrosi_que_modifico_campo(contrato, 'nueva_modalidad_pago')
    if otrosi_modalidad and otrosi_modalidad.nueva_modalidad_pago:
        modalidad_actual = otrosi_modalidad.nueva_modalidad_pago
    else:
        modalidad_actual = contrato.modalidad_pago or ''
    
    context = {
        'form': form,
        'contrato': contrato,
        'condiciones_para_template': condiciones_para_template,
        'otrosi_vigente_actual': otrosi_vigente_actual,
        'fuente_condiciones': fuente_condiciones,
        'valores_iniciales_polizas': json.dumps(valores_iniciales_polizas),
        'modalidad_actual': modalidad_actual,
        'titulo': f'Nuevo Otro Sí - Contrato {contrato.num_contrato}'
    }
    return render(request, 'gestion/otrosi/form.html', context)




@admin_required
def editar_otrosi(request, otrosi_id):
    """Edita un Otro Sí existente (solo admin, cualquier estado)"""
    from gestion.forms_otrosi import OtroSiForm
    from gestion.models import OtroSi
    
    otrosi = get_object_or_404(OtroSi, id=otrosi_id)
    contrato = otrosi.contrato
    
    # Obtener el último OtroSi aprobado previo (excluyendo el actual)
    ultimo_otrosi_previo = OtroSi.objects.filter(
        contrato=contrato,
        estado='APROBADO'
    ).exclude(pk=otrosi.id).order_by('-fecha_creacion', '-version').first()
    
    # Obtener condiciones de pólizas: del último OtroSi previo si modifica pólizas, sino del contrato
    if ultimo_otrosi_previo and ultimo_otrosi_previo.modifica_polizas:
        from datetime import date
        polizas_requeridas = get_polizas_requeridas_contrato(contrato, ultimo_otrosi_previo.effective_from)
        fuente_condiciones = 'otrosi_previo'
        otrosi_vigente_actual = ultimo_otrosi_previo
    else:
        condiciones_polizas = get_condiciones_polizas_vigentes(contrato)
        polizas_requeridas = condiciones_polizas['polizas']
        fuente_condiciones = 'contrato_base'
        otrosi_vigente_actual = None
    
    if request.method == 'POST':
        continuar_desde_advertencia = request.POST.get('continuar_desde_advertencia')
        
        # Si viene desde la advertencia, restaurar datos del formulario desde la sesión
        if continuar_desde_advertencia and 'otrosi_pendiente_advertencia' in request.session:
            datos_sesion = request.session['otrosi_pendiente_advertencia']
            # Crear un nuevo QueryDict con los datos guardados
            from django.http import QueryDict
            form_data = QueryDict(mutable=True)
            form_data_dict = datos_sesion.get('form_data', {})
            for key, value in form_data_dict.items():
                if isinstance(value, list):
                    for v in value:
                        form_data.appendlist(key, v)
                else:
                    form_data[key] = value
            form_data['continuar_desde_advertencia'] = '1'
            form = OtroSiForm(form_data, instance=otrosi, contrato=contrato, contrato_id=contrato.id)
            del request.session['otrosi_pendiente_advertencia']
        else:
            form = OtroSiForm(request.POST, instance=otrosi, contrato=contrato, contrato_id=contrato.id)
        
        if form.is_valid():
            otrosi = form.save(commit=False)
            
            # Verificar si el otro sí modifica el canon y si existe un cálculo de IPC/Salario Mínimo
            if (otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado) and not continuar_desde_advertencia:
                from gestion.utils_ipc import verificar_calculo_existente_para_fecha
                from decimal import Decimal
                
                # Obtener el nuevo valor del canon del otro sí
                nuevo_valor_canon = otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado
                
                # Verificar cálculos existentes para la fecha de vigencia del otro sí
                fecha_verificacion = otrosi.effective_from
                calculo_info = verificar_calculo_existente_para_fecha(contrato, fecha_verificacion)
                
                # Si no hay cálculo para la fecha exacta, buscar por año
                if not calculo_info['existe']:
                    from datetime import date
                    año_verificacion = fecha_verificacion.year
                    # Buscar cualquier cálculo aplicado en ese año
                    from gestion.models import CalculoIPC, CalculoSalarioMinimo
                    calculo_ipc = CalculoIPC.objects.filter(
                        contrato=contrato,
                        año_aplicacion=año_verificacion,
                        estado='APLICADO'
                    ).order_by('-fecha_aplicacion').first()
                    calculo_sm = CalculoSalarioMinimo.objects.filter(
                        contrato=contrato,
                        año_aplicacion=año_verificacion,
                        estado='APLICADO'
                    ).order_by('-fecha_aplicacion').first()
                    
                    # Determinar cuál cálculo usar (el más reciente si hay ambos)
                    calculo_existente = None
                    tipo_calculo = None
                    if calculo_ipc and calculo_sm:
                        calculo_existente = calculo_ipc if calculo_ipc.fecha_aplicacion >= calculo_sm.fecha_aplicacion else calculo_sm
                        tipo_calculo = 'IPC' if calculo_existente == calculo_ipc else 'Salario Mínimo'
                    elif calculo_ipc:
                        calculo_existente = calculo_ipc
                        tipo_calculo = 'IPC'
                    elif calculo_sm:
                        calculo_existente = calculo_sm
                        tipo_calculo = 'Salario Mínimo'
                else:
                    calculo_existente = calculo_info['calculo']
                    tipo_calculo = calculo_info['tipo']
                
                # Si hay un cálculo existente y el valor es diferente, mostrar advertencia
                if calculo_existente and calculo_existente.estado == 'APLICADO':
                    valor_calculo = calculo_existente.nuevo_canon
                    diferencia = abs(valor_calculo - nuevo_valor_canon)
                    
                    if diferencia > Decimal('0.01'):  # Tolerancia de 1 centavo
                        # Guardar datos del formulario en la sesión para continuar después
                        # Convertir QueryDict a dict mutable
                        form_data_dict = {}
                        for key in request.POST.keys():
                            values = request.POST.getlist(key)
                            if len(values) == 1:
                                form_data_dict[key] = values[0]
                            else:
                                form_data_dict[key] = values
                        
                        request.session['otrosi_pendiente_advertencia'] = {
                            'form_data': form_data_dict,
                            'contrato_id': contrato.id,
                            'otrosi_id': otrosi.id,
                            'es_edicion': True,
                        }
                        
                        context = {
                            'otrosi': otrosi,
                            'contrato': contrato,
                            'calculo_existente': calculo_existente,
                            'tipo_calculo': tipo_calculo,
                            'nuevo_valor_canon': nuevo_valor_canon,
                            'diferencia': diferencia,
                            'es_edicion': True,
                            'titulo': 'Advertencia - Cálculo Existente',
                        }
                        return render(request, 'gestion/otrosi/advertencia_calculo_existente.html', context)
            
            guardar_con_auditoria(otrosi, request.user, es_nuevo=False)
            otrosi.save()
            
            # Si el Otro Sí modifica el canon, actualizar cálculos existentes inmediatamente
            # Esto asegura que la base de datos se actualice cuando se detecta el cálculo existente
            if otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado:
                from gestion.utils_ipc import actualizar_calculos_por_otrosi
                resultado_actualizacion = actualizar_calculos_por_otrosi(
                    otrosi.contrato,
                    otrosi,
                    request.user
                )
                
                if resultado_actualizacion['actualizados'] > 0:
                    detalles_str = ', '.join([
                        f"{d['tipo']} ({d['fecha'].strftime('%d/%m/%Y')})"
                        for d in resultado_actualizacion['detalles']
                    ])
                    if otrosi.estado == 'APROBADO':
                        messages.success(
                            request,
                            f'✅ Otro Sí {otrosi.numero_otrosi} actualizado exitosamente! '
                            f'Se actualizaron automáticamente {resultado_actualizacion["actualizados"]} cálculo(s) de ajuste: {detalles_str}.'
                        )
                    else:
                        messages.success(
                            request,
                            f'✅ Otro Sí {otrosi.numero_otrosi} actualizado exitosamente! '
                            f'Cuando se apruebe este Otro Sí, se actualizarán automáticamente {resultado_actualizacion["actualizados"]} cálculo(s) de ajuste: {detalles_str}.'
                        )
                else:
                    messages.success(request, f'✅ Otro Sí {otrosi.numero_otrosi} actualizado exitosamente!')
            else:
                messages.success(request, f'✅ Otro Sí {otrosi.numero_otrosi} actualizado exitosamente!')
            
            # Los valores de pólizas ya se guardan en los campos nuevo_* del OtroSi mediante el formulario
            # No necesitamos procesar condiciones adicionales
            
            return redirect('gestion:detalle_otrosi', otrosi_id=otrosi.id)
        else:
            # Agregar mensajes de error específicos
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form, prefijo_emoji='❌ ')
    else:
        form = OtroSiForm(instance=otrosi, contrato=contrato, contrato_id=contrato.id)
    
    # Preparar datos de condiciones de pólizas para el template
    condiciones_para_template = []
    for tipo, config in polizas_requeridas.items():
        condiciones_para_template.append({
            'tipo': tipo,
            'tipo_key': tipo.replace(' ', '').replace('-', '').lower(),
            'config': config,
            'fuente': fuente_condiciones,
        })
    
    # Preparar valores iniciales de pólizas para JavaScript
    valores_iniciales_polizas = {}
    if ultimo_otrosi_previo and ultimo_otrosi_previo.modifica_polizas:
        # Usar valores del último OtroSi aprobado
        otrosi_base = ultimo_otrosi_previo
    else:
        # Usar valores del contrato inicial
        otrosi_base = None
    
    # Función auxiliar para obtener valor inicial
    def obtener_valor_inicial(campo_otrosi, campo_contrato):
        if otrosi_base:
            valor = getattr(otrosi_base, campo_otrosi, None)
            if valor is not None:
                return valor
        return getattr(contrato, campo_contrato, None)
    
    # RCE
    if contrato.exige_poliza_rce or (otrosi_base and otrosi_base.nuevo_exige_poliza_rce):
        valores_iniciales_polizas['rce'] = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_rce', 'exige_poliza_rce') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_rce', 'valor_asegurado_rce') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_rce', 'meses_vigencia_rce') or '',
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_rce', 'fecha_fin_vigencia_rce') or ''),
            'valor_plo': str(obtener_valor_inicial('nuevo_valor_propietario_locatario_ocupante_rce', 'valor_propietario_locatario_ocupante_rce') or ''),
            'valor_patronal': str(obtener_valor_inicial('nuevo_valor_patronal_rce', 'valor_patronal_rce') or ''),
            'valor_gastos_medicos': str(obtener_valor_inicial('nuevo_valor_gastos_medicos_rce', 'valor_gastos_medicos_rce') or ''),
            'valor_vehiculos': str(obtener_valor_inicial('nuevo_valor_vehiculos_rce', 'valor_vehiculos_rce') or ''),
            'valor_contratistas': str(obtener_valor_inicial('nuevo_valor_contratistas_rce', 'valor_contratistas_rce') or ''),
            'valor_perjuicios': str(obtener_valor_inicial('nuevo_valor_perjuicios_extrapatrimoniales_rce', 'valor_perjuicios_extrapatrimoniales_rce') or ''),
            'valor_dano_moral': str(obtener_valor_inicial('nuevo_valor_dano_moral_rce', 'valor_dano_moral_rce') or ''),
            'valor_lucro_cesante': str(obtener_valor_inicial('nuevo_valor_lucro_cesante_rce', 'valor_lucro_cesante_rce') or ''),
        }
    
    # Cumplimiento
    if contrato.exige_poliza_cumplimiento or (otrosi_base and otrosi_base.nuevo_exige_poliza_cumplimiento):
        valores_iniciales_polizas['cumplimiento'] = {
            'exige': obtener_valor_inicial('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento') or False,
            'valor_asegurado': str(obtener_valor_inicial('nuevo_valor_asegurado_cumplimiento', 'valor_asegurado_cumplimiento') or ''),
            'meses_vigencia': obtener_valor_inicial('nuevo_meses_vigencia_cumplimiento', 'meses_vigencia_cumplimiento') or '',
            'fecha_inicio': str(obtener_valor_inicial('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento') or ''),
            'fecha_fin': str(obtener_valor_inicial('nuevo_fecha_fin_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento') or ''),
            'valor_remuneraciones': str(obtener_valor_inicial('nuevo_valor_remuneraciones_cumplimiento', 'valor_remuneraciones_cumplimiento') or ''),
            'valor_servicios_publicos': str(obtener_valor_inicial('nuevo_valor_servicios_publicos_cumplimiento', 'valor_servicios_publicos_cumplimiento') or ''),
            'valor_iva': str(obtener_valor_inicial('nuevo_valor_iva_cumplimiento', 'valor_iva_cumplimiento') or ''),
            'valor_otros': str(obtener_valor_inicial('nuevo_valor_otros_cumplimiento', 'valor_otros_cumplimiento') or ''),
        }
    
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
    
    # Obtener modalidad de pago actual (del último otro sí aprobado o del contrato)
    from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo
    otrosi_modalidad = get_ultimo_otrosi_que_modifico_campo(contrato, 'nueva_modalidad_pago')
    if otrosi_modalidad and otrosi_modalidad.nueva_modalidad_pago:
        modalidad_actual = otrosi_modalidad.nueva_modalidad_pago
    else:
        modalidad_actual = contrato.modalidad_pago or ''
    
    context = {
        'form': form,
        'otrosi': otrosi,
        'contrato': contrato,
        'condiciones_para_template': condiciones_para_template,
        'otrosi_vigente_actual': otrosi_vigente_actual,
        'fuente_condiciones': fuente_condiciones,
        'valores_iniciales_polizas': json.dumps(valores_iniciales_polizas),
        'modalidad_actual': modalidad_actual,
        'titulo': f'Editar Otro Sí - {otrosi.numero_otrosi}'
    }
    return render(request, 'gestion/otrosi/form.html', context)




@login_required_custom
def detalle_otrosi(request, otrosi_id):
    """Muestra el detalle de un Otro Sí con la vista vigente del contrato"""
    from gestion.models import OtroSi
    from gestion.utils_otrosi import tiene_otrosi_posteriores
    
    otrosi = get_object_or_404(OtroSi, id=otrosi_id)
    contrato = otrosi.contrato
    
    # Obtener vista vigente del contrato en la fecha effective_from del Otro Sí
    vista_vigente = get_vista_vigente_contrato(contrato, otrosi.effective_from)
    
    # Obtener cambios resumidos
    cambios = otrosi.get_cambios_resumen()
    
    # Verificar si hay Otros Sí posteriores
    tiene_posteriores = tiene_otrosi_posteriores(otrosi)
    
    context = {
        'otrosi': otrosi,
        'contrato': contrato,
        'vista_vigente': vista_vigente,
        'cambios': cambios,
        'tiene_posteriores': tiene_posteriores,
        'titulo': f'Detalle Otro Sí - {otrosi.numero_otrosi}'
    }
    return render(request, 'gestion/otrosi/detalle.html', context)




@admin_required
def aprobar_otrosi(request, otrosi_id):
    """Aprueba un Otro Sí (solo administradores)"""
    from gestion.models import OtroSi
    from datetime import datetime
    
    otrosi = get_object_or_404(OtroSi, id=otrosi_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'aprobar':
            if otrosi.estado == 'EN_REVISION':
                otrosi.estado = 'APROBADO'
                otrosi.aprobado_por = request.user.username
                otrosi.fecha_aprobacion = timezone.now()
                otrosi.save()
                
                # Actualizar cálculos de IPC/Salario Mínimo si el Otro Sí modifica el canon
                if otrosi.nuevo_valor_canon or otrosi.nuevo_canon_minimo_garantizado:
                    from gestion.utils_ipc import actualizar_calculos_por_otrosi
                    resultado_actualizacion = actualizar_calculos_por_otrosi(
                        otrosi.contrato,
                        otrosi,
                        request.user
                    )
                    
                    if resultado_actualizacion['actualizados'] > 0:
                        detalles_str = ', '.join([
                            f"{d['tipo']} ({d['fecha'].strftime('%d/%m/%Y')})"
                            for d in resultado_actualizacion['detalles']
                        ])
                        messages.success(
                            request,
                            f'Otro Sí {otrosi.numero_otrosi} aprobado exitosamente! '
                            f'Se actualizaron automáticamente {resultado_actualizacion["actualizados"]} cálculo(s) de ajuste: {detalles_str}.'
                        )
                    else:
                        messages.success(request, f'Otro Sí {otrosi.numero_otrosi} aprobado exitosamente!')
                else:
                    messages.success(request, f'Otro Sí {otrosi.numero_otrosi} aprobado exitosamente!')
            else:
                messages.warning(request, f'Solo se pueden aprobar Otro Sí en estado "En Revisión".')
        
        elif accion == 'rechazar':
            if otrosi.estado == 'EN_REVISION':
                otrosi.estado = 'RECHAZADO'
                otrosi.observaciones = request.POST.get('observaciones_rechazo', '')
                otrosi.save()
                
                messages.success(request, f'Otro Sí {otrosi.numero_otrosi} rechazado.')
            else:
                messages.warning(request, f'Solo se pueden rechazar Otro Sí en estado "En Revisión".')
        
        return redirect('gestion:detalle_otrosi', otrosi_id=otrosi.id)
    
    context = {
        'otrosi': otrosi,
        'contrato': otrosi.contrato,
        'titulo': f'Aprobar Otro Sí - {otrosi.numero_otrosi}'
    }
    return render(request, 'gestion/otrosi/aprobar.html', context)




@login_required_custom
def enviar_a_revision_otrosi(request, otrosi_id):
    """Envía un Otro Sí a revisión"""
    from gestion.models import OtroSi
    
    otrosi = get_object_or_404(OtroSi, id=otrosi_id)
    
    if request.method == 'POST':
        if otrosi.estado == 'BORRADOR':
            otrosi.estado = 'EN_REVISION'
            otrosi.save()
            
            messages.success(request, f'Otro Sí {otrosi.numero_otrosi} enviado a revisión exitosamente!')
        else:
            messages.warning(request, f'Solo se pueden enviar a revisión Otro Sí en estado "Borrador".')
        
        return redirect('gestion:detalle_otrosi', otrosi_id=otrosi.id)
    
    context = {
        'otrosi': otrosi,
        'contrato': otrosi.contrato,
        'titulo': f'Enviar a Revisión - {otrosi.numero_otrosi}'
    }
    return render(request, 'gestion/otrosi/enviar_revision.html', context)




@admin_required
def eliminar_otrosi(request, otrosi_id):
    """Elimina un Otro Sí (solo admin, cualquier estado)"""
    from gestion.models import OtroSi
    from gestion.utils_otrosi import tiene_otrosi_posteriores
    
    otrosi = get_object_or_404(OtroSi, id=otrosi_id)
    contrato = otrosi.contrato
    
    # Validar si hay Otros Sí posteriores
    tiene_posteriores = tiene_otrosi_posteriores(otrosi)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'confirmar':
            # Validar nuevamente antes de eliminar (por si acaso se intenta forzar)
            if tiene_otrosi_posteriores(otrosi):
                messages.error(
                    request, 
                    f'❌ No se puede eliminar el Otro Sí {otrosi.numero_otrosi} porque existen Otros Sí posteriores. '
                    'Solo se puede eliminar el último Otro Sí del contrato. Se permite editar, pero no eliminar.'
                )
                return redirect('gestion:detalle_otrosi', otrosi_id=otrosi.id)
            
            registrar_eliminacion(otrosi, request.user)
            numero = otrosi.numero_otrosi
            otrosi.delete()
            messages.success(request, f'✅ Otro Sí {numero} eliminado exitosamente!')
            return redirect('gestion:lista_otrosi', contrato_id=contrato.id)
        elif accion == 'cancelar':
            return redirect('gestion:detalle_otrosi', otrosi_id=otrosi.id)
    
    context = {
        'otrosi': otrosi,
        'contrato': contrato,
        'tiene_posteriores': tiene_posteriores,
        'titulo': f'Eliminar Otro Sí - {otrosi.numero_otrosi}'
    }
    return render(request, 'gestion/otrosi/eliminar.html', context)




