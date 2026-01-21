from django import forms
from .models import (
    TipoContrato, TipoServicio, Contrato, Tercero, Arrendatario, Local, Poliza, 
    ConfiguracionEmpresa, ConfiguracionEmail, RequerimientoPoliza, InformeVentas, CalculoFacturacionVentas, 
    IPCHistorico, CalculoIPC, TipoCondicionIPC, PeriodicidadIPC,
    SalarioMinimoHistorico, CalculoSalarioMinimo,
    obtener_tipos_condicion_ipc_choices, obtener_periodicidades_ipc_choices, MESES_CHOICES
)
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import strip_tags
from datetime import date, timedelta
from decimal import Decimal
import re
from .utils import calcular_fecha_vencimiento, validar_fecha_vencimiento_poliza
from .utils_formateo import (
    limpiar_valor_numerico, 
    limpiar_datos_post_numericos,
    aplicar_nombre_propio,
    es_campo_excluido_nombre_propio
)
from gestion.utils_otrosi import (
    obtener_valores_vigentes_facturacion_ventas,
    es_fecha_fuera_vigencia_contrato,
)


def sanitizar_texto(texto):
    """
    Sanitiza texto removiendo HTML y scripts potencialmente peligrosos.
    
    Args:
        texto: Texto a sanitizar
        
    Returns:
        Texto sanitizado sin etiquetas HTML
    """
    if not texto:
        return texto
    
    # Remover etiquetas HTML
    texto_sanitizado = strip_tags(str(texto))
    
    # Remover scripts JavaScript
    texto_sanitizado = re.sub(r'<script[^>]*>.*?</script>', '', texto_sanitizado, flags=re.DOTALL | re.IGNORECASE)
    
    # Remover eventos onclick, onerror, etc.
    texto_sanitizado = re.sub(r'on\w+\s*=', '', texto_sanitizado, flags=re.IGNORECASE)
    
    return texto_sanitizado.strip()


def validar_longitud_maxima(campo_nombre, valor, max_length, mensaje_error=None):
    """
    Valida que un campo no exceda la longitud máxima permitida.
    
    Args:
        campo_nombre: Nombre del campo
        valor: Valor a validar
        max_length: Longitud máxima permitida
        mensaje_error: Mensaje de error personalizado (opcional)
        
    Raises:
        ValidationError: Si el valor excede la longitud máxima
    """
    if valor and len(str(valor)) > max_length:
        if mensaje_error:
            raise ValidationError(mensaje_error)
        raise ValidationError(
            f'El campo "{campo_nombre}" no puede exceder {max_length} caracteres. '
            f'Longitud actual: {len(str(valor))} caracteres.'
        )


def inicializar_campos_numericos_en_cero(form_instance):
    """
    Función helper para inicializar todos los campos numéricos en 0 sin decimales.
    Se aplica cuando el formulario está en modo creación (sin datos POST y sin instancia).
    
    Respeta los valores iniciales ya configurados en los campos, no los sobrescribe.
    
    Args:
        form_instance: Instancia del formulario
    """
    # Solo aplicar si no hay datos POST y no hay instancia (modo creación)
    if form_instance.data or (hasattr(form_instance, 'instance') and form_instance.instance.pk):
        return
    
    # Detectar campos numéricos
    campos_numericos = []
    for field_name, field in form_instance.fields.items():
        # Detectar DecimalField, IntegerField
        if isinstance(field, (forms.DecimalField, forms.IntegerField)):
            campos_numericos.append(field_name)
        # Detectar campos con NumberInput widget
        elif hasattr(field, 'widget') and isinstance(field.widget, forms.NumberInput):
            campos_numericos.append(field_name)
        # Detectar campos con TextInput que tienen clase money-input o percentage-input
        elif (hasattr(field, 'widget') and isinstance(field.widget, forms.TextInput) and
              hasattr(field.widget, 'attrs') and 
              ('money-input' in field.widget.attrs.get('class', '') or 
               'percentage-input' in field.widget.attrs.get('class', ''))):
            campos_numericos.append(field_name)
    
    # Campos que NO deben inicializarse en 0 (deben quedar en None si no se modifican)
    campos_excluidos_inicializacion = [
        'nuevos_puntos_adicionales_ipc',  # Debe quedar en None si no se modifica
        'nuevo_porcentaje_ventas',  # Debe quedar en None si no se modifica
        'año',  # Debe mantenerse con el valor configurado manualmente
        'año_aplicacion',  # Debe mantenerse con el valor configurado manualmente
    ]
    
    # Inicializar campos numéricos en '0' si están vacíos y no tienen valor inicial configurado
    for campo in campos_numericos:
        if campo in form_instance.fields:
            # Excluir campos que no deben inicializarse en 0
            if campo in campos_excluidos_inicializacion:
                continue
                
            field = form_instance.fields[campo]
            
            # Verificar si el campo ya tiene un valor inicial configurado
            valor_initial_field = getattr(field, 'initial', None)
            valor_initial_dict = form_instance.initial.get(campo)
            
            # Si el campo tiene un valor inicial configurado (y no es None, '', 0, '0', Decimal('0'))
            # no lo sobrescribimos
            tiene_valor_inicial = False
            
            # Verificar valor inicial del campo
            if valor_initial_field is not None and valor_initial_field not in [None, '', 0, '0', Decimal('0')]:
                tiene_valor_inicial = True
            
            # Verificar valor inicial en el diccionario initial
            if valor_initial_dict is not None and valor_initial_dict not in [None, '', 0, '0', Decimal('0')]:
                tiene_valor_inicial = True
            
            # Solo inicializar en '0' si no tiene valor inicial configurado
            if not tiene_valor_inicial:
                valor_actual = form_instance.initial.get(campo)
                if valor_actual in [None, '', 0, '0', Decimal('0')]:
                    form_instance.initial[campo] = '0'
                    form_instance.fields[campo].initial = '0'


class BaseModelForm(forms.ModelForm):
    """
    Clase base para todos los ModelForm que inicializa automáticamente 
    campos numéricos en 0 sin decimales en modo creación.
    
    También incluye validaciones de seguridad:
    - Sanitización de HTML en campos de texto
    - Validación de longitud máxima
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inicializar_campos_numericos_en_cero(self)
        
        # Agregar validación de longitud máxima a campos CharField y Textarea
        for field_name, field in self.fields.items():
            if isinstance(field, forms.CharField):
                # Si el campo no tiene max_length definido, usar el del modelo
                if not hasattr(field, 'max_length') or field.max_length is None:
                    if hasattr(self, 'Meta') and hasattr(self.Meta, 'model'):
                        try:
                            model_field = self.Meta.model._meta.get_field(field_name)
                            if hasattr(model_field, 'max_length') and model_field.max_length:
                                field.max_length = model_field.max_length
                        except:
                            pass
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Sanitizar campos de texto (CharField y Textarea)
        for field_name, field in self.fields.items():
            if isinstance(field, forms.CharField) and field_name in cleaned_data:
                valor = cleaned_data[field_name]
                if valor:
                    # Sanitizar HTML
                    valor_sanitizado = sanitizar_texto(valor)
                    
                    # Aplicar formato nombre propio si no es campo excluido
                    if not es_campo_excluido_nombre_propio(field_name, field):
                        valor_sanitizado = aplicar_nombre_propio(valor_sanitizado)
                    
                    cleaned_data[field_name] = valor_sanitizado
                    
                    # Validar longitud máxima
                    max_length = getattr(field, 'max_length', None)
                    if max_length and max_length > 0:
                        try:
                            validar_longitud_maxima(
                                field.label or field_name,
                                valor_sanitizado,
                                max_length
                            )
                        except ValidationError as e:
                            self.add_error(field_name, e)
        
        return cleaned_data


class BaseForm(forms.Form):
    """
    Clase base para todos los Form que inicializa automáticamente 
    campos numéricos en 0 sin decimales en modo creación.
    
    También incluye validaciones de seguridad:
    - Sanitización de HTML en campos de texto
    - Validación de longitud máxima
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inicializar_campos_numericos_en_cero(self)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Sanitizar campos de texto (CharField y Textarea)
        for field_name, field in self.fields.items():
            if isinstance(field, forms.CharField) and field_name in cleaned_data:
                valor = cleaned_data[field_name]
                if valor:
                    # Sanitizar HTML
                    valor_sanitizado = sanitizar_texto(valor)
                    
                    # Aplicar formato nombre propio si no es campo excluido
                    if not es_campo_excluido_nombre_propio(field_name, field):
                        valor_sanitizado = aplicar_nombre_propio(valor_sanitizado)
                    
                    cleaned_data[field_name] = valor_sanitizado
                    
                    # Validar longitud máxima
                    max_length = getattr(field, 'max_length', None)
                    if max_length and max_length > 0:
                        try:
                            validar_longitud_maxima(
                                field.label or field_name,
                                valor_sanitizado,
                                max_length
                            )
                        except ValidationError as e:
                            self.add_error(field_name, e)
        
        return cleaned_data

class ContratoForm(BaseModelForm):
    seguimiento_general = forms.CharField(
        required=False,
        label='Seguimiento general del contrato',
        widget=forms.Textarea(attrs={'rows': 4}),
        max_length=5000,
        help_text='Máximo 5000 caracteres. El HTML será removido por seguridad.'
    )
    seguimiento_poliza_rce = forms.CharField(
        required=False,
        label='Seguimiento póliza RCE',
        widget=forms.Textarea(attrs={'rows': 3}),
        max_length=2000,
        help_text='Máximo 2000 caracteres. El HTML será removido por seguridad.'
    )
    seguimiento_poliza_cumplimiento = forms.CharField(
        required=False,
        label='Seguimiento póliza de Cumplimiento',
        widget=forms.Textarea(attrs={'rows': 3}),
        max_length=2000,
        help_text='Máximo 2000 caracteres. El HTML será removido por seguridad.'
    )
    seguimiento_poliza_arrendamiento = forms.CharField(
        required=False,
        label='Seguimiento póliza de Arrendamiento',
        widget=forms.Textarea(attrs={'rows': 3}),
        max_length=2000,
        help_text='Máximo 2000 caracteres. El HTML será removido por seguridad.'
    )
    seguimiento_poliza_todo_riesgo = forms.CharField(
        required=False,
        label='Seguimiento póliza Todo Riesgo para Equipos',
        widget=forms.Textarea(attrs={'rows': 3}),
        max_length=2000,
        help_text='Máximo 2000 caracteres. El HTML será removido por seguridad.'
    )
    seguimiento_poliza_otra = forms.CharField(
        required=False,
        label='Seguimiento otras pólizas',
        widget=forms.Textarea(attrs={'rows': 3}),
        max_length=2000,
        help_text='Máximo 2000 caracteres. El HTML será removido por seguridad.'
    )

    class Meta:
        model = Contrato
        fields = '__all__'
        widgets = {
            'fecha_firma': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicial_contrato': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_final_inicial': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_final_actualizada': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio_periodo_gracia': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin_periodo_gracia': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio_vigencia_rce': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin_vigencia_rce': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio_vigencia_cumplimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin_vigencia_cumplimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio_vigencia_arrendamiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin_vigencia_arrendamiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio_vigencia_todo_riesgo': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin_vigencia_todo_riesgo': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inicio_vigencia_otra_1': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin_vigencia_otra_1': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_aumento_ipc': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'url_archivo': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            # Campos monetarios con formateo automático
            'canon_minimo_garantizado': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_asegurado_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_propietario_locatario_ocupante_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_patronal_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_gastos_medicos_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_vehiculos_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_contratistas_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_perjuicios_extrapatrimoniales_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_dano_moral_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_lucro_cesante_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_asegurado_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_remuneraciones_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_servicios_publicos_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_iva_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_otros_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_asegurado_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_remuneraciones_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_servicios_publicos_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_iva_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_otros_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_asegurado_todo_riesgo': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_asegurado_otra_1': forms.TextInput(attrs={'class': 'money-input'}),
            'clausula_penal_incumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'penalidad_terminacion_anticipada': forms.TextInput(attrs={'class': 'money-input'}),
            'multa_mora_no_restitucion': forms.TextInput(attrs={'class': 'money-input'}),
            # Campos de coberturas RCE para PROVEEDOR
            'rce_cobertura_danos_materiales': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_lesiones_personales': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_muerte_terceros': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_bienes_terceros': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_responsabilidad_patronal': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_responsabilidad_cruzada': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_contratistas': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_ejecucion_contrato': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_predios_vecinos': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_gastos_medicos': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_gastos_defensa': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_perjuicios_patrimoniales': forms.TextInput(attrs={'class': 'money-input'}),
            # Campos de amparos Cumplimiento para PROVEEDOR
            'cumplimiento_amparo_cumplimiento_contrato': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_buen_manejo_anticipo': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_amortizacion_anticipo': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_salarios_prestaciones': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_aportes_seguridad_social': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_calidad_servicio': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_estabilidad_obra': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_calidad_bienes': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_multas': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_clausula_penal': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_sanciones_incumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            # Campos de porcentaje con formateo automático
            'porcentaje_ventas': forms.TextInput(attrs={'class': 'percentage-input'}),
            'interes_mora_pagos': forms.TextInput(attrs={'class': 'percentage-input'}),
            'puntos_adicionales_ipc': forms.TextInput(attrs={'class': 'percentage-input', 'placeholder': 'Ej: 2.5% o 2.5'}),
            'porcentaje_salario_minimo': forms.TextInput(attrs={'class': 'percentage-input', 'placeholder': 'Ej: 5.5% o 5.5'}),
        }

    def __init__(self, *args, **kwargs):
        # Limpiar datos antes de la validación si hay datos POST
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data'].copy()
            self._limpiar_datos_post(data)
            kwargs['data'] = data
            
        super().__init__(*args, **kwargs)
        
        # Actualizar choices de IPC desde la BD
        if 'tipo_condicion_ipc' in self.fields:
            self.fields['tipo_condicion_ipc'].choices = [('', '---------')] + obtener_tipos_condicion_ipc_choices()
        if 'periodicidad_ipc' in self.fields:
            self.fields['periodicidad_ipc'].choices = [('', '---------')] + obtener_periodicidades_ipc_choices()
        
        # Configurar formato de fecha para todos los campos de fecha
        fecha_fields = [
            'fecha_firma', 'fecha_inicial_contrato', 'fecha_final_inicial', 
            'fecha_final_actualizada', 'fecha_inicio_periodo_gracia', 'fecha_fin_periodo_gracia',
            'fecha_inicio_vigencia_rce', 'fecha_fin_vigencia_rce',
            'fecha_inicio_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento',
            'fecha_inicio_vigencia_arrendamiento', 'fecha_fin_vigencia_arrendamiento',
            'fecha_inicio_vigencia_todo_riesgo', 'fecha_fin_vigencia_todo_riesgo',
            'fecha_inicio_vigencia_otra_1', 'fecha_fin_vigencia_otra_1',
            'fecha_aumento_ipc'
        ]
        
        for field_name in fecha_fields:
            if field_name in self.fields:
                self.fields[field_name].input_formats = ['%Y-%m-%d']
        
        # Ocultar campo porcentaje_salario_minimo (se obtiene automáticamente de SalarioMinimoHistorico)
        if 'porcentaje_salario_minimo' in self.fields:
            self.fields['porcentaje_salario_minimo'].widget = forms.HiddenInput()
            self.fields['porcentaje_salario_minimo'].required = False
        
        # Hacer campos opcionales para evitar errores de validación
        for field_name, field in self.fields.items():
            if field_name not in ['num_contrato', 'fecha_firma', 'fecha_inicial_contrato']:
                field.required = False

        if 'tipo_contrato' in self.fields:
            self.fields['tipo_contrato'].queryset = TipoContrato.objects.all()
        
        if 'tipo_servicio' in self.fields:
            self.fields['tipo_servicio'].queryset = TipoServicio.objects.all()
        
        # Configurar querysets iniciales para arrendatario y proveedor
        if 'arrendatario' in self.fields:
            self.fields['arrendatario'].queryset = Tercero.objects.filter(tipo='ARRENDATARIO').order_by('razon_social')
        
        if 'proveedor' in self.fields:
            self.fields['proveedor'].queryset = Tercero.objects.filter(tipo='PROVEEDOR').order_by('razon_social')
        
        # Configurar campos según tipo de contrato (cliente/proveedor)
        if 'tipo_contrato_cliente_proveedor' in self.fields:
            # Si hay datos POST, usar esos datos para determinar qué campos mostrar
            if self.data:
                tipo_contrato_val = self.data.get('tipo_contrato_cliente_proveedor', 'CLIENTE')
            elif self.instance and self.instance.pk:
                tipo_contrato_val = self.instance.tipo_contrato_cliente_proveedor or 'CLIENTE'
            else:
                tipo_contrato_val = 'CLIENTE'
            
            # Configurar campos según el tipo
            if tipo_contrato_val == 'CLIENTE':
                # Mostrar campos de cliente
                if 'tipo_contrato' in self.fields:
                    self.fields['tipo_contrato'].required = True
                if 'tipo_servicio' in self.fields:
                    self.fields['tipo_servicio'].required = False
                if 'arrendatario' in self.fields:
                    self.fields['arrendatario'].queryset = Tercero.objects.filter(tipo='ARRENDATARIO').order_by('razon_social')
                    self.fields['arrendatario'].required = True
                if 'proveedor' in self.fields:
                    self.fields['proveedor'].queryset = Tercero.objects.filter(tipo='PROVEEDOR').order_by('razon_social')
                    self.fields['proveedor'].required = False
                if 'local' in self.fields:
                    self.fields['local'].required = True
            else:  # PROVEEDOR
                # Mostrar campos de proveedor
                if 'tipo_contrato' in self.fields:
                    self.fields['tipo_contrato'].required = False
                if 'tipo_servicio' in self.fields:
                    self.fields['tipo_servicio'].required = True
                if 'arrendatario' in self.fields:
                    self.fields['arrendatario'].queryset = Tercero.objects.filter(tipo='ARRENDATARIO').order_by('razon_social')
                    self.fields['arrendatario'].required = False
                if 'proveedor' in self.fields:
                    self.fields['proveedor'].queryset = Tercero.objects.filter(tipo='PROVEEDOR').order_by('razon_social')
                    self.fields['proveedor'].required = True
                if 'local' in self.fields:
                    self.fields['local'].required = False

    def _limpiar_datos_post(self, data):
        """Limpia los datos POST antes de la validación"""
        campos_numericos = [
            'canon_minimo_garantizado', 'porcentaje_ventas', 'puntos_adicionales_ipc',
            'interes_mora_pagos', 'valor_asegurado_rce', 'valor_propietario_locatario_ocupante_rce',
            'valor_patronal_rce', 'valor_gastos_medicos_rce', 'valor_vehiculos_rce',
            'valor_contratistas_rce', 'valor_perjuicios_extrapatrimoniales_rce',
            'valor_dano_moral_rce', 'valor_lucro_cesante_rce', 'valor_asegurado_cumplimiento',
            'valor_remuneraciones_cumplimiento', 'valor_servicios_publicos_cumplimiento',
            'valor_iva_cumplimiento', 'valor_otros_cumplimiento',
            'valor_asegurado_arrendamiento', 'valor_remuneraciones_arrendamiento',
            'valor_servicios_publicos_arrendamiento', 'valor_iva_arrendamiento',
            'valor_otros_arrendamiento', 'valor_asegurado_todo_riesgo', 'valor_asegurado_otra_1',
            'clausula_penal_incumplimiento', 'penalidad_terminacion_anticipada',
            'multa_mora_no_restitucion'
        ]
        return limpiar_datos_post_numericos(data, campos_numericos)

    def limpiar_valor_numerico(self, value, campo_nombre="campo"):
        """Función universal para limpiar valores numéricos con formateo"""
        try:
            valor_limpio = limpiar_valor_numerico(value, campo_nombre)
            return valor_limpio
        except ValueError as e:
            raise ValidationError(str(e))


    def clean(self):
        cleaned_data = super().clean()
        
        # Limpiar todos los campos numéricos y de porcentaje
        campos_numericos = [
            'canon_minimo_garantizado', 'porcentaje_ventas', 'puntos_adicionales_ipc',
            'interes_mora_pagos', 'valor_asegurado_rce', 'valor_propietario_locatario_ocupante_rce',
            'valor_patronal_rce', 'valor_gastos_medicos_rce', 'valor_vehiculos_rce',
            'valor_contratistas_rce', 'valor_perjuicios_extrapatrimoniales_rce',
            'valor_dano_moral_rce', 'valor_lucro_cesante_rce', 'valor_asegurado_cumplimiento',
            'valor_remuneraciones_cumplimiento', 'valor_servicios_publicos_cumplimiento',
            'valor_iva_cumplimiento', 'valor_otros_cumplimiento',
            'valor_asegurado_arrendamiento', 'valor_remuneraciones_arrendamiento',
            'valor_servicios_publicos_arrendamiento', 'valor_iva_arrendamiento',
            'valor_otros_arrendamiento', 'valor_asegurado_todo_riesgo', 'valor_asegurado_otra_1',
            'clausula_penal_incumplimiento', 'penalidad_terminacion_anticipada',
            'multa_mora_no_restitucion'
        ]
        
        for campo in campos_numericos:
            if campo in cleaned_data and cleaned_data[campo]:
                try:
                    valor = cleaned_data[campo]
                    # Convertir a string si no lo es
                    valor_str = str(valor).strip()
                    
                    # Remover símbolo % si existe (para campos de porcentaje)
                    if valor_str.endswith('%'):
                        valor_str = valor_str[:-1].strip()
                    
                    # Si quedó vacío después de remover el %, usar None
                    if not valor_str:
                        cleaned_data[campo] = None
                    else:
                        cleaned_data[campo] = self.limpiar_valor_numerico(
                            valor_str, 
                            self.fields[campo].label
                        )
                except ValidationError as e:
                    self.add_error(campo, e)
        
        # Validar que según el tipo de contrato se completen los campos correspondientes
        tipo_contrato_val = cleaned_data.get('tipo_contrato_cliente_proveedor', 'CLIENTE')
        
        if tipo_contrato_val == 'CLIENTE':
            if not cleaned_data.get('tipo_contrato'):
                self.add_error('tipo_contrato', 'Este campo es requerido para contratos de clientes.')
            if not cleaned_data.get('arrendatario'):
                self.add_error('arrendatario', 'Este campo es requerido para contratos de clientes.')
            if not cleaned_data.get('local'):
                self.add_error('local', 'Este campo es requerido para contratos de clientes.')
            # Limpiar campos de proveedor
            cleaned_data['proveedor'] = None
            cleaned_data['tipo_servicio'] = None
        else:  # PROVEEDOR
            if not cleaned_data.get('tipo_servicio'):
                self.add_error('tipo_servicio', 'Este campo es requerido para contratos de proveedores.')
            if not cleaned_data.get('proveedor'):
                self.add_error('proveedor', 'Este campo es requerido para contratos de proveedores.')
            # Limpiar campos de cliente
            cleaned_data['tipo_contrato'] = None
            cleaned_data['arrendatario'] = None
            cleaned_data['local'] = None
        
        # Cálculo de fechas
        fecha_inicial = cleaned_data.get('fecha_inicial_contrato')
        duracion_meses = cleaned_data.get('duracion_inicial_meses')
        
        if fecha_inicial and duracion_meses:
            fecha_final_calculada = calcular_fecha_vencimiento(fecha_inicial, duracion_meses)
            cleaned_data['fecha_final_inicial'] = fecha_final_calculada
            cleaned_data['fecha_final_actualizada'] = fecha_final_calculada
        
        return cleaned_data

class TerceroForm(BaseModelForm):
    class Meta:
        model = Tercero
        exclude = ['fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por', 'eliminado_por', 'fecha_eliminacion']
        widgets = {
            'nit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT'}),
            'razon_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razón Social'}),
            'tipo': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'nombre_rep_legal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Representante Legal'}),
            'nombre_supervisor_op': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Supervisor (opcional)'}),
            'email_supervisor_op': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        nit = cleaned_data.get('nit')
        tipo = cleaned_data.get('tipo')
        
        if nit and tipo:
            # Verificar si ya existe otro tercero con el mismo NIT y tipo
            queryset = Tercero.objects.filter(nit=nit, tipo=tipo)
            
            # Si estamos editando, excluir el registro actual
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                tipo_display = dict(Tercero.TIPO_CHOICES).get(tipo, tipo)
                raise ValidationError({
                    'nit': f'Ya existe un {tipo_display.lower()} con el NIT {nit}. El mismo NIT puede existir como cliente y proveedor, pero no puede haber duplicados del mismo tipo.'
                })
        
        return cleaned_data

# Alias para compatibilidad hacia atrás
ArrendatarioForm = TerceroForm

class LocalForm(BaseModelForm):
    class Meta:
        model = Local
        exclude = ['fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por', 'eliminado_por', 'fecha_eliminacion']
        widgets = {
            'nombre_comercial_stand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Local A-101'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Primer Piso, Sector A, Corredor Norte'}),
            'total_area_m2': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 50.5', 'step': '0.01'}),
        }


class TipoContratoForm(BaseModelForm):
    class Meta:
        model = TipoContrato
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: STAND CUARTO PISO'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '')
        if nombre:
            nombre = nombre.strip().upper()

        if self.instance.pk and self.instance.contratos.exists():
            if nombre != self.instance.nombre:
                raise ValidationError('No se puede modificar el nombre porque existen contratos asociados.')

        if TipoContrato.objects.exclude(pk=self.instance.pk).filter(nombre__iexact=nombre).exists():
            raise ValidationError('Ya existe un tipo de contrato con este nombre.')

        return nombre


class TipoServicioForm(BaseModelForm):
    class Meta:
        model = TipoServicio
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Mantenimiento, Seguridad, Aseo'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '')
        if nombre:
            nombre = nombre.strip().upper()

        if self.instance.pk and self.instance.contratos.exists():
            if nombre != self.instance.nombre:
                raise ValidationError('No se puede modificar el nombre porque existen contratos asociados.')

        if TipoServicio.objects.exclude(pk=self.instance.pk).filter(nombre__iexact=nombre).exists():
            raise ValidationError('Ya existe un tipo de servicio con este nombre.')

        return nombre


DEFAULT_EMPRESA_CONFIG = {
    'nombre_empresa': 'EMPRESA DEMO S.A.S.',
    'nit_empresa': '900.000.000-0',
    'representante_legal': 'JUANA EJEMPLO GARCÍA',
    'direccion': 'Carrera 00 # 00-00, Bogotá D.C.',
    'telefono': '+57 (1) 000 0000',
    'email': 'contacto@empresademo.com',
}


class ConfiguracionEmpresaForm(BaseModelForm):
    class Meta:
        model = ConfiguracionEmpresa
        exclude = ['fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por', 'eliminado_por', 'fecha_eliminacion']
        widgets = {
            'direccion': forms.TextInput(attrs={'maxlength': 255}),
        }


class ConfiguracionEmailForm(BaseModelForm):
    """Formulario personalizado para ConfiguracionEmail con campo de contraseña"""
    password_input = forms.CharField(
        label='Contraseña',
        required=False,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ingrese contraseña',
            'class': 'vTextField'
        }),
        help_text='Ingrese nueva contraseña o deje en blanco para mantener la actual'
    )
    
    class Meta:
        model = ConfiguracionEmail
        exclude = ['email_host_password', 'fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es un nuevo registro, hacer el campo requerido
        if not self.instance.pk:
            self.fields['password_input'].required = True
            self.fields['password_input'].help_text = 'Ingrese contraseña (requerida)'
            self.fields['password_input'].widget.attrs['placeholder'] = 'Ingrese contraseña'
    
    def clean(self):
        """Validar que la contraseña esté presente al crear un nuevo registro"""
        cleaned_data = super().clean()
        
        # Si es un nuevo registro y no hay contraseña, mostrar error
        if not self.instance.pk:
            password_input = cleaned_data.get('password_input', '').strip()
            if not password_input:
                from django.core.exceptions import ValidationError
                self.add_error('password_input', 'Debe proporcionar una contraseña al crear la configuración')
        
        return cleaned_data


class RequerimientoPolizaForm(BaseModelForm):
    class Meta:
        model = RequerimientoPoliza
        fields = '__all__'
        widgets = {
            'fecha_inicio_vigencia': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin_vigencia': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio_vigencia')
        meses_vigencia = cleaned_data.get('meses_vigencia')
        
        if fecha_inicio and meses_vigencia:
            fecha_fin_calculada = calcular_fecha_vencimiento(fecha_inicio, meses_vigencia)
            cleaned_data['fecha_fin_vigencia'] = fecha_fin_calculada
        
        return cleaned_data

# Formset para requerimientos de pólizas
RequerimientoPolizaFormSet = inlineformset_factory(
    Contrato,
    RequerimientoPoliza,
    form=RequerimientoPolizaForm,
    extra=1,
    can_delete=True
)

class PolizaForm(BaseModelForm):
    class Meta:
        model = Poliza
        exclude = ['contrato', 'fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por', 'eliminado_por', 'fecha_eliminacion']  # Excluir contrato y campos de auditoría que se asignan automáticamente
        widgets = {
            'fecha_inicio_vigencia': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'valor_asegurado': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_propietario_locatario_ocupante_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'url_archivo': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'valor_patronal_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_gastos_medicos_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_vehiculos_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_contratistas_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_perjuicios_extrapatrimoniales_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_dano_moral_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_lucro_cesante_rce': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_remuneraciones_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_servicios_publicos_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_iva_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_otros_cumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_remuneraciones_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_servicios_publicos_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_iva_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            'valor_otros_arrendamiento': forms.TextInput(attrs={'class': 'money-input'}),
            # Campos RCE - Coberturas para PROVEEDOR
            'rce_cobertura_danos_materiales': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_lesiones_personales': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_muerte_terceros': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_bienes_terceros': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_responsabilidad_patronal': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_responsabilidad_cruzada': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_contratistas': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_ejecucion_contrato': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_danos_predios_vecinos': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_gastos_medicos': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_gastos_defensa': forms.TextInput(attrs={'class': 'money-input'}),
            'rce_cobertura_perjuicios_patrimoniales': forms.TextInput(attrs={'class': 'money-input'}),
            # Campos Cumplimiento - Amparos para PROVEEDOR
            'cumplimiento_amparo_cumplimiento_contrato': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_buen_manejo_anticipo': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_amortizacion_anticipo': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_salarios_prestaciones': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_aportes_seguridad_social': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_calidad_servicio': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_estabilidad_obra': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_calidad_bienes': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_multas': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_clausula_penal': forms.TextInput(attrs={'class': 'money-input'}),
            'cumplimiento_amparo_sanciones_incumplimiento': forms.TextInput(attrs={'class': 'money-input'}),
            'numero_poliza': forms.TextInput(attrs={'placeholder': 'Ej: POL-2024-001'}),
            'aseguradora': forms.TextInput(attrs={'placeholder': 'Nombre de la aseguradora'}),
            'cobertura': forms.TextInput(attrs={'placeholder': 'Ej: Responsabilidad Civil Extracontractual'}),
            'condiciones': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Especifique las condiciones generales de la póliza'}),
            'garantias': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describa las cláusulas de garantías y coberturas especiales'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraer argumentos personalizados antes de llamar al __init__ de la clase padre
        self.contrato = kwargs.pop('contrato', None)
        self.es_edicion = kwargs.pop('es_edicion', False)
        
        # Limpiar datos antes de la validación si hay datos POST
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data'].copy()
            campos_monetarios = [
                'valor_asegurado',
                'valor_asegurado_rce', 'valor_propietario_locatario_ocupante_rce', 'valor_patronal_rce',
                'valor_gastos_medicos_rce', 'valor_vehiculos_rce', 'valor_contratistas_rce',
                'valor_perjuicios_extrapatrimoniales_rce', 'valor_dano_moral_rce', 'valor_lucro_cesante_rce',
                'valor_asegurado_cumplimiento', 'valor_remuneraciones_cumplimiento', 'valor_servicios_publicos_cumplimiento',
                'valor_iva_cumplimiento', 'valor_otros_cumplimiento',
                'valor_asegurado_arrendamiento', 'valor_remuneraciones_arrendamiento', 'valor_servicios_publicos_arrendamiento',
                'valor_iva_arrendamiento', 'valor_otros_arrendamiento',
                # Campos RCE - Coberturas para PROVEEDOR
                'rce_cobertura_danos_materiales', 'rce_cobertura_lesiones_personales', 'rce_cobertura_muerte_terceros',
                'rce_cobertura_danos_bienes_terceros', 'rce_cobertura_responsabilidad_patronal', 'rce_cobertura_responsabilidad_cruzada',
                'rce_cobertura_danos_contratistas', 'rce_cobertura_danos_ejecucion_contrato', 'rce_cobertura_danos_predios_vecinos',
                'rce_cobertura_gastos_medicos', 'rce_cobertura_gastos_defensa', 'rce_cobertura_perjuicios_patrimoniales',
                # Campos Cumplimiento - Amparos para PROVEEDOR
                'cumplimiento_amparo_cumplimiento_contrato', 'cumplimiento_amparo_buen_manejo_anticipo', 'cumplimiento_amparo_amortizacion_anticipo',
                'cumplimiento_amparo_salarios_prestaciones', 'cumplimiento_amparo_aportes_seguridad_social', 'cumplimiento_amparo_calidad_servicio',
                'cumplimiento_amparo_estabilidad_obra', 'cumplimiento_amparo_calidad_bienes', 'cumplimiento_amparo_multas',
                'cumplimiento_amparo_clausula_penal', 'cumplimiento_amparo_sanciones_incumplimiento'
            ]
            for campo in campos_monetarios:
                if campo in data and data[campo]:
                    valor = data[campo]
                    if isinstance(valor, str):
                        valor = valor.replace('.', '').replace(',', '').replace('$', '').strip()
                        data[campo] = valor
            kwargs['data'] = data
        
        super().__init__(*args, **kwargs)
        
        # Configurar formato de fecha
        fecha_fields = ['fecha_inicio_vigencia', 'fecha_vencimiento']
        for field_name in fecha_fields:
            if field_name in self.fields:
                self.fields[field_name].input_formats = ['%Y-%m-%d']
        
        # Configurar opciones del campo tipo según el contrato y si es edición
        if 'tipo' in self.fields and self.contrato:
            if self.es_edicion:
                # En edición: hacer el campo de solo lectura
                self.fields['tipo'].disabled = True
                self.fields['tipo'].widget.attrs['readonly'] = 'readonly'
                self.fields['tipo'].widget.attrs['class'] = 'form-control form-control-enhanced'
            else:
                # En creación: filtrar opciones según el contrato considerando OtroSí vigentes
                tipos_disponibles = []
                polizas_existentes = Poliza.objects.filter(contrato=self.contrato).values_list('tipo', flat=True)
                
                # Obtener requisitos considerando OtroSí vigentes (incluyendo futuros)
                # Para registrar pólizas, necesitamos considerar OtroSí aprobados aunque tengan fechas futuras
                from gestion.utils_otrosi import get_polizas_requeridas_contrato
                from datetime import date
                
                # Obtener directamente las pólizas requeridas considerando OtroSí aprobados con fechas futuras
                # Esto asegura que se muestren pólizas agregadas por OtroSí aunque aún no estén vigentes
                polizas_requeridas = get_polizas_requeridas_contrato(self.contrato, date.today(), permitir_fuera_vigencia=True)
                
                # Construir estructura de requisitos para el formulario
                requisitos_contrato = {
                    'rce': {'exigida': False},
                    'cumplimiento': {'exigida': False},
                    'arrendamiento': {'exigida': False},
                    'todo_riesgo': {'exigida': False},
                    'otra': {'exigida': False, 'nombre': None}
                }
                
                # Mapear pólizas requeridas a la estructura de requisitos
                mapeo_polizas = {
                    'RCE - Responsabilidad Civil': 'rce',
                    'Cumplimiento': 'cumplimiento',
                    'Poliza de Arrendamiento': 'arrendamiento',
                    'Arrendamiento': 'todo_riesgo',
                    'Otra': 'otra'
                }
                
                for tipo_poliza, clave in mapeo_polizas.items():
                    if tipo_poliza in polizas_requeridas:
                        requisitos_contrato[clave]['exigida'] = True
                        if tipo_poliza == 'Otra':
                            pol_data = polizas_requeridas[tipo_poliza]
                            requisitos_contrato[clave]['nombre'] = pol_data.get('nombre') or self.contrato.nombre_poliza_otra_1 or 'Otra'
                
                # Mapeo de requisitos del contrato (considerando OtroSí) a tipos de póliza
                if requisitos_contrato['cumplimiento']['exigida'] and 'Cumplimiento' not in polizas_existentes:
                    tipos_disponibles.append(('Cumplimiento', 'Cumplimiento'))
                
                if requisitos_contrato['rce']['exigida'] and 'RCE - Responsabilidad Civil' not in polizas_existentes:
                    tipos_disponibles.append(('RCE - Responsabilidad Civil', 'RCE - Responsabilidad Civil'))
                
                if requisitos_contrato['arrendamiento']['exigida'] and 'Poliza de Arrendamiento' not in polizas_existentes:
                    tipos_disponibles.append(('Poliza de Arrendamiento', 'Póliza de Arrendamiento'))
                
                if requisitos_contrato['todo_riesgo']['exigida'] and 'Arrendamiento' not in polizas_existentes:
                    tipos_disponibles.append(('Arrendamiento', 'Arrendamiento'))
                
                if requisitos_contrato['otra']['exigida'] and 'Otra' not in polizas_existentes:
                    nombre_otra = requisitos_contrato['otra'].get('nombre') or self.contrato.nombre_poliza_otra_1 or 'Otra'
                    tipos_disponibles.append(('Otra', nombre_otra))
                
                # Actualizar las opciones del campo
                self.fields['tipo'].choices = [('', '----------')] + tipos_disponibles
                
                # Si no hay opciones disponibles, deshabilitar el campo
                if not tipos_disponibles:
                    self.fields['tipo'].disabled = True
                    self.fields['tipo'].help_text = 'Todas las pólizas requeridas ya han sido registradas'
                else:
                    self.fields['tipo'].help_text = 'Solo se muestran las pólizas requeridas que aún no han sido registradas'
        
        # Mostrar/ocultar campos según tipo de contrato
        if self.contrato:
            tipo_contrato = self.contrato.tipo_contrato_cliente_proveedor
            
            if tipo_contrato == 'PROVEEDOR':
                # Ocultar campos de CLIENTE para RCE
                campos_cliente_rce = [
                    'valor_propietario_locatario_ocupante_rce', 'valor_patronal_rce',
                    'valor_gastos_medicos_rce', 'valor_vehiculos_rce', 'valor_contratistas_rce',
                    'valor_perjuicios_extrapatrimoniales_rce', 'valor_dano_moral_rce', 'valor_lucro_cesante_rce'
                ]
                for campo in campos_cliente_rce:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False
                
                # Ocultar campos de CLIENTE para Cumplimiento
                campos_cliente_cumplimiento = [
                    'valor_remuneraciones_cumplimiento', 'valor_servicios_publicos_cumplimiento',
                    'valor_iva_cumplimiento', 'valor_otros_cumplimiento'
                ]
                for campo in campos_cliente_cumplimiento:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False
            
            elif tipo_contrato == 'CLIENTE':
                # Ocultar campos de PROVEEDOR para RCE
                campos_proveedor_rce = [
                    'rce_cobertura_danos_materiales', 'rce_cobertura_lesiones_personales',
                    'rce_cobertura_muerte_terceros', 'rce_cobertura_danos_bienes_terceros',
                    'rce_cobertura_responsabilidad_patronal', 'rce_cobertura_responsabilidad_cruzada',
                    'rce_cobertura_danos_contratistas', 'rce_cobertura_danos_ejecucion_contrato',
                    'rce_cobertura_danos_predios_vecinos', 'rce_cobertura_gastos_medicos',
                    'rce_cobertura_gastos_defensa', 'rce_cobertura_perjuicios_patrimoniales'
                ]
                for campo in campos_proveedor_rce:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False
                
                # Ocultar campos de PROVEEDOR para Cumplimiento
                campos_proveedor_cumplimiento = [
                    'cumplimiento_amparo_cumplimiento_contrato', 'cumplimiento_amparo_buen_manejo_anticipo',
                    'cumplimiento_amparo_amortizacion_anticipo', 'cumplimiento_amparo_salarios_prestaciones',
                    'cumplimiento_amparo_aportes_seguridad_social', 'cumplimiento_amparo_calidad_servicio',
                    'cumplimiento_amparo_estabilidad_obra', 'cumplimiento_amparo_calidad_bienes',
                    'cumplimiento_amparo_multas', 'cumplimiento_amparo_clausula_penal',
                    'cumplimiento_amparo_sanciones_incumplimiento'
                ]
                for campo in campos_proveedor_cumplimiento:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False


    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio_vigencia')
        meses_cobertura = cleaned_data.get('meses_cobertura')
        
        if fecha_inicio and meses_cobertura:
            fecha_fin_calculada = calcular_fecha_vencimiento(fecha_inicio, meses_cobertura)
            cleaned_data['fecha_fin_vigencia'] = fecha_fin_calculada
        
        return cleaned_data



class FiltroExportacionContratosForm(BaseForm):
    """Formulario para filtrar contratos en la exportación"""
    
    ESTADO_CHOICES = [
        ('', 'Todos'),
        ('vigentes', 'Solo Vigentes'),
        ('vencidos', 'Solo Vencidos'),
    ]
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        label='Estado del Contrato',
        initial='',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_contrato_cliente_proveedor = forms.ChoiceField(
        choices=[('', 'Todos')] + Contrato.TIPO_CONTRATO_CHOICES,
        required=False,
        label='Tipo de Contrato (Cliente/Proveedor)',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_contrato = forms.ModelChoiceField(
        queryset=TipoContrato.objects.all(),
        required=False,
        label='Tipo de Contrato (Cliente)',
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_inicio_desde = forms.DateField(
        required=False,
        label='Fecha Inicial Desde',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_inicio_hasta = forms.DateField(
        required=False,
        label='Fecha Inicial Hasta',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_final_desde = forms.DateField(
        required=False,
        label='Fecha Final Desde',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    fecha_final_hasta = forms.DateField(
        required=False,
        label='Fecha Final Hasta',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    arrendatario = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label='Arrendatario',
        empty_label='Todos los arrendatarios',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    local = forms.ModelChoiceField(
        queryset=Local.objects.all(),
        required=False,
        label='Local',
        empty_label='Todos los locales',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    modalidad_pago = forms.ChoiceField(
        choices=[('', 'Todas')] + Contrato.MODALIDAD_CHOICES,
        required=False,
        label='Modalidad de Pago',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    prorroga_automatica = forms.ChoiceField(
        choices=[('', 'Todos'), ('si', 'Con Prórroga'), ('no', 'Sin Prórroga')],
        required=False,
        label='Prórroga Automática',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from gestion.models import Tercero
        self.fields['arrendatario'].queryset = Tercero.objects.filter(tipo='ARRENDATARIO').order_by('razon_social')


class InformeVentasForm(BaseModelForm):
    """Formulario para crear y editar informes de ventas"""
    
    class Meta:
        model = InformeVentas
        fields = ['contrato', 'mes', 'año', 'observaciones', 'url_archivo']
        widgets = {
            'contrato': forms.Select(attrs={'class': 'form-select'}),
            'mes': forms.Select(attrs={'class': 'form-select'}),
            'año': forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2100}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'url_archivo': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo contratos que reportan ventas
        self.fields['contrato'].queryset = Contrato.objects.filter(reporta_ventas=True).order_by('num_contrato')
        # Establecer año por defecto al año actual
        if not self.instance.pk:
            self.fields['año'].initial = date.today().year
            self.fields['mes'].initial = date.today().month
    
    def clean(self):
        cleaned_data = super().clean()
        contrato = cleaned_data.get('contrato')
        mes = cleaned_data.get('mes')
        año = cleaned_data.get('año')
        
        # Validar que el contrato reporte ventas
        if contrato and not contrato.reporta_ventas:
            raise ValidationError('El contrato seleccionado no reporta ventas.')
        
        # Validar que no exista un informe duplicado para el mismo contrato, mes y año
        if contrato and mes and año:
            informe_existente = InformeVentas.objects.filter(
                contrato=contrato,
                mes=mes,
                año=año
            )
            if self.instance.pk:
                informe_existente = informe_existente.exclude(pk=self.instance.pk)
            
            if informe_existente.exists():
                informe = informe_existente.first()
                estado_display = informe.get_estado_display()
                mensaje = (
                    f'Ya existe un informe de ventas para este contrato en {self.get_mes_display(mes)}/{año}. '
                    f'Estado: {estado_display}. '
                    f'ID del informe: {informe.id}. '
                    f'Puede editarlo desde la lista de informes.'
                )
                raise ValidationError(mensaje)
        
        if contrato and mes and año:
            mes_int = int(mes)
            año_int = int(año)
            from calendar import monthrange
            fecha_corte = date(año_int, mes_int, monthrange(año_int, mes_int)[1])
            if es_fecha_fuera_vigencia_contrato(contrato, fecha_corte):
                raise ValidationError('El contrato no estaba vigente en el periodo seleccionado.')

            valores_vigentes = obtener_valores_vigentes_facturacion_ventas(contrato, mes_int, año_int)
            if not valores_vigentes:
                raise ValidationError(
                    'El contrato no tiene modalidad Variable Puro o Híbrido con porcentaje de ventas vigente para este periodo.'
                )
        
        return cleaned_data
    
    @staticmethod
    def get_mes_display(mes):
        """Retorna el nombre del mes"""
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return meses[mes] if 1 <= mes <= 12 else f'Mes {mes}'


class FiltroContratosVentasForm(BaseForm):
    """Formulario para filtrar contratos que reportan ventas"""
    
    ESTADO_VIGENCIA_CHOICES = [
        ('vigentes', 'Contratos vigentes'),
        ('todos', 'Todos los contratos'),
        ('vencidos', 'Contratos vencidos'),
    ]
    
    tipo_contrato_cliente_proveedor = forms.ChoiceField(
        choices=[('', 'Todos')] + Contrato.TIPO_CONTRATO_CHOICES,
        required=False,
        label='Tipo de Contrato (Cliente/Proveedor)',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_contrato = forms.ModelChoiceField(
        queryset=None,  # Se establecerá en __init__
        required=False,
        label='Tipo de Contrato (Cliente)',
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    mes = forms.ChoiceField(
        choices=[(i, ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][i-1]) for i in range(1, 13)],
        required=True,
        label='Mes a evaluar',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    año = forms.IntegerField(
        required=False,
        label='Año a evaluar',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2100})
    )
    
    buscar = forms.CharField(
        required=False,
        label='Buscar por Cliente',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre del cliente...'
        })
    )
    
    estado_vigencia = forms.ChoiceField(
        choices=ESTADO_VIGENCIA_CHOICES,
        required=False,
        label='Estado del contrato',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from gestion.models import TipoContrato
        self.fields['tipo_contrato'].queryset = TipoContrato.objects.all().order_by('nombre')
        
        # Establecer valores iniciales de mes/año si no vienen en data inicial
        ahora = timezone.now()
        if self.is_bound:
            data = self.data.copy()
            data[self.add_prefix('año')] = str(ahora.year)
            self.data = data
        self.fields['mes'].initial = str(ahora.month)
        self.fields['año'].initial = ahora.year
        self.initial['año'] = ahora.year
        self.fields['año'].widget.attrs['readonly'] = True
        self.fields['año'].widget.attrs['value'] = ahora.year
        self.fields['estado_vigencia'].initial = 'vigentes'


class FiltroListaContratosForm(BaseForm):
    """Formulario para filtrar la lista de contratos"""
    
    ESTADO_VIGENCIA_CHOICES = [
        ('vigentes', 'Contratos vigentes'),
        ('todos', 'Todos los contratos'),
        ('vencidos', 'Contratos vencidos'),
    ]
    
    TIPO_CONTRATO_CHOICES = [
        ('', 'Todos'),
        ('CLIENTE', 'Clientes'),
        ('PROVEEDOR', 'Proveedores'),
    ]
    
    tipo_contrato_cliente_proveedor = forms.ChoiceField(
        choices=TIPO_CONTRATO_CHOICES,
        required=False,
        label='Tipo de Contrato',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_contrato_cliente_proveedor'})
    )
    
    tipo_contrato = forms.ModelChoiceField(
        queryset=None,  # Se establecerá en __init__
        required=False,
        label='Tipo de Contrato (Cliente)',
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_servicio = forms.ModelChoiceField(
        queryset=None,  # Se establecerá en __init__
        required=False,
        label='Tipo de Servicio (Proveedor)',
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    buscar = forms.CharField(
        required=False,
        label='Buscar por Tercero',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre del tercero...'
        })
    )
    
    estado_vigencia = forms.ChoiceField(
        choices=ESTADO_VIGENCIA_CHOICES,
        required=False,
        label='Estado del contrato',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from gestion.models import TipoContrato, TipoServicio
        self.fields['tipo_contrato'].queryset = TipoContrato.objects.all().order_by('nombre')
        self.fields['tipo_servicio'].queryset = TipoServicio.objects.all().order_by('nombre')
        self.fields['estado_vigencia'].initial = 'vigentes'


class FiltroRenovacionesAutomaticasForm(BaseForm):
    """Formulario para filtrar renovaciones automáticas"""
    
    TIPO_CONTRATO_CHOICES = [
        ('', 'Todos'),
        ('CLIENTE', 'Clientes'),
        ('PROVEEDOR', 'Proveedores'),
    ]
    
    tipo_contrato_cliente_proveedor = forms.ChoiceField(
        choices=TIPO_CONTRATO_CHOICES,
        required=False,
        label='Tipo de Contrato',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_contrato_cliente_proveedor'})
    )
    
    tipo_contrato = forms.ModelChoiceField(
        queryset=None,  # Se establecerá en __init__
        required=False,
        label='Tipo de Contrato (Cliente)',
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_servicio = forms.ModelChoiceField(
        queryset=None,  # Se establecerá en __init__
        required=False,
        label='Tipo de Servicio (Proveedor)',
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    buscar = forms.CharField(
        required=False,
        label='Buscar por Tercero',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre del tercero...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from gestion.models import TipoContrato, TipoServicio
        self.fields['tipo_contrato'].queryset = TipoContrato.objects.all().order_by('nombre')
        self.fields['tipo_servicio'].queryset = TipoServicio.objects.all().order_by('nombre')


class FiltroInformesEntregadosForm(BaseForm):
    """Formulario para filtrar informes entregados"""
    
    tipo_contrato_cliente_proveedor = forms.ChoiceField(
        choices=[('', 'Todos')] + Contrato.TIPO_CONTRATO_CHOICES,
        required=False,
        label='Tipo de Contrato (Cliente/Proveedor)',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_contrato = forms.ModelChoiceField(
        queryset=None,  # Se establecerá en __init__
        required=False,
        label='Tipo de Contrato (Cliente)',
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    mes = forms.ChoiceField(
        choices=[('', 'Todos los meses')] + [(i, ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][i-1]) for i in range(1, 13)],
        required=False,
        label='Mes',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    año = forms.IntegerField(
        required=False,
        label='Año',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2100, 'placeholder': 'Ej: 2024'})
    )
    
    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + InformeVentas.ESTADO_CHOICES,
        required=False,
        label='Estado',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    buscar = forms.CharField(
        required=False,
        label='Buscar',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por número de contrato, tercero...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from gestion.models import TipoContrato
        self.fields['tipo_contrato'].queryset = TipoContrato.objects.all().order_by('nombre')


class FiltroExportacionAlertasForm(BaseForm):
    """Formulario simple para seleccionar el tipo de contrato al exportar alertas"""
    
    tipo_contrato_cliente_proveedor = forms.ChoiceField(
        choices=[('', 'Todos'), ('CLIENTE', 'Solo Clientes'), ('PROVEEDOR', 'Solo Proveedores')],
        required=False,
        label='Tipo de Contrato',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )


class CalculoFacturacionVentasForm(BaseForm):
    """Formulario para calcular facturación por ventas"""
    
    contrato = forms.ModelChoiceField(
        queryset=Contrato.objects.none(),
        required=True,
        label='Contrato',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo contratos que reportan ventas
        self.fields['contrato'].queryset = Contrato.objects.filter(reporta_ventas=True).order_by('num_contrato')
    
    mes = forms.ChoiceField(
        choices=[(i, ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][i-1]) for i in range(1, 13)],
        required=True,
        label='Mes',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    año = forms.IntegerField(
        required=True,
        label='Año',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 2000, 'max': 2100})
    )
    
    ventas_totales = forms.CharField(
        required=True,
        label='Ventas Totales',
        widget=forms.TextInput(attrs={
            'class': 'form-control money-input',
            'placeholder': 'Ej: 1.000.000'
        })
    )
    
    devoluciones = forms.CharField(
        required=False,
        label='Devoluciones',
        initial='0',
        widget=forms.TextInput(attrs={
            'class': 'form-control money-input',
            'placeholder': 'Ej: 50.000'
        })
    )
    
    observaciones = forms.CharField(
        required=False,
        label='Observaciones',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notas adicionales sobre el cálculo...'
        })
    )
    
    def clean_ventas_totales(self):
        """Limpia y convierte el valor de ventas totales"""
        from .utils_formateo import limpiar_valor_numerico
        valor = self.cleaned_data.get('ventas_totales')
        if valor:
            valor_limpio = limpiar_valor_numerico(valor)
            if valor_limpio <= 0:
                raise ValidationError('Las ventas totales deben ser mayores a cero.')
            return valor_limpio
        return None
    
    def clean_devoluciones(self):
        """Limpia y convierte el valor de devoluciones"""
        from .utils_formateo import limpiar_valor_numerico
        valor = self.cleaned_data.get('devoluciones')
        if valor:
            valor_limpio = limpiar_valor_numerico(valor)
            if valor_limpio < 0:
                raise ValidationError('Las devoluciones no pueden ser negativas.')
            return valor_limpio
        return Decimal('0')
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        contrato = cleaned_data.get('contrato')
        mes = cleaned_data.get('mes')
        año = cleaned_data.get('año')
        ventas_totales = cleaned_data.get('ventas_totales')
        devoluciones = cleaned_data.get('devoluciones') or Decimal('0')
        
        if contrato and mes and año and ventas_totales:
            # Validar que el contrato reporte ventas
            if not contrato.reporta_ventas:
                raise ValidationError('El contrato seleccionado no reporta ventas.')
            
            # Validar que exista un informe de ventas para ese mes
            informe_existente = InformeVentas.objects.filter(
                contrato=contrato,
                mes=int(mes),
                año=año
            ).first()
            
            if not informe_existente:
                raise ValidationError(
                    f'No existe un informe de ventas para este contrato en {self.get_mes_display(int(mes))}/{año}. '
                    f'Por favor, cree el informe primero.'
                )
            
            # Validar que las devoluciones no sean mayores que las ventas totales
            if devoluciones > ventas_totales:
                raise ValidationError('Las devoluciones no pueden ser mayores que las ventas totales.')
        
        return cleaned_data
    
    @staticmethod
    def get_mes_display(mes):
        """Retorna el nombre del mes"""
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        return meses[int(mes)] if 1 <= int(mes) <= 12 else f'Mes {mes}'


class IPCHistoricoForm(BaseModelForm):
    """Formulario para gestionar el histórico de valores del IPC"""
    
    class Meta:
        model = IPCHistorico
        fields = ['año', 'valor_ipc', 'fecha_certificacion', 'observaciones']
        widgets = {
            'año': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': '2100'}),
            'valor_ipc': forms.TextInput(attrs={
                'class': 'form-control percentage-input',
                'placeholder': 'Ej: 5.2 o 5,2 para 5.2%',
                'type': 'text',
                'inputmode': 'decimal'
            }),
            'fecha_certificacion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'año': 'Año',
            'valor_ipc': 'Valor IPC (%)',
            'fecha_certificacion': 'Fecha de Certificación',
            'observaciones': 'Observaciones',
        }
        help_texts = {
            'valor_ipc': 'Ingrese el valor del IPC en porcentaje (ej: 5.2 para 5.2%)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'fecha_certificacion' in self.fields:
            self.fields['fecha_certificacion'].input_formats = ['%Y-%m-%d']
        
        # Limpiar datos POST si hay (esto se hace antes de la validación)
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data'].copy()
            if 'valor_ipc' in data and data['valor_ipc']:
                try:
                    # Convertir a string y limpiar
                    valor_str = str(data['valor_ipc']).strip()
                    # Remover símbolo % si existe
                    if valor_str.endswith('%'):
                        valor_str = valor_str[:-1].strip()
                    # Limpiar el valor numérico
                    if valor_str:
                        data['valor_ipc'] = limpiar_valor_numerico(valor_str, 'Valor IPC')
                    else:
                        data['valor_ipc'] = ''
                except (ValueError, TypeError):
                    # Si hay error, dejar que el clean_valor_ipc lo maneje
                    pass
            kwargs['data'] = data

    def clean_valor_ipc(self):
        """Limpia y valida el valor del IPC"""
        valor = self.cleaned_data.get('valor_ipc')
        if not valor:
            # Si el campo está vacío y es requerido, Django ya lo validará
            return valor
        
        try:
            # Convertir a string si no lo es
            valor_str = str(valor).strip()
            
            # Remover símbolo % si existe (por si no se limpió antes)
            if valor_str.endswith('%'):
                valor_str = valor_str[:-1].strip()
            
            # Si quedó vacío después de remover el %, es inválido
            if not valor_str:
                raise ValidationError('Ingrese un valor válido para el IPC')
            
            # Limpiar el valor numérico (retorna float)
            valor_limpio = limpiar_valor_numerico(valor_str, 'Valor IPC')
            
            # Si después de limpiar es None, el valor original era inválido
            if valor_limpio is None:
                raise ValidationError('Ingrese un número válido para el IPC')
            
            if valor_limpio < 0:
                raise ValidationError('El valor del IPC debe ser positivo')
            
            # Convertir a Decimal y redondear a máximo 2 decimales
            from decimal import ROUND_HALF_UP
            valor_decimal = Decimal(str(valor_limpio))
            valor_decimal = valor_decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            return valor_decimal
        except ValueError as e:
            raise ValidationError(str(e))

    def clean_año(self):
        """Valida que el año no esté duplicado"""
        año = self.cleaned_data.get('año')
        if año:
            # Verificar si ya existe otro registro con el mismo año (excluyendo el actual)
            qs = IPCHistorico.objects.filter(año=año)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f'Ya existe un registro de IPC para el año {año}')
        return año


class CalculoIPCForm(BaseForm):
    """Formulario para calcular el ajuste de canon por IPC"""
    
    contrato = forms.ModelChoiceField(
        queryset=Contrato.objects.filter(
            vigente=True
        ).filter(
            tipo_condicion_ipc__in=['IPC', 'SALARIO_MINIMO']
        ),
        label='Contrato',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Seleccione el contrato para calcular el ajuste'
    )
    fecha_aplicacion = forms.DateField(
        label='Fecha de Aplicación',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text='Fecha exacta en que se aplica el ajuste por IPC',
        required=True
    )
    ipc_historico = forms.ModelChoiceField(
        queryset=IPCHistorico.objects.all().order_by('-año'),
        label='IPC Histórico',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Seleccione el valor del IPC certificado por el DANE'
    )
    canon_anterior = forms.DecimalField(
        label='Canon Anterior',
        max_digits=20,
        decimal_places=2,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control money-input',
            'readonly': False,
            'placeholder': 'Se calculará automáticamente o ingrese manualmente'
        }),
        help_text='Canon base sobre el cual se calcula el ajuste. Se obtiene automáticamente si está disponible, de lo contrario ingréselo manualmente.'
    )
    canon_anterior_manual = forms.BooleanField(
        required=False,
        label='Ingresar Canon Anterior Manualmente',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Marque esta opción si desea ingresar el canon anterior manualmente'
    )
    observaciones = forms.CharField(
        required=False,
        label='Observaciones',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text='Notas adicionales sobre este cálculo'
    )

    def __init__(self, *args, **kwargs):
        contrato_initial = kwargs.pop('contrato_initial', None)
        fecha_aplicacion_initial = kwargs.pop('fecha_aplicacion_initial', None)
        año_initial = kwargs.pop('año_initial', None)
        user = kwargs.pop('user', None)
        
        # Limpiar datos POST antes de la validación si hay datos
        # Puede venir como primer argumento posicional (args[0]) o como kwargs['data']
        if args and hasattr(args[0], 'get'):
            # Es un QueryDict (request.POST)
            data = args[0].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior'])
            args = (data,) + args[1:]
        elif 'data' in kwargs and kwargs.get('data'):
            # Viene en kwargs
            data = kwargs['data'].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior'])
            kwargs['data'] = data
        
        super().__init__(*args, **kwargs)
        
        # Guardar usuario para validación posterior
        self.user = user
        
        # Restringir campo canon_anterior_manual solo a administradores
        if user and not user.is_staff:
            self.fields['canon_anterior_manual'].widget.attrs['disabled'] = True
            self.fields['canon_anterior_manual'].widget.attrs['readonly'] = True
            self.fields['canon_anterior_manual'].help_text = 'Solo los administradores pueden ingresar el canon anterior manualmente.'
        
        if contrato_initial:
            try:
                contrato_obj = Contrato.objects.get(id=contrato_initial)
                # Actualizar queryset para incluir el contrato seleccionado
                self.fields['contrato'].queryset = Contrato.objects.filter(
                    vigente=True,
                    tipo_condicion_ipc__in=['IPC', 'SALARIO_MINIMO']
                ) | Contrato.objects.filter(id=contrato_initial)
                # Inicializar con el objeto del contrato
                self.fields['contrato'].initial = contrato_obj
                self.initial['contrato'] = contrato_obj
                
                # Detectar tipo de contrato y cargar histórico correspondiente
                if contrato_obj.tipo_condicion_ipc == 'SALARIO_MINIMO':
                    # Si es Salario Mínimo, ocultar campo IPC y mostrar mensaje
                    self.fields['ipc_historico'].widget = forms.HiddenInput()
                    self.fields['ipc_historico'].required = False
                elif contrato_obj.tipo_condicion_ipc == 'IPC':
                    # Si es IPC, cargar IPC histórico según año
                    if fecha_aplicacion_initial:
                        año_requerido = fecha_aplicacion_initial.year - 1
                    elif año_initial:
                        año_requerido = int(año_initial) - 1
                    else:
                        año_actual = timezone.now().year
                        año_requerido = año_actual - 1
                    
                    queryset_ipc = IPCHistorico.objects.filter(año=año_requerido).order_by('-año')
                    if queryset_ipc.exists():
                        self.fields['ipc_historico'].queryset = queryset_ipc
                        if not self.initial.get('ipc_historico'):
                            self.initial['ipc_historico'] = queryset_ipc.first().id
                    else:
                        self.fields['ipc_historico'].queryset = IPCHistorico.objects.all().order_by('-año')
            except Contrato.DoesNotExist:
                pass
        
        if fecha_aplicacion_initial:
            self.fields['fecha_aplicacion'].initial = fecha_aplicacion_initial
        elif año_initial:
            # Si solo viene el año, usar fecha de aumento del contrato si está disponible
            if contrato_initial:
                try:
                    contrato_obj = Contrato.objects.get(id=contrato_initial)
                    if contrato_obj.fecha_aumento_ipc:
                        fecha_aplicacion = date(
                            int(año_initial),
                            contrato_obj.fecha_aumento_ipc.month,
                            contrato_obj.fecha_aumento_ipc.day
                        )
                        self.fields['fecha_aplicacion'].initial = fecha_aplicacion
                except Contrato.DoesNotExist:
                    pass
        
        # Actualizar queryset de IPC histórico si no se hizo antes
        if not contrato_initial or (contrato_initial and not hasattr(self, '_ipc_queryset_set')):
            if fecha_aplicacion_initial:
                año_requerido = fecha_aplicacion_initial.year - 1
                queryset_ipc = IPCHistorico.objects.filter(año=año_requerido).order_by('-año')
            elif año_initial:
                año_requerido = int(año_initial) - 1
                queryset_ipc = IPCHistorico.objects.filter(año=año_requerido).order_by('-año')
            else:
                año_actual = timezone.now().year
                queryset_ipc = IPCHistorico.objects.filter(año=año_actual - 1).order_by('-año')
            if queryset_ipc.exists():
                self.fields['ipc_historico'].queryset = queryset_ipc
            else:
                self.fields['ipc_historico'].queryset = IPCHistorico.objects.all().order_by('-año')

    def clean_canon_anterior(self):
        """Limpia y valida el canon anterior"""
        canon = self.cleaned_data.get('canon_anterior')
        if canon:
            try:
                # Si ya es un Decimal o número, convertirlo a string para limpiar
                if isinstance(canon, (Decimal, int, float)):
                    canon_str = str(canon)
                else:
                    canon_str = str(canon)
                
                canon_limpio = limpiar_valor_numerico(canon_str, 'Canon Anterior')
                if canon_limpio is None:
                    return None
                if canon_limpio <= 0:
                    raise ValidationError('El canon anterior debe ser mayor a cero')
                return Decimal(str(canon_limpio))
            except ValueError as e:
                raise ValidationError(str(e))
        return canon

    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        contrato = cleaned_data.get('contrato')
        fecha_aplicacion = cleaned_data.get('fecha_aplicacion')
        ipc_historico = cleaned_data.get('ipc_historico')
        canon_anterior_manual = cleaned_data.get('canon_anterior_manual', False)
        canon_anterior = cleaned_data.get('canon_anterior')
        
        # Validar que solo administradores puedan usar canon_anterior_manual
        # Si el campo está deshabilitado, verificar si alguien intentó enviarlo manualmente
        user = getattr(self, 'user', None)
        if user and not user.is_staff:
            # Si el usuario no es staff, forzar canon_anterior_manual a False
            if canon_anterior_manual:
                raise ValidationError('Solo los administradores pueden ingresar el canon anterior manualmente.')
            cleaned_data['canon_anterior_manual'] = False
            # También verificar en los datos raw si alguien intentó manipular el formulario
            if hasattr(self, 'data') and self.data.get('canon_anterior_manual'):
                raise ValidationError('No tiene permisos para ingresar el canon anterior manualmente.')
        
        if contrato and fecha_aplicacion:
            # Validar que no exista ya un cálculo para este contrato y fecha
            # Nota: CalculoIPCForm es un Form, no ModelForm, por lo que no tiene instance
            calculo_existente = CalculoIPC.objects.filter(
                contrato=contrato,
                fecha_aplicacion=fecha_aplicacion
            )
            
            if calculo_existente.exists():
                raise ValidationError(
                    f'Ya existe un cálculo de IPC para el contrato {contrato.num_contrato} '
                    f'en la fecha {fecha_aplicacion.strftime("%d/%m/%Y")}'
                )
            
            # Validar que el IPC histórico corresponda al año anterior al año de aplicación
            # Lógica: en el año X se aplica el IPC del año X-1
            año_aplicacion_calc = fecha_aplicacion.year
            if ipc_historico and ipc_historico.año != (año_aplicacion_calc - 1):
                raise ValidationError(
                    f'El IPC histórico seleccionado ({ipc_historico.año}) no corresponde '
                    f'al año de aplicación {año_aplicacion_calc}. Debe ser el IPC del año {año_aplicacion_calc - 1} '
                    f'(año anterior al de aplicación).'
                )
            
            # Validar que la fecha de aplicación coincida con la fecha proyectada (±1 día)
            from gestion.utils_ipc import calcular_proxima_fecha_aumento
            from gestion.utils_otrosi import get_ultimo_otrosi_que_modifico_campo_hasta_fecha
            
            fecha_referencia = date.today()
            fecha_proyectada = calcular_proxima_fecha_aumento(contrato, fecha_referencia)
            
            if fecha_proyectada:
                diferencia_dias = abs((fecha_aplicacion - fecha_proyectada).days)
                if diferencia_dias > 1:
                    fecha_proyectada_str = fecha_proyectada.strftime("%d/%m/%Y")
                    fecha_aplicacion_str = fecha_aplicacion.strftime("%d/%m/%Y")
                    self.add_error(
                        'fecha_aplicacion',
                        f'La fecha de aplicación ({fecha_aplicacion_str}) no coincide con la fecha proyectada '
                        f'({fecha_proyectada_str}). Solo se permite un margen de ±1 día. '
                        f'Si necesita ajustar en una fecha diferente, debe modificar la fecha de aumento en el contrato u otro sí.'
                    )
            
            # Si no es manual, obtener el canon automáticamente
            if not canon_anterior_manual and not canon_anterior:
                from gestion.utils_ipc import obtener_canon_base_para_ipc
                canon_info = obtener_canon_base_para_ipc(contrato, fecha_aplicacion)
                if canon_info['canon']:
                    cleaned_data['canon_anterior'] = canon_info['canon']
                else:
                    # No lanzar error, permitir que el usuario lo ingrese manualmente
                    # El error se mostrará en la vista
                    pass
        
        return cleaned_data


class EditarCalculoIPCForm(BaseModelForm):
    """Formulario para editar un cálculo de IPC existente"""
    
    class Meta:
        model = CalculoIPC
        fields = ['ipc_historico', 'canon_anterior', 'puntos_adicionales', 'observaciones', 'estado']
        widgets = {
            'ipc_historico': forms.Select(attrs={'class': 'form-control'}),
            'canon_anterior': forms.TextInput(attrs={
                'class': 'form-control money-input',
                'placeholder': 'Ingrese el canon anterior'
            }),
            'puntos_adicionales': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'ipc_historico': 'IPC Histórico',
            'canon_anterior': 'Canon Anterior',
            'puntos_adicionales': 'Puntos Adicionales (%)',
            'observaciones': 'Observaciones',
            'estado': 'Estado',
        }
        help_texts = {
            'ipc_historico': 'Valor del IPC certificado por el DANE',
            'canon_anterior': 'Canon base sobre el cual se calcula el ajuste',
            'puntos_adicionales': 'Puntos adicionales pactados en el contrato',
            'observaciones': 'Notas adicionales sobre este cálculo',
            'estado': 'Estado del cálculo',
        }
    
    def __init__(self, *args, **kwargs):
        # Limpiar datos POST antes de la validación si hay datos
        # Puede venir como primer argumento posicional (args[0]) o como kwargs['data']
        if args and hasattr(args[0], 'get'):
            # Es un QueryDict (request.POST)
            data = args[0].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior'])
            args = (data,) + args[1:]
        elif 'data' in kwargs and kwargs.get('data'):
            # Viene en kwargs
            data = kwargs['data'].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior'])
            kwargs['data'] = data
        
        super().__init__(*args, **kwargs)
        
        # Actualizar queryset de IPC histórico
        self.fields['ipc_historico'].queryset = IPCHistorico.objects.all().order_by('-año')
        
        # Si hay instancia, limitar el queryset de IPC histórico al año anterior al año de aplicación
        # Lógica: en el año X se aplica el IPC del año X-1
        if self.instance and self.instance.pk:
            año_aplicacion = self.instance.año_aplicacion
            año_ipc_requerido = año_aplicacion - 1
            self.fields['ipc_historico'].queryset = IPCHistorico.objects.filter(año=año_ipc_requerido).order_by('-año')
    
    def clean_canon_anterior(self):
        """Limpia y valida el canon anterior"""
        canon = self.cleaned_data.get('canon_anterior')
        if canon:
            try:
                # Si ya es un Decimal o número, convertirlo a string para limpiar
                if isinstance(canon, (Decimal, int, float)):
                    canon_str = str(canon)
                else:
                    canon_str = str(canon)
                
                canon_limpio = limpiar_valor_numerico(canon_str, 'Canon Anterior')
                if canon_limpio is None:
                    return None
                if canon_limpio <= 0:
                    raise ValidationError('El canon anterior debe ser mayor a cero')
                return Decimal(str(canon_limpio))
            except ValueError as e:
                raise ValidationError(str(e))
        return canon
    
    def clean(self):
        """Validaciones adicionales y recálculo automático"""
        cleaned_data = super().clean()
        ipc_historico = cleaned_data.get('ipc_historico')
        canon_anterior = cleaned_data.get('canon_anterior')
        puntos_adicionales = cleaned_data.get('puntos_adicionales', Decimal('0'))
        
        # Validar que el IPC histórico corresponda al año de aplicación
        if self.instance and self.instance.pk:
            año_aplicacion = self.instance.año_aplicacion
            # Validar que el IPC histórico corresponda al año anterior al año de aplicación
            # Lógica: en el año X se aplica el IPC del año X-1
            if ipc_historico and ipc_historico.año != (año_aplicacion - 1):
                    raise ValidationError(
                    f'El IPC histórico seleccionado ({ipc_historico.año}) no corresponde '
                    f'al año de aplicación {año_aplicacion}. Debe ser el IPC del año {año_aplicacion - 1} '
                    f'(año anterior al de aplicación).'
                )
        
        # Recalcular valores si se modificaron campos relevantes
        if canon_anterior and ipc_historico:
            from gestion.utils_ipc import calcular_ajuste_ipc
            try:
                resultado = calcular_ajuste_ipc(
                    canon_anterior,
                    ipc_historico.valor_ipc,
                    puntos_adicionales
                )
                # Guardar valores calculados en cleaned_data para usar en la vista
                cleaned_data['_porcentaje_total'] = resultado['porcentaje_total']
                cleaned_data['_valor_incremento'] = resultado['valor_incremento']
                cleaned_data['_nuevo_canon'] = resultado['nuevo_canon']
            except ValueError as e:
                raise ValidationError(f'Error al calcular el ajuste: {str(e)}')
        
        return cleaned_data


class TipoCondicionIPCForm(BaseModelForm):
    """Formulario para gestionar tipos de condición IPC"""
    
    class Meta:
        model = TipoCondicionIPC
        fields = ['codigo', 'nombre', 'descripcion', 'activo', 'orden']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
        labels = {
            'codigo': 'Código',
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'activo': 'Activo',
            'orden': 'Orden',
        }
        help_texts = {
            'codigo': 'Código único del tipo de condición (ej: IPC, SALARIO_MINIMO)',
            'nombre': 'Nombre descriptivo del tipo de condición',
            'descripcion': 'Descripción detallada del tipo de condición',
            'activo': 'Indica si este tipo está disponible para usar',
            'orden': 'Orden de visualización (menor número aparece primero)',
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        if codigo:
            codigo = codigo.upper().strip()
            qs = TipoCondicionIPC.objects.filter(codigo=codigo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f'Ya existe un tipo de condición IPC con el código "{codigo}"')
        return codigo


class PeriodicidadIPCForm(BaseModelForm):
    """Formulario para gestionar periodicidades IPC"""
    
    class Meta:
        model = PeriodicidadIPC
        fields = ['codigo', 'nombre', 'descripcion', 'activo', 'orden']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
        labels = {
            'codigo': 'Código',
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'activo': 'Activo',
            'orden': 'Orden',
        }
        help_texts = {
            'codigo': 'Código único de la periodicidad (ej: ANUAL, FECHA_ESPECIFICA)',
            'nombre': 'Nombre descriptivo de la periodicidad',
            'descripcion': 'Descripción detallada de la periodicidad',
            'activo': 'Indica si esta periodicidad está disponible para usar',
            'orden': 'Orden de visualización (menor número aparece primero)',
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        if codigo:
            codigo = codigo.upper().strip()
            qs = PeriodicidadIPC.objects.filter(codigo=codigo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f'Ya existe una periodicidad IPC con el código "{codigo}"')
        return codigo


class SalarioMinimoHistoricoForm(BaseModelForm):
    """Formulario para gestionar el histórico de valores del Salario Mínimo"""
    
    class Meta:
        model = SalarioMinimoHistorico
        fields = ['año', 'valor_salario_minimo', 'fecha_decreto', 'observaciones']
        widgets = {
            'año': forms.NumberInput(attrs={'class': 'form-control', 'min': '1900', 'max': '2100'}),
            'valor_salario_minimo': forms.TextInput(attrs={
                'class': 'form-control money-input',
                'placeholder': 'Ej: 1.300.000 o 1300000',
                'type': 'text',
                'inputmode': 'decimal'
            }),
            'fecha_decreto': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'año': 'Año',
            'valor_salario_minimo': 'Valor Salario Mínimo ($)',
            'fecha_decreto': 'Fecha de Decreto',
            'observaciones': 'Observaciones',
        }
        help_texts = {
            'valor_salario_minimo': 'Ingrese el valor del Salario Mínimo Legal Vigente en pesos colombianos',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'fecha_decreto' in self.fields:
            self.fields['fecha_decreto'].input_formats = ['%Y-%m-%d']
        
        # Limpiar datos POST si hay (esto se hace antes de la validación)
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data'].copy()
            if 'valor_salario_minimo' in data and data['valor_salario_minimo']:
                try:
                    valor_str = str(data['valor_salario_minimo']).strip()
                    if valor_str:
                        data['valor_salario_minimo'] = limpiar_valor_numerico(valor_str, 'Valor Salario Mínimo')
                    else:
                        data['valor_salario_minimo'] = ''
                except (ValueError, TypeError):
                    pass
            kwargs['data'] = data

    def clean_valor_salario_minimo(self):
        """Limpia y valida el valor del Salario Mínimo"""
        valor = self.cleaned_data.get('valor_salario_minimo')
        if not valor:
            return valor
        
        try:
            valor_str = str(valor).strip()
            valor_limpio = limpiar_valor_numerico(valor_str, 'Valor Salario Mínimo')
            
            if valor_limpio is None:
                raise ValidationError('Ingrese un número válido para el Salario Mínimo')
            
            if valor_limpio < 0:
                raise ValidationError('El valor del Salario Mínimo debe ser positivo')
            
            return valor_limpio
        except ValueError as e:
            raise ValidationError(str(e))

    def clean_año(self):
        """Valida que el año no esté duplicado"""
        año = self.cleaned_data.get('año')
        if año:
            qs = SalarioMinimoHistorico.objects.filter(año=año)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(f'Ya existe un registro de Salario Mínimo para el año {año}')
        return año


class CalculoSalarioMinimoForm(BaseForm):
    """Formulario para calcular el ajuste de canon por Salario Mínimo"""
    
    contrato = forms.ModelChoiceField(
        queryset=Contrato.objects.filter(tipo_condicion_ipc='SALARIO_MINIMO', vigente=True),
        label='Contrato',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Seleccione el contrato para calcular el ajuste por Salario Mínimo'
    )
    fecha_aplicacion = forms.DateField(
        label='Fecha de Aplicación',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text='Fecha exacta en que se aplica el ajuste por Salario Mínimo',
        required=True
    )
    salario_minimo_historico = forms.ModelChoiceField(
        queryset=SalarioMinimoHistorico.objects.all().order_by('-año'),
        label='Salario Mínimo Histórico',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Seleccione el valor del Salario Mínimo Legal Vigente'
    )
    canon_anterior = forms.DecimalField(
        label='Canon Anterior',
        widget=forms.TextInput(attrs={
            'class': 'form-control money-input',
            'placeholder': 'Ingrese el canon anterior'
        }),
        help_text='Canon base sobre el cual se calcula el ajuste',
        required=True
    )
    porcentaje_salario_minimo = forms.DecimalField(
        label='Porcentaje Salario Mínimo (%)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control percentage-input',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Se calcula automáticamente desde la variación del SMLV',
            'readonly': True
        }),
        help_text='Variación porcentual calculada automáticamente comparando con el año anterior del Salario Mínimo',
        required=False
    )
    puntos_adicionales = forms.DecimalField(
        label='Puntos Adicionales (%)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control percentage-input',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Ej: 2.0 o 2,0 para 2.0%'
        }),
        help_text='Puntos adicionales pactados en el contrato',
        required=False,
        initial=0
    )
    canon_anterior_manual = forms.BooleanField(
        required=False,
        label='Ingresar Canon Anterior Manualmente',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Marque esta opción si desea ingresar el canon anterior manualmente en lugar de obtenerlo automáticamente'
    )
    observaciones = forms.CharField(
        label='Observaciones',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        }),
        required=False,
        help_text='Notas adicionales sobre este cálculo'
    )

    def __init__(self, *args, **kwargs):
        # Extraer user de kwargs antes de llamar a super()
        user = kwargs.pop('user', None)
        contrato_initial = kwargs.pop('contrato_initial', None)
        
        # Limpiar datos POST antes de la validación si hay datos
        if args and hasattr(args[0], 'get'):
            data = args[0].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior', 'porcentaje_salario_minimo', 'puntos_adicionales'])
            args = (data,) + args[1:]
        elif 'data' in kwargs and kwargs.get('data'):
            data = kwargs['data'].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior', 'porcentaje_salario_minimo', 'puntos_adicionales'])
            kwargs['data'] = data
        
        super().__init__(*args, **kwargs)
        
        # Guardar user para usar en clean()
        self.user = user
        
        # Si hay un contrato inicial, actualizar queryset para incluirlo
        if contrato_initial:
            try:
                contrato_obj = Contrato.objects.get(id=contrato_initial)
                self.fields['contrato'].queryset = Contrato.objects.filter(
                    tipo_condicion_ipc='SALARIO_MINIMO',
                    vigente=True
                ) | Contrato.objects.filter(id=contrato_initial)
                self.fields['contrato'].initial = contrato_obj
                self.initial['contrato'] = contrato_obj
            except Contrato.DoesNotExist:
                pass
        
        # Actualizar queryset de Salario Mínimo histórico
        self.fields['salario_minimo_historico'].queryset = SalarioMinimoHistorico.objects.all().order_by('-año')
        
        # Restringir campo canon_anterior_manual solo a administradores
        if user and not user.is_staff:
            self.fields['canon_anterior_manual'].widget.attrs['disabled'] = True
            self.fields['canon_anterior_manual'].widget.attrs['readonly'] = True
            self.fields['canon_anterior_manual'].help_text = 'Solo los administradores pueden ingresar el canon anterior manualmente.'
    
    def clean_canon_anterior(self):
        """Limpia y valida el canon anterior"""
        canon = self.cleaned_data.get('canon_anterior')
        if canon:
            try:
                canon_str = str(canon)
                canon_limpio = limpiar_valor_numerico(canon_str, 'Canon Anterior')
                if canon_limpio is None:
                    return None
                if canon_limpio <= 0:
                    raise ValidationError('El canon anterior debe ser mayor a cero')
                return Decimal(str(canon_limpio))
            except ValueError as e:
                raise ValidationError(str(e))
        return canon
    
    def clean(self):
        """Validaciones adicionales y recálculo automático"""
        cleaned_data = super().clean()
        contrato = cleaned_data.get('contrato')
        fecha_aplicacion = cleaned_data.get('fecha_aplicacion')
        salario_minimo_historico = cleaned_data.get('salario_minimo_historico')
        canon_anterior = cleaned_data.get('canon_anterior')
        canon_anterior_manual = cleaned_data.get('canon_anterior_manual', False)
        porcentaje_salario_minimo = cleaned_data.get('porcentaje_salario_minimo', Decimal('0'))
        puntos_adicionales = cleaned_data.get('puntos_adicionales', Decimal('0'))
        
        # Validar que solo administradores puedan usar canon_anterior_manual
        user = getattr(self, 'user', None)
        if user and not user.is_staff:
            if canon_anterior_manual:
                raise ValidationError('Solo los administradores pueden ingresar el canon anterior manualmente.')
            cleaned_data['canon_anterior_manual'] = False
            if hasattr(self, 'data') and self.data.get('canon_anterior_manual'):
                raise ValidationError('No tiene permisos para ingresar el canon anterior manualmente.')
        
        # Validar que el Salario Mínimo histórico corresponda al año de aplicación
        if fecha_aplicacion and salario_minimo_historico:
            año_aplicacion = fecha_aplicacion.year
            # En el año X se aplica el Salario Mínimo del año X
            if salario_minimo_historico.año != año_aplicacion:
                raise ValidationError(
                    f'El Salario Mínimo histórico seleccionado ({salario_minimo_historico.año}) no corresponde '
                    f'al año de aplicación {año_aplicacion}. Debe ser el Salario Mínimo del año {año_aplicacion}.'
                )
        
        # Si no es manual y no hay canon, obtenerlo automáticamente
        if contrato and fecha_aplicacion:
            if not canon_anterior_manual and not canon_anterior:
                from gestion.utils_salario_minimo import obtener_canon_base_para_salario_minimo
                canon_info = obtener_canon_base_para_salario_minimo(contrato, fecha_aplicacion)
                if canon_info['canon']:
                    cleaned_data['canon_anterior'] = canon_info['canon']
                else:
                    if not user or not user.is_staff:
                        raise ValidationError('No se pudo obtener el canon anterior automáticamente. Por favor, contacte a un administrador.')
        
        # Recalcular valores si se modificaron campos relevantes
        if canon_anterior and porcentaje_salario_minimo is not None:
            from gestion.utils_salario_minimo import calcular_ajuste_salario_minimo
            try:
                resultado = calcular_ajuste_salario_minimo(
                    canon_anterior,
                    porcentaje_salario_minimo,
                    puntos_adicionales
                )
                cleaned_data['_porcentaje_total'] = resultado['porcentaje_total']
                cleaned_data['_valor_incremento'] = resultado['valor_incremento']
                cleaned_data['_nuevo_canon'] = resultado['nuevo_canon']
            except ValueError as e:
                raise ValidationError(f'Error al calcular el ajuste: {str(e)}')
        
        return cleaned_data


class EditarCalculoSalarioMinimoForm(BaseModelForm):
    """Formulario para editar un cálculo de Salario Mínimo existente"""
    
    class Meta:
        model = CalculoSalarioMinimo
        fields = ['salario_minimo_historico', 'canon_anterior', 'porcentaje_salario_minimo', 'puntos_adicionales', 'observaciones', 'estado']
        widgets = {
            'salario_minimo_historico': forms.Select(attrs={'class': 'form-control'}),
            'canon_anterior': forms.TextInput(attrs={
                'class': 'form-control money-input',
                'placeholder': 'Ingrese el canon anterior'
            }),
            'porcentaje_salario_minimo': forms.NumberInput(attrs={
                'class': 'form-control percentage-input',
                'step': '0.01',
                'min': '0'
            }),
            'puntos_adicionales': forms.NumberInput(attrs={
                'class': 'form-control percentage-input',
                'step': '0.01',
                'min': '0'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'salario_minimo_historico': 'Salario Mínimo Histórico',
            'canon_anterior': 'Canon Anterior',
            'porcentaje_salario_minimo': 'Porcentaje Salario Mínimo (%)',
            'puntos_adicionales': 'Puntos Adicionales (%)',
            'observaciones': 'Observaciones',
            'estado': 'Estado',
        }
        help_texts = {
            'salario_minimo_historico': 'Valor del Salario Mínimo Legal Vigente',
            'canon_anterior': 'Canon base sobre el cual se calcula el ajuste',
            'porcentaje_salario_minimo': 'Porcentaje del Salario Mínimo pactado en el contrato',
            'puntos_adicionales': 'Puntos adicionales pactados en el contrato',
            'observaciones': 'Notas adicionales sobre este cálculo',
            'estado': 'Estado del cálculo',
        }
    
    def __init__(self, *args, **kwargs):
        if args and hasattr(args[0], 'get'):
            data = args[0].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior', 'porcentaje_salario_minimo', 'puntos_adicionales'])
            args = (data,) + args[1:]
        elif 'data' in kwargs and kwargs.get('data'):
            data = kwargs['data'].copy()
            data = limpiar_datos_post_numericos(data, ['canon_anterior', 'porcentaje_salario_minimo', 'puntos_adicionales'])
            kwargs['data'] = data
        
        super().__init__(*args, **kwargs)
        
        # Actualizar queryset de Salario Mínimo histórico
        self.fields['salario_minimo_historico'].queryset = SalarioMinimoHistorico.objects.all().order_by('-año')
        
        # Si hay instancia, limitar el queryset al año de aplicación
        if self.instance and self.instance.pk:
            año_aplicacion = self.instance.año_aplicacion
            self.fields['salario_minimo_historico'].queryset = SalarioMinimoHistorico.objects.filter(año=año_aplicacion).order_by('-año')
    
    def clean_canon_anterior(self):
        """Limpia y valida el canon anterior"""
        canon = self.cleaned_data.get('canon_anterior')
        if canon:
            try:
                canon_str = str(canon)
                canon_limpio = limpiar_valor_numerico(canon_str, 'Canon Anterior')
                if canon_limpio is None:
                    return None
                if canon_limpio <= 0:
                    raise ValidationError('El canon anterior debe ser mayor a cero')
                return Decimal(str(canon_limpio))
            except ValueError as e:
                raise ValidationError(str(e))
        return canon
    
    def clean(self):
        """Validaciones adicionales y recálculo automático"""
        cleaned_data = super().clean()
        salario_minimo_historico = cleaned_data.get('salario_minimo_historico')
        canon_anterior = cleaned_data.get('canon_anterior')
        puntos_adicionales = cleaned_data.get('puntos_adicionales', Decimal('0'))
        
        # Obtener variación del salario mínimo histórico
        variacion_salario_minimo = None
        if salario_minimo_historico:
            variacion_salario_minimo = salario_minimo_historico.variacion_porcentual
            # Si no hay variación (primer año), usar porcentaje del formulario como fallback
            if variacion_salario_minimo is None:
                porcentaje_form = cleaned_data.get('porcentaje_salario_minimo')
                if porcentaje_form:
                    variacion_salario_minimo = porcentaje_form
                else:
                    raise ValidationError({
                        'salario_minimo_historico': 'El Salario Mínimo seleccionado no tiene variación calculada (primer año). '
                                                   'Por favor, ingrese el porcentaje manualmente.'
                    })
        
        # Validar que el Salario Mínimo histórico corresponda al año de aplicación
        if self.instance and self.instance.pk:
            año_aplicacion = self.instance.año_aplicacion
            if salario_minimo_historico and salario_minimo_historico.año != año_aplicacion:
                raise ValidationError({
                    'salario_minimo_historico': f'El Salario Mínimo histórico seleccionado ({salario_minimo_historico.año}) no corresponde '
                                               f'al año de aplicación {año_aplicacion}. Debe ser el Salario Mínimo del año {año_aplicacion}.'
                })
        
        # Recalcular valores si se modificaron campos relevantes
        if canon_anterior and variacion_salario_minimo is not None:
            from gestion.utils_salario_minimo import calcular_ajuste_salario_minimo
            try:
                resultado = calcular_ajuste_salario_minimo(
                    canon_anterior,
                    variacion_salario_minimo,
                    puntos_adicionales
                )
                cleaned_data['_porcentaje_total'] = resultado['porcentaje_total']
                cleaned_data['_valor_incremento'] = resultado['valor_incremento']
                cleaned_data['_nuevo_canon'] = resultado['nuevo_canon']
                # Guardar la variación en porcentaje_salario_minimo para compatibilidad con el modelo
                cleaned_data['porcentaje_salario_minimo'] = variacion_salario_minimo
            except ValueError as e:
                raise ValidationError(f'Error al calcular el ajuste: {str(e)}')
        
        return cleaned_data
