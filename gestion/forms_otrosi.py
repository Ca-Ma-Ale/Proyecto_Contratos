"""
Formularios para el módulo de Otro Sí
"""
from django import forms
from .models import (
    OtroSi, Contrato, MESES_CHOICES, 
    obtener_tipos_condicion_ipc_choices, obtener_periodicidades_ipc_choices
)
from datetime import date
from .utils_formateo import limpiar_valor_numerico, limpiar_datos_post_numericos
from .forms import BaseModelForm


class DateInputHTML5(forms.DateInput):
    """Widget personalizado para campos de fecha HTML5 que siempre formatea en YYYY-MM-DD"""
    input_type = 'date'
    
    def format_value(self, value):
        """Formatea el valor al formato YYYY-MM-DD requerido por HTML5 date inputs"""
        if value is None:
            return ''
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        # Si ya es un string, intentar parsearlo
        if isinstance(value, str):
            # Si ya está en formato YYYY-MM-DD, devolverlo tal cual
            if len(value) == 10 and value[4] == '-' and value[7] == '-':
                return value
            # Intentar parsear otros formatos comunes
            try:
                from datetime import datetime
                # Intentar formato dd/MM/yyyy
                if '/' in value:
                    parts = value.split('/')
                    if len(parts) == 3:
                        d = datetime.strptime(value, '%d/%m/%Y')
                        return d.strftime('%Y-%m-%d')
            except:
                pass
        return super().format_value(value) if hasattr(super(), 'format_value') else value


class OtroSiForm(BaseModelForm):
    """Formulario para crear/editar Otro Sí"""
    
    # Opciones de modalidad de pago (iguales a las del modelo Contrato)
    MODALIDAD_CHOICES = [
        ('', '---------'),
        ('Fijo', 'Fijo'),
        ('Variable Puro', 'Variable Puro'),
        ('Hibrido (Min Garantizado)', 'Híbrido (Min Garantizado)'),
    ]
    
    # Campo de modalidad de pago con Select
    nueva_modalidad_pago = forms.ChoiceField(
        choices=MODALIDAD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Nueva Modalidad de Pago'
    )
    
    # Campo de fecha de aumento IPC
    nueva_fecha_aumento_ipc = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}),
        label='Nueva Fecha Aumento IPC',
        help_text='Fecha exacta en que se aplica el ajuste por IPC'
    )
    
    # Sobreescribir campos numéricos como CharField para manejar formato
    nuevo_valor_canon = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Nuevo Valor Canon'
    )
    nuevo_canon_minimo_garantizado = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Nuevo Canon Mínimo Garantizado'
    )
    nuevo_porcentaje_ventas = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'percentage-input form-control'}),
        label='Nuevo % Ventas'
    )
    nuevos_puntos_adicionales_ipc = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'percentage-input form-control'}),
        label='Nuevos Puntos Adicionales IPC'
    )
    
    # Campos de Pólizas - RCE
    nuevo_exige_poliza_rce = forms.BooleanField(required=False, label='¿Exige Póliza RCE?')
    nuevo_valor_asegurado_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Valor Asegurado RCE'
    )
    nuevo_valor_propietario_locatario_ocupante_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='PLO (Propietario, Locatario y Ocupante)'
    )
    nuevo_valor_patronal_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Patronal'
    )
    nuevo_valor_gastos_medicos_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Gastos Médicos de Terceros'
    )
    nuevo_valor_vehiculos_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Vehículos Propios y No Propios'
    )
    nuevo_valor_contratistas_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Contratistas y Subcontratistas'
    )
    nuevo_valor_perjuicios_extrapatrimoniales_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Perjuicios Extrapatrimoniales'
    )
    nuevo_valor_dano_moral_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Daño Moral'
    )
    nuevo_valor_lucro_cesante_rce = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Lucro Cesante'
    )
    # Campos RCE - Coberturas para PROVEEDOR
    nuevo_rce_cobertura_danos_materiales = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Daños materiales a terceros'
    )
    nuevo_rce_cobertura_lesiones_personales = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Lesiones personales a terceros'
    )
    nuevo_rce_cobertura_muerte_terceros = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Muerte de terceros'
    )
    nuevo_rce_cobertura_danos_bienes_terceros = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Daños a bienes de terceros'
    )
    nuevo_rce_cobertura_responsabilidad_patronal = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Responsabilidad patronal (si aplica)'
    )
    nuevo_rce_cobertura_responsabilidad_cruzada = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Responsabilidad cruzada (si aplica)'
    )
    nuevo_rce_cobertura_danos_contratistas = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Daños causados por contratistas y subcontratistas (si aplica)'
    )
    nuevo_rce_cobertura_danos_ejecucion_contrato = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Daños durante la ejecución del contrato'
    )
    nuevo_rce_cobertura_danos_predios_vecinos = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Daños en predios vecinos (si aplica)'
    )
    nuevo_rce_cobertura_gastos_medicos = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Gastos médicos (si aplica)'
    )
    nuevo_rce_cobertura_gastos_defensa = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Gastos de defensa (si aplica)'
    )
    nuevo_rce_cobertura_perjuicios_patrimoniales = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Perjuicios patrimoniales consecuenciales (si aplica)'
    )
    nuevo_meses_vigencia_rce = forms.IntegerField(required=False, label='Meses de Vigencia RCE')
    nuevo_fecha_inicio_vigencia_rce = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Inicio Vigencia RCE'
    )
    nuevo_fecha_fin_vigencia_rce = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Fin Vigencia RCE'
    )
    
    # Campos de Pólizas - Cumplimiento
    nuevo_exige_poliza_cumplimiento = forms.BooleanField(required=False, label='¿Exige Póliza de Cumplimiento?')
    nuevo_valor_asegurado_cumplimiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Valor Asegurado Cumplimiento'
    )
    nuevo_valor_remuneraciones_cumplimiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Remuneraciones Mensuales'
    )
    nuevo_valor_servicios_publicos_cumplimiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Servicios Públicos'
    )
    nuevo_valor_iva_cumplimiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='IVA'
    )
    nuevo_valor_otros_cumplimiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Cuota de Administración'
    )
    # Campos Cumplimiento - Amparos para PROVEEDOR
    nuevo_cumplimiento_amparo_cumplimiento_contrato = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Cumplimiento del contrato'
    )
    nuevo_cumplimiento_amparo_buen_manejo_anticipo = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Buen manejo y correcta inversión del anticipo (si aplica)'
    )
    nuevo_cumplimiento_amparo_amortizacion_anticipo = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Correcta amortización del anticipo (si aplica)'
    )
    nuevo_cumplimiento_amparo_salarios_prestaciones = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Salarios, prestaciones sociales e indemnizaciones laborales'
    )
    nuevo_cumplimiento_amparo_aportes_seguridad_social = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Aportes al sistema de seguridad social'
    )
    nuevo_cumplimiento_amparo_calidad_servicio = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Calidad del servicio'
    )
    nuevo_cumplimiento_amparo_estabilidad_obra = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Estabilidad de la obra (si aplica)'
    )
    nuevo_cumplimiento_amparo_calidad_bienes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Calidad y correcto funcionamiento de bienes (si aplica)'
    )
    nuevo_cumplimiento_amparo_multas = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Multas (si aplica)'
    )
    nuevo_cumplimiento_amparo_clausula_penal = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Cláusula penal pecuniaria (si aplica)'
    )
    nuevo_cumplimiento_amparo_sanciones_incumplimiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Sanciones por incumplimiento (si aplica)'
    )
    nuevo_meses_vigencia_cumplimiento = forms.IntegerField(required=False, label='Meses de Vigencia Cumplimiento')
    nuevo_fecha_inicio_vigencia_cumplimiento = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Inicio Vigencia Cumplimiento'
    )
    nuevo_fecha_fin_vigencia_cumplimiento = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Fin Vigencia Cumplimiento'
    )
    
    # Campos de Pólizas - Arrendamiento
    nuevo_exige_poliza_arrendamiento = forms.BooleanField(required=False, label='¿Exige Póliza de Arrendamiento?')
    nuevo_valor_asegurado_arrendamiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Valor Asegurado Arrendamiento'
    )
    nuevo_valor_remuneraciones_arrendamiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Remuneraciones Mensuales'
    )
    nuevo_valor_servicios_publicos_arrendamiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Servicios Públicos'
    )
    nuevo_valor_iva_arrendamiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='IVA'
    )
    nuevo_valor_otros_arrendamiento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Cuota de Administración'
    )
    nuevo_meses_vigencia_arrendamiento = forms.IntegerField(required=False, label='Meses de Vigencia Arrendamiento')
    nuevo_fecha_inicio_vigencia_arrendamiento = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Inicio Vigencia Arrendamiento'
    )
    nuevo_fecha_fin_vigencia_arrendamiento = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Fin Vigencia Arrendamiento'
    )
    
    # Campos de Pólizas - Todo Riesgo
    nuevo_exige_poliza_todo_riesgo = forms.BooleanField(required=False, label='¿Exige Póliza Todo Riesgo?')
    nuevo_valor_asegurado_todo_riesgo = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Valor Asegurado Todo Riesgo'
    )
    nuevo_meses_vigencia_todo_riesgo = forms.IntegerField(required=False, label='Meses de Vigencia Todo Riesgo')
    nuevo_fecha_inicio_vigencia_todo_riesgo = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Inicio Vigencia Todo Riesgo'
    )
    nuevo_fecha_fin_vigencia_todo_riesgo = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Fin Vigencia Todo Riesgo'
    )
    
    # Campos de Pólizas - Otras
    nuevo_exige_poliza_otra_1 = forms.BooleanField(required=False, label='¿Exige Otras Pólizas?')
    nuevo_nombre_poliza_otra_1 = forms.CharField(required=False, label='Nombre Otras Pólizas')
    nuevo_valor_asegurado_otra_1 = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'money-input form-control'}),
        label='Valor Asegurado Otras Pólizas'
    )
    nuevo_meses_vigencia_otra_1 = forms.IntegerField(required=False, label='Meses de Vigencia Otras Pólizas')
    nuevo_fecha_inicio_vigencia_otra_1 = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Inicio Vigencia Otras Pólizas'
    )
    nuevo_fecha_fin_vigencia_otra_1 = forms.DateField(
        required=False,
        widget=DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
        label='Fecha Fin Vigencia Otras Pólizas'
    )
    
    def save(self, commit=True):
        """Override save para asegurar que None se mantenga como None y no se convierta a 0"""
        instance = super().save(commit=False)
        
        # Campos que deben mantenerse como None si no se modificaron
        campos_opcionales = [
            'nuevos_puntos_adicionales_ipc',
            'nuevo_porcentaje_ventas',
        ]
        
        for campo in campos_opcionales:
            valor = getattr(instance, campo, None)
            # Si el valor es 0 y no está en los datos POST, establecerlo como None
            if valor is not None:
                from decimal import Decimal
                if isinstance(valor, Decimal) and valor == 0:
                    campo_en_post = campo in self.data if hasattr(self, 'data') else False
                    if not campo_en_post:
                        setattr(instance, campo, None)
        
        if commit:
            instance.save()
        return instance
    
    class Meta:
        model = OtroSi
        exclude = ['contrato', 'creado_por', 'fecha_creacion', 'aprobado_por', 'fecha_aprobacion', 'modificado_por', 'fecha_modificacion', 'version']
        widgets = {
            'fecha_otrosi': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'effective_from': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'effective_to': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'nueva_fecha_final_actualizada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'clausulas_modificadas': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'justificacion_legal': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'numero_otrosi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Se genera automáticamente', 'readonly': 'readonly'}),
            'nuevo_plazo_meses': forms.NumberInput(attrs={'class': 'form-control'}),
            'nuevo_tipo_condicion_ipc': forms.Select(attrs={'class': 'form-control'}),
            'nueva_periodicidad_ipc': forms.Select(attrs={'class': 'form-control'}),
            # Pólizas
            'modifica_polizas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notas_polizas': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Detalle de las modificaciones en pólizas (ej: actualización de RCE, nueva vigencia de cumplimiento, etc.)'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Guardar contrato para inicializar valores de pólizas
        self.contrato = kwargs.pop('contrato', None)
        self.contrato_id = kwargs.pop('contrato_id', None)
        
        # Si no tenemos contrato pero tenemos contrato_id, obtenerlo
        if not self.contrato and self.contrato_id:
            try:
                self.contrato = Contrato.objects.get(id=self.contrato_id)
            except Contrato.DoesNotExist:
                self.contrato = None
        
        # Limpiar datos antes de la validación si hay datos POST
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data'].copy()
            self._limpiar_datos_post(data)
            kwargs['data'] = data
        
        super().__init__(*args, **kwargs)
        
        # Actualizar choices de IPC desde la BD
        if 'nuevo_tipo_condicion_ipc' in self.fields:
            self.fields['nuevo_tipo_condicion_ipc'].choices = [('', '---------')] + obtener_tipos_condicion_ipc_choices()
        if 'nueva_periodicidad_ipc' in self.fields:
            self.fields['nueva_periodicidad_ipc'].choices = [('', '---------')] + obtener_periodicidades_ipc_choices()
        
        # Hacer numero_otrosi no requerido (se genera auto)
        self.fields['numero_otrosi'].required = False
        # Deshabilitar edición en el formulario; será asignado automáticamente en el modelo
        if 'numero_otrosi' in self.fields:
            self.fields['numero_otrosi'].disabled = True
        
        # Configurar formato de fecha para campos de fecha (IMPORTANTE para HTML5 date inputs)
        fecha_fields = [
            'fecha_otrosi', 'effective_from', 'effective_to', 'nueva_fecha_final_actualizada',
            'nueva_fecha_aumento_ipc',
            'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
            'nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento',
            'nuevo_fecha_inicio_vigencia_arrendamiento', 'nuevo_fecha_fin_vigencia_arrendamiento',
            'nuevo_fecha_inicio_vigencia_todo_riesgo', 'nuevo_fecha_fin_vigencia_todo_riesgo',
            'nuevo_fecha_inicio_vigencia_otra_1', 'nuevo_fecha_fin_vigencia_otra_1'
        ]
        
        # Configurar widget para url_archivo
        if 'url_archivo' in self.fields:
            self.fields['url_archivo'].widget = forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'})
        for field_name in fecha_fields:
            if field_name in self.fields:
                self.fields[field_name].input_formats = ['%Y-%m-%d']
        
        # Hacer campos numéricos opcionales para evitar error de validación con formato
        campos_opcionales = [
            'nuevo_valor_canon', 'nuevo_canon_minimo_garantizado',
            'nuevo_porcentaje_ventas', 'nuevos_puntos_adicionales_ipc',
            'nueva_fecha_final_actualizada', 'nuevo_plazo_meses',
            # Campos de pólizas
            'nuevo_valor_asegurado_rce', 'nuevo_valor_propietario_locatario_ocupante_rce',
            'nuevo_valor_patronal_rce', 'nuevo_valor_gastos_medicos_rce',
            'nuevo_valor_vehiculos_rce', 'nuevo_valor_contratistas_rce',
            'nuevo_valor_perjuicios_extrapatrimoniales_rce', 'nuevo_valor_dano_moral_rce',
            'nuevo_valor_lucro_cesante_rce', 'nuevo_meses_vigencia_rce',
            'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
            'nuevo_valor_asegurado_cumplimiento', 'nuevo_valor_remuneraciones_cumplimiento',
            'nuevo_valor_servicios_publicos_cumplimiento', 'nuevo_valor_iva_cumplimiento',
            'nuevo_valor_otros_cumplimiento', 'nuevo_meses_vigencia_cumplimiento',
            'nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento',
            'nuevo_valor_asegurado_arrendamiento', 'nuevo_valor_remuneraciones_arrendamiento',
            'nuevo_valor_servicios_publicos_arrendamiento', 'nuevo_valor_iva_arrendamiento',
            'nuevo_valor_otros_arrendamiento', 'nuevo_meses_vigencia_arrendamiento',
            'nuevo_fecha_inicio_vigencia_arrendamiento', 'nuevo_fecha_fin_vigencia_arrendamiento',
            'nuevo_valor_asegurado_todo_riesgo', 'nuevo_meses_vigencia_todo_riesgo',
            'nuevo_fecha_inicio_vigencia_todo_riesgo', 'nuevo_fecha_fin_vigencia_todo_riesgo',
            'nuevo_nombre_poliza_otra_1', 'nuevo_valor_asegurado_otra_1',
            'nuevo_meses_vigencia_otra_1', 'nuevo_fecha_inicio_vigencia_otra_1',
            'nuevo_fecha_fin_vigencia_otra_1'
        ]
        for campo in campos_opcionales:
            if campo in self.fields:
                self.fields[campo].required = False
        
        # Si estamos editando (hay instance.pk), asegurar que las fechas estén en formato correcto
        # Esto debe hacerse DESPUÉS de super().__init__ para que Django inicialice los valores desde instance
        if self.instance and self.instance.pk:
            self._formatear_fechas_para_edicion()
        
        # Inicializar campos de pólizas con valores del contrato si es nuevo OtroSi y no hay datos POST
        if self.contrato and not self.instance.pk and not kwargs.get('data'):
            self._inicializar_valores_polizas_desde_contrato()
        
        # Mostrar/ocultar campos según tipo de contrato
        if self.contrato:
            tipo_contrato = self.contrato.tipo_contrato_cliente_proveedor
            
            if tipo_contrato == 'PROVEEDOR':
                # Ocultar campos de CLIENTE para RCE
                campos_cliente_rce = [
                    'nuevo_valor_propietario_locatario_ocupante_rce', 'nuevo_valor_patronal_rce',
                    'nuevo_valor_gastos_medicos_rce', 'nuevo_valor_vehiculos_rce', 'nuevo_valor_contratistas_rce',
                    'nuevo_valor_perjuicios_extrapatrimoniales_rce', 'nuevo_valor_dano_moral_rce', 'nuevo_valor_lucro_cesante_rce'
                ]
                for campo in campos_cliente_rce:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False
                
                # Ocultar campos de CLIENTE para Cumplimiento
                campos_cliente_cumplimiento = [
                    'nuevo_valor_remuneraciones_cumplimiento', 'nuevo_valor_servicios_publicos_cumplimiento',
                    'nuevo_valor_iva_cumplimiento', 'nuevo_valor_otros_cumplimiento'
                ]
                for campo in campos_cliente_cumplimiento:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False
            
            elif tipo_contrato == 'CLIENTE':
                # Ocultar campos de PROVEEDOR para RCE
                campos_proveedor_rce = [
                    'nuevo_rce_cobertura_danos_materiales', 'nuevo_rce_cobertura_lesiones_personales',
                    'nuevo_rce_cobertura_muerte_terceros', 'nuevo_rce_cobertura_danos_bienes_terceros',
                    'nuevo_rce_cobertura_responsabilidad_patronal', 'nuevo_rce_cobertura_responsabilidad_cruzada',
                    'nuevo_rce_cobertura_danos_contratistas', 'nuevo_rce_cobertura_danos_ejecucion_contrato',
                    'nuevo_rce_cobertura_danos_predios_vecinos', 'nuevo_rce_cobertura_gastos_medicos',
                    'nuevo_rce_cobertura_gastos_defensa', 'nuevo_rce_cobertura_perjuicios_patrimoniales'
                ]
                for campo in campos_proveedor_rce:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False
                
                # Ocultar campos de PROVEEDOR para Cumplimiento
                campos_proveedor_cumplimiento = [
                    'nuevo_cumplimiento_amparo_cumplimiento_contrato', 'nuevo_cumplimiento_amparo_buen_manejo_anticipo',
                    'nuevo_cumplimiento_amparo_amortizacion_anticipo', 'nuevo_cumplimiento_amparo_salarios_prestaciones',
                    'nuevo_cumplimiento_amparo_aportes_seguridad_social', 'nuevo_cumplimiento_amparo_calidad_servicio',
                    'nuevo_cumplimiento_amparo_estabilidad_obra', 'nuevo_cumplimiento_amparo_calidad_bienes',
                    'nuevo_cumplimiento_amparo_multas', 'nuevo_cumplimiento_amparo_clausula_penal',
                    'nuevo_cumplimiento_amparo_sanciones_incumplimiento'
                ]
                for campo in campos_proveedor_cumplimiento:
                    if campo in self.fields:
                        self.fields[campo].widget = forms.HiddenInput()
                        self.fields[campo].required = False
        
        # Ocultar nueva_fecha_final_actualizada (se muestra como campo de solo lectura en el template)
        if 'nueva_fecha_final_actualizada' in self.fields:
            self.fields['nueva_fecha_final_actualizada'].widget = forms.HiddenInput()
            self.fields['nueva_fecha_final_actualizada'].required = False
        
        # Deshabilitar campos de vigencia si el contrato tiene renovación automática
        if self.contrato and self.contrato.prorroga_automatica:
            campos_vigencia = ['nueva_fecha_final_actualizada', 'nuevo_plazo_meses']
            for campo in campos_vigencia:
                if campo in self.fields:
                    self.fields[campo].disabled = True
                    self.fields[campo].widget.attrs['disabled'] = 'disabled'
                    self.fields[campo].required = False
        
        # Los campos de selección ya tienen las opciones del modelo
    
    def clean_numero_otrosi(self):
        """Forzar número automático: ignorar cualquier valor enviado."""
        # En creación, devolver None para que el modelo lo asigne; en edición, conservar el existente
        if self.instance and self.instance.pk:
            return self.instance.numero_otrosi
        return None

    def _obtener_ultimo_otrosi_aprobado(self):
        """Obtiene el último OtroSi aprobado del contrato (sin importar fecha de vigencia)"""
        if not self.contrato:
            return None
        
        # Buscar el último OtroSi aprobado, excluyendo el actual si estamos editando
        otrosis_aprobados = OtroSi.objects.filter(
            contrato=self.contrato,
            estado='APROBADO'
        )
        
        # Excluir el OtroSi actual si estamos editando
        if self.instance and self.instance.pk:
            otrosis_aprobados = otrosis_aprobados.exclude(pk=self.instance.pk)
        
        # Ordenar por fecha de creación y versión descendente
        return otrosis_aprobados.order_by('-fecha_creacion', '-version').first()
    
    def _formatear_fechas_para_edicion(self):
        """Formatea las fechas de la instancia al formato YYYY-MM-DD para campos HTML5 date"""
        fecha_fields = [
            'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
            'nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento',
            'nuevo_fecha_inicio_vigencia_arrendamiento', 'nuevo_fecha_fin_vigencia_arrendamiento',
            'nuevo_fecha_inicio_vigencia_todo_riesgo', 'nuevo_fecha_fin_vigencia_todo_riesgo',
            'nuevo_fecha_inicio_vigencia_otra_1', 'nuevo_fecha_fin_vigencia_otra_1'
        ]
        
        for field_name in fecha_fields:
            if field_name in self.fields:
                fecha_valor = getattr(self.instance, field_name, None)
                if fecha_valor:
                    # Formatear fecha al formato YYYY-MM-DD requerido por HTML5 date inputs
                    fecha_formateada = fecha_valor.strftime('%Y-%m-%d')
                    # Establecer en initial para que Django lo use al renderizar
                    self.initial[field_name] = fecha_formateada
                    # También asegurar que el widget tenga el formato correcto
                    if hasattr(self.fields[field_name], 'widget'):
                        self.fields[field_name].widget.format = '%Y-%m-%d'
    
    def _obtener_valor_base_poliza(self, campo_otrosi, campo_contrato, otrosi_previo=None):
        """Obtiene el valor base para un campo de póliza: primero del OtroSi previo, luego del contrato"""
        # Si hay OtroSi previo con modifica_polizas=True, usar sus valores
        if otrosi_previo and otrosi_previo.modifica_polizas:
            valor_otrosi = getattr(otrosi_previo, campo_otrosi, None)
            if valor_otrosi is not None:
                return valor_otrosi
        
        # Si no hay OtroSi previo o no tiene ese campo, usar el valor del contrato
        return getattr(self.contrato, campo_contrato, None)
    
    def _inicializar_valores_polizas_desde_contrato(self):
        """
        Inicializa los campos de pólizas con los valores base.
        Si existe un OtroSi previo aprobado que modifica pólizas, usa esos valores.
        Si no, usa los valores del contrato inicial.
        """
        if not self.contrato:
            return
        
        # Buscar último OtroSi aprobado previo
        otrosi_previo = self._obtener_ultimo_otrosi_aprobado()
        
        # Función auxiliar para obtener valor base
        def obtener_valor(campo_otrosi, campo_contrato):
            return self._obtener_valor_base_poliza(campo_otrosi, campo_contrato, otrosi_previo)
        
        # RCE
        exige_rce = obtener_valor('nuevo_exige_poliza_rce', 'exige_poliza_rce')
        if exige_rce:
            self.initial['nuevo_exige_poliza_rce'] = True
            valor = obtener_valor('nuevo_valor_asegurado_rce', 'valor_asegurado_rce')
            if valor:
                self.initial['nuevo_valor_asegurado_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_propietario_locatario_ocupante_rce', 'valor_propietario_locatario_ocupante_rce')
            if valor:
                self.initial['nuevo_valor_propietario_locatario_ocupante_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_patronal_rce', 'valor_patronal_rce')
            if valor:
                self.initial['nuevo_valor_patronal_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_gastos_medicos_rce', 'valor_gastos_medicos_rce')
            if valor:
                self.initial['nuevo_valor_gastos_medicos_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_vehiculos_rce', 'valor_vehiculos_rce')
            if valor:
                self.initial['nuevo_valor_vehiculos_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_contratistas_rce', 'valor_contratistas_rce')
            if valor:
                self.initial['nuevo_valor_contratistas_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_perjuicios_extrapatrimoniales_rce', 'valor_perjuicios_extrapatrimoniales_rce')
            if valor:
                self.initial['nuevo_valor_perjuicios_extrapatrimoniales_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_dano_moral_rce', 'valor_dano_moral_rce')
            if valor:
                self.initial['nuevo_valor_dano_moral_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_lucro_cesante_rce', 'valor_lucro_cesante_rce')
            if valor:
                self.initial['nuevo_valor_lucro_cesante_rce'] = str(int(valor))
            
            valor = obtener_valor('nuevo_meses_vigencia_rce', 'meses_vigencia_rce')
            if valor:
                self.initial['nuevo_meses_vigencia_rce'] = valor
            
            # Fechas RCE
            fecha_inicio = obtener_valor('nuevo_fecha_inicio_vigencia_rce', 'fecha_inicio_vigencia_rce')
            if fecha_inicio:
                self.initial['nuevo_fecha_inicio_vigencia_rce'] = fecha_inicio
            
            fecha_fin = obtener_valor('nuevo_fecha_fin_vigencia_rce', 'fecha_fin_vigencia_rce')
            if fecha_fin:
                self.initial['nuevo_fecha_fin_vigencia_rce'] = fecha_fin
            elif fecha_inicio and valor:
                # Calcular fecha fin si no existe pero tenemos fecha inicio y meses
                from .utils import calcular_fecha_vencimiento
                self.initial['nuevo_fecha_fin_vigencia_rce'] = calcular_fecha_vencimiento(fecha_inicio, valor)
        
        # Cumplimiento
        exige_cumplimiento = obtener_valor('nuevo_exige_poliza_cumplimiento', 'exige_poliza_cumplimiento')
        if exige_cumplimiento:
            self.initial['nuevo_exige_poliza_cumplimiento'] = True
            valor = obtener_valor('nuevo_valor_asegurado_cumplimiento', 'valor_asegurado_cumplimiento')
            if valor:
                self.initial['nuevo_valor_asegurado_cumplimiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_remuneraciones_cumplimiento', 'valor_remuneraciones_cumplimiento')
            if valor:
                self.initial['nuevo_valor_remuneraciones_cumplimiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_servicios_publicos_cumplimiento', 'valor_servicios_publicos_cumplimiento')
            if valor:
                self.initial['nuevo_valor_servicios_publicos_cumplimiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_iva_cumplimiento', 'valor_iva_cumplimiento')
            if valor:
                self.initial['nuevo_valor_iva_cumplimiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_otros_cumplimiento', 'valor_otros_cumplimiento')
            if valor:
                self.initial['nuevo_valor_otros_cumplimiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_meses_vigencia_cumplimiento', 'meses_vigencia_cumplimiento')
            if valor:
                self.initial['nuevo_meses_vigencia_cumplimiento'] = valor
            
            # Fechas Cumplimiento
            fecha_inicio = obtener_valor('nuevo_fecha_inicio_vigencia_cumplimiento', 'fecha_inicio_vigencia_cumplimiento')
            if fecha_inicio:
                self.initial['nuevo_fecha_inicio_vigencia_cumplimiento'] = fecha_inicio
            
            fecha_fin = obtener_valor('nuevo_fecha_fin_vigencia_cumplimiento', 'fecha_fin_vigencia_cumplimiento')
            if fecha_fin:
                self.initial['nuevo_fecha_fin_vigencia_cumplimiento'] = fecha_fin
            elif fecha_inicio and valor:
                from .utils import calcular_fecha_vencimiento
                self.initial['nuevo_fecha_fin_vigencia_cumplimiento'] = calcular_fecha_vencimiento(fecha_inicio, valor)
        
        # Arrendamiento
        exige_arrendamiento = obtener_valor('nuevo_exige_poliza_arrendamiento', 'exige_poliza_arrendamiento')
        if exige_arrendamiento:
            self.initial['nuevo_exige_poliza_arrendamiento'] = True
            valor = obtener_valor('nuevo_valor_asegurado_arrendamiento', 'valor_asegurado_arrendamiento')
            if valor:
                self.initial['nuevo_valor_asegurado_arrendamiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_remuneraciones_arrendamiento', 'valor_remuneraciones_arrendamiento')
            if valor:
                self.initial['nuevo_valor_remuneraciones_arrendamiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_servicios_publicos_arrendamiento', 'valor_servicios_publicos_arrendamiento')
            if valor:
                self.initial['nuevo_valor_servicios_publicos_arrendamiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_iva_arrendamiento', 'valor_iva_arrendamiento')
            if valor:
                self.initial['nuevo_valor_iva_arrendamiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_valor_otros_arrendamiento', 'valor_otros_arrendamiento')
            if valor:
                self.initial['nuevo_valor_otros_arrendamiento'] = str(int(valor))
            
            valor = obtener_valor('nuevo_meses_vigencia_arrendamiento', 'meses_vigencia_arrendamiento')
            if valor:
                self.initial['nuevo_meses_vigencia_arrendamiento'] = valor
            
            # Fechas Arrendamiento
            fecha_inicio = obtener_valor('nuevo_fecha_inicio_vigencia_arrendamiento', 'fecha_inicio_vigencia_arrendamiento')
            if fecha_inicio:
                self.initial['nuevo_fecha_inicio_vigencia_arrendamiento'] = fecha_inicio
            
            fecha_fin = obtener_valor('nuevo_fecha_fin_vigencia_arrendamiento', 'fecha_fin_vigencia_arrendamiento')
            if fecha_fin:
                self.initial['nuevo_fecha_fin_vigencia_arrendamiento'] = fecha_fin
            elif fecha_inicio and valor:
                from .utils import calcular_fecha_vencimiento
                self.initial['nuevo_fecha_fin_vigencia_arrendamiento'] = calcular_fecha_vencimiento(fecha_inicio, valor)
        
        # Todo Riesgo
        exige_todo_riesgo = obtener_valor('nuevo_exige_poliza_todo_riesgo', 'exige_poliza_todo_riesgo')
        if exige_todo_riesgo:
            self.initial['nuevo_exige_poliza_todo_riesgo'] = True
            valor = obtener_valor('nuevo_valor_asegurado_todo_riesgo', 'valor_asegurado_todo_riesgo')
            if valor:
                self.initial['nuevo_valor_asegurado_todo_riesgo'] = str(int(valor))
            
            valor = obtener_valor('nuevo_meses_vigencia_todo_riesgo', 'meses_vigencia_todo_riesgo')
            if valor:
                self.initial['nuevo_meses_vigencia_todo_riesgo'] = valor
            
            # Fechas Todo Riesgo
            fecha_inicio = obtener_valor('nuevo_fecha_inicio_vigencia_todo_riesgo', 'fecha_inicio_vigencia_todo_riesgo')
            if fecha_inicio:
                self.initial['nuevo_fecha_inicio_vigencia_todo_riesgo'] = fecha_inicio
            
            fecha_fin = obtener_valor('nuevo_fecha_fin_vigencia_todo_riesgo', 'fecha_fin_vigencia_todo_riesgo')
            if fecha_fin:
                self.initial['nuevo_fecha_fin_vigencia_todo_riesgo'] = fecha_fin
            elif fecha_inicio and valor:
                from .utils import calcular_fecha_vencimiento
                self.initial['nuevo_fecha_fin_vigencia_todo_riesgo'] = calcular_fecha_vencimiento(fecha_inicio, valor)
        
        # Otras Pólizas
        exige_otra = obtener_valor('nuevo_exige_poliza_otra_1', 'exige_poliza_otra_1')
        if exige_otra:
            self.initial['nuevo_exige_poliza_otra_1'] = True
            valor = obtener_valor('nuevo_nombre_poliza_otra_1', 'nombre_poliza_otra_1')
            if valor:
                self.initial['nuevo_nombre_poliza_otra_1'] = valor
            
            valor = obtener_valor('nuevo_valor_asegurado_otra_1', 'valor_asegurado_otra_1')
            if valor:
                self.initial['nuevo_valor_asegurado_otra_1'] = str(int(valor))
            
            valor = obtener_valor('nuevo_meses_vigencia_otra_1', 'meses_vigencia_otra_1')
            if valor:
                self.initial['nuevo_meses_vigencia_otra_1'] = valor
            
            # Fechas Otras Pólizas
            fecha_inicio = obtener_valor('nuevo_fecha_inicio_vigencia_otra_1', 'fecha_inicio_vigencia_otra_1')
            if fecha_inicio:
                self.initial['nuevo_fecha_inicio_vigencia_otra_1'] = fecha_inicio
            
            fecha_fin = obtener_valor('nuevo_fecha_fin_vigencia_otra_1', 'fecha_fin_vigencia_otra_1')
            if fecha_fin:
                self.initial['nuevo_fecha_fin_vigencia_otra_1'] = fecha_fin
            elif fecha_inicio and valor:
                from .utils import calcular_fecha_vencimiento
                self.initial['nuevo_fecha_fin_vigencia_otra_1'] = calcular_fecha_vencimiento(fecha_inicio, valor)
    
    def _limpiar_datos_post(self, data):
        """Limpia los datos POST antes de la validación"""
        campos_numericos = [
            'nuevo_valor_canon', 'nuevo_canon_minimo_garantizado',
            'nuevo_porcentaje_ventas', 'nuevos_puntos_adicionales_ipc',
            # Campos de pólizas RCE
            'nuevo_valor_asegurado_rce', 'nuevo_valor_propietario_locatario_ocupante_rce',
            'nuevo_valor_patronal_rce', 'nuevo_valor_gastos_medicos_rce',
            'nuevo_valor_vehiculos_rce', 'nuevo_valor_contratistas_rce',
            'nuevo_valor_perjuicios_extrapatrimoniales_rce', 'nuevo_valor_dano_moral_rce',
            'nuevo_valor_lucro_cesante_rce',
            # Campos de pólizas Cumplimiento
            'nuevo_valor_asegurado_cumplimiento', 'nuevo_valor_remuneraciones_cumplimiento',
            'nuevo_valor_servicios_publicos_cumplimiento', 'nuevo_valor_iva_cumplimiento',
            'nuevo_valor_otros_cumplimiento',
            # Campos RCE - Coberturas para PROVEEDOR
            'nuevo_rce_cobertura_danos_materiales', 'nuevo_rce_cobertura_lesiones_personales',
            'nuevo_rce_cobertura_muerte_terceros', 'nuevo_rce_cobertura_danos_bienes_terceros',
            'nuevo_rce_cobertura_responsabilidad_patronal', 'nuevo_rce_cobertura_responsabilidad_cruzada',
            'nuevo_rce_cobertura_danos_contratistas', 'nuevo_rce_cobertura_danos_ejecucion_contrato',
            'nuevo_rce_cobertura_danos_predios_vecinos', 'nuevo_rce_cobertura_gastos_medicos',
            'nuevo_rce_cobertura_gastos_defensa', 'nuevo_rce_cobertura_perjuicios_patrimoniales',
            # Campos Cumplimiento - Amparos para PROVEEDOR
            'nuevo_cumplimiento_amparo_cumplimiento_contrato', 'nuevo_cumplimiento_amparo_buen_manejo_anticipo',
            'nuevo_cumplimiento_amparo_amortizacion_anticipo', 'nuevo_cumplimiento_amparo_salarios_prestaciones',
            'nuevo_cumplimiento_amparo_aportes_seguridad_social', 'nuevo_cumplimiento_amparo_calidad_servicio',
            'nuevo_cumplimiento_amparo_estabilidad_obra', 'nuevo_cumplimiento_amparo_calidad_bienes',
            'nuevo_cumplimiento_amparo_multas', 'nuevo_cumplimiento_amparo_clausula_penal',
            'nuevo_cumplimiento_amparo_sanciones_incumplimiento',
            # Campos de pólizas Arrendamiento
            'nuevo_valor_asegurado_arrendamiento', 'nuevo_valor_remuneraciones_arrendamiento',
            'nuevo_valor_servicios_publicos_arrendamiento', 'nuevo_valor_iva_arrendamiento',
            'nuevo_valor_otros_arrendamiento',
            # Campos de pólizas Todo Riesgo y Otras
            'nuevo_valor_asegurado_todo_riesgo', 'nuevo_valor_asegurado_otra_1'
        ]
        return limpiar_datos_post_numericos(data, campos_numericos)
    
    def limpiar_valor_numerico(self, value, campo_nombre="campo"):
        """Función para limpiar valores numéricos con formateo"""
        try:
            return limpiar_valor_numerico(value, campo_nombre)
        except ValueError as e:
            raise forms.ValidationError(str(e))
    
    def clean_nuevo_valor_canon(self):
        """Limpia y convierte el campo nuevo_valor_canon"""
        valor = self.cleaned_data.get('nuevo_valor_canon')
        valor_limpio = self.limpiar_valor_numerico(valor)
        # Convertir a Decimal para que coincida con el modelo
        if valor_limpio is not None:
            from decimal import Decimal
            return Decimal(str(valor_limpio))
        return None
    
    def clean_nuevo_canon_minimo_garantizado(self):
        """Limpia y convierte el campo nuevo_canon_minimo_garantizado"""
        valor = self.cleaned_data.get('nuevo_canon_minimo_garantizado')
        valor_limpio = self.limpiar_valor_numerico(valor)
        if valor_limpio is not None:
            from decimal import Decimal
            return Decimal(str(valor_limpio))
        return None
    
    def clean_nuevo_porcentaje_ventas(self):
        """Limpia y convierte el campo nuevo_porcentaje_ventas"""
        valor = self.cleaned_data.get('nuevo_porcentaje_ventas')
        
        # Verificar si el campo está en los datos POST para saber si el usuario lo modificó
        campo_en_post = 'nuevo_porcentaje_ventas' in self.data
        
        # Si el campo no está en POST o está vacío, no se modificó
        if not campo_en_post or not valor:
            return None
        
        # Convertir a string y remover símbolo % si existe
        valor_str = str(valor).strip()
        if valor_str.endswith('%'):
            valor_str = valor_str[:-1].strip()
        
        if not valor_str:
            return None
        
        valor_limpio = self.limpiar_valor_numerico(valor_str, 'Nuevo % Ventas')
        if valor_limpio is not None:
            from decimal import Decimal
            valor_decimal = Decimal(str(valor_limpio))
            # Si el usuario ingresó explícitamente 0, guardarlo como 0
            # Si el valor es 0 pero no está en POST, retornar None
            return valor_decimal
        return None
    
    def clean_nuevos_puntos_adicionales_ipc(self):
        """Limpia y convierte el campo nuevos_puntos_adicionales_ipc"""
        valor = self.cleaned_data.get('nuevos_puntos_adicionales_ipc')
        
        # Verificar si el campo está en los datos POST para saber si el usuario lo modificó
        campo_en_post = 'nuevos_puntos_adicionales_ipc' in self.data
        
        # Si el campo no está en POST o está vacío, no se modificó
        if not campo_en_post or not valor:
            return None
        
        # Convertir a string y remover símbolo % si existe
        valor_str = str(valor).strip()
        if valor_str.endswith('%'):
            valor_str = valor_str[:-1].strip()
        
        if not valor_str:
            return None
        
        valor_limpio = self.limpiar_valor_numerico(valor_str, 'Nuevos Puntos Adicionales IPC')
        if valor_limpio is not None:
            from decimal import Decimal
            valor_decimal = Decimal(str(valor_limpio))
            # Si el usuario ingresó explícitamente 0, guardarlo como 0
            # Si el valor es 0 pero no está en POST, retornar None
            return valor_decimal
        return None
    
    # Métodos clean para campos de pólizas monetarios
    def _clean_campo_monetario(self, campo_nombre):
        """Método auxiliar para limpiar campos monetarios"""
        valor = self.cleaned_data.get(campo_nombre)
        valor_limpio = self.limpiar_valor_numerico(valor)
        if valor_limpio is not None:
            from decimal import Decimal
            return Decimal(str(valor_limpio))
        return None
    
    def clean_nuevo_valor_asegurado_rce(self):
        return self._clean_campo_monetario('nuevo_valor_asegurado_rce')
    
    def clean_nuevo_valor_propietario_locatario_ocupante_rce(self):
        return self._clean_campo_monetario('nuevo_valor_propietario_locatario_ocupante_rce')
    
    def clean_nuevo_valor_patronal_rce(self):
        return self._clean_campo_monetario('nuevo_valor_patronal_rce')
    
    def clean_nuevo_valor_gastos_medicos_rce(self):
        return self._clean_campo_monetario('nuevo_valor_gastos_medicos_rce')
    
    def clean_nuevo_valor_vehiculos_rce(self):
        return self._clean_campo_monetario('nuevo_valor_vehiculos_rce')
    
    def clean_nuevo_valor_contratistas_rce(self):
        return self._clean_campo_monetario('nuevo_valor_contratistas_rce')
    
    def clean_nuevo_valor_perjuicios_extrapatrimoniales_rce(self):
        return self._clean_campo_monetario('nuevo_valor_perjuicios_extrapatrimoniales_rce')
    
    def clean_nuevo_valor_dano_moral_rce(self):
        return self._clean_campo_monetario('nuevo_valor_dano_moral_rce')
    
    def clean_nuevo_valor_lucro_cesante_rce(self):
        return self._clean_campo_monetario('nuevo_valor_lucro_cesante_rce')
    
    def clean_nuevo_valor_asegurado_cumplimiento(self):
        return self._clean_campo_monetario('nuevo_valor_asegurado_cumplimiento')
    
    def clean_nuevo_valor_remuneraciones_cumplimiento(self):
        return self._clean_campo_monetario('nuevo_valor_remuneraciones_cumplimiento')
    
    def clean_nuevo_valor_servicios_publicos_cumplimiento(self):
        return self._clean_campo_monetario('nuevo_valor_servicios_publicos_cumplimiento')
    
    def clean_nuevo_valor_iva_cumplimiento(self):
        return self._clean_campo_monetario('nuevo_valor_iva_cumplimiento')
    
    def clean_nuevo_valor_otros_cumplimiento(self):
        return self._clean_campo_monetario('nuevo_valor_otros_cumplimiento')
    
    def clean_nuevo_valor_asegurado_arrendamiento(self):
        return self._clean_campo_monetario('nuevo_valor_asegurado_arrendamiento')
    
    def clean_nuevo_valor_remuneraciones_arrendamiento(self):
        return self._clean_campo_monetario('nuevo_valor_remuneraciones_arrendamiento')
    
    def clean_nuevo_valor_servicios_publicos_arrendamiento(self):
        return self._clean_campo_monetario('nuevo_valor_servicios_publicos_arrendamiento')
    
    def clean_nuevo_valor_iva_arrendamiento(self):
        return self._clean_campo_monetario('nuevo_valor_iva_arrendamiento')
    
    def clean_nuevo_valor_otros_arrendamiento(self):
        return self._clean_campo_monetario('nuevo_valor_otros_arrendamiento')
    
    # Métodos clean para campos RCE - Coberturas PROVEEDOR
    def clean_nuevo_rce_cobertura_danos_materiales(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_danos_materiales')
    
    def clean_nuevo_rce_cobertura_lesiones_personales(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_lesiones_personales')
    
    def clean_nuevo_rce_cobertura_muerte_terceros(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_muerte_terceros')
    
    def clean_nuevo_rce_cobertura_danos_bienes_terceros(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_danos_bienes_terceros')
    
    def clean_nuevo_rce_cobertura_responsabilidad_patronal(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_responsabilidad_patronal')
    
    def clean_nuevo_rce_cobertura_responsabilidad_cruzada(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_responsabilidad_cruzada')
    
    def clean_nuevo_rce_cobertura_danos_contratistas(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_danos_contratistas')
    
    def clean_nuevo_rce_cobertura_danos_ejecucion_contrato(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_danos_ejecucion_contrato')
    
    def clean_nuevo_rce_cobertura_danos_predios_vecinos(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_danos_predios_vecinos')
    
    def clean_nuevo_rce_cobertura_gastos_medicos(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_gastos_medicos')
    
    def clean_nuevo_rce_cobertura_gastos_defensa(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_gastos_defensa')
    
    def clean_nuevo_rce_cobertura_perjuicios_patrimoniales(self):
        return self._clean_campo_monetario('nuevo_rce_cobertura_perjuicios_patrimoniales')
    
    # Métodos clean para campos Cumplimiento - Amparos PROVEEDOR
    def clean_nuevo_cumplimiento_amparo_cumplimiento_contrato(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_cumplimiento_contrato')
    
    def clean_nuevo_cumplimiento_amparo_buen_manejo_anticipo(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_buen_manejo_anticipo')
    
    def clean_nuevo_cumplimiento_amparo_amortizacion_anticipo(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_amortizacion_anticipo')
    
    def clean_nuevo_cumplimiento_amparo_salarios_prestaciones(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_salarios_prestaciones')
    
    def clean_nuevo_cumplimiento_amparo_aportes_seguridad_social(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_aportes_seguridad_social')
    
    def clean_nuevo_cumplimiento_amparo_calidad_servicio(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_calidad_servicio')
    
    def clean_nuevo_cumplimiento_amparo_estabilidad_obra(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_estabilidad_obra')
    
    def clean_nuevo_cumplimiento_amparo_calidad_bienes(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_calidad_bienes')
    
    def clean_nuevo_cumplimiento_amparo_multas(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_multas')
    
    def clean_nuevo_cumplimiento_amparo_clausula_penal(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_clausula_penal')
    
    def clean_nuevo_cumplimiento_amparo_sanciones_incumplimiento(self):
        return self._clean_campo_monetario('nuevo_cumplimiento_amparo_sanciones_incumplimiento')
    
    def clean_nuevo_valor_asegurado_todo_riesgo(self):
        return self._clean_campo_monetario('nuevo_valor_asegurado_todo_riesgo')
    
    def clean_nuevo_valor_asegurado_otra_1(self):
        return self._clean_campo_monetario('nuevo_valor_asegurado_otra_1')
    
    def clean(self):
        cleaned_data = super().clean()
        effective_from = cleaned_data.get('effective_from')
        effective_to = cleaned_data.get('effective_to')
        estado = cleaned_data.get('estado')
        # Obtener contrato de la instancia (si existe) o None
        contrato = self.instance.contrato if self.instance.pk else None
        
        # Si no tenemos contrato de la instancia, usar self.contrato
        if not contrato:
            contrato = self.contrato
        
        # Validar que no se modifiquen plazos y vigencia si el contrato tiene renovación automática
        if contrato and contrato.prorroga_automatica:
            nueva_fecha_final = cleaned_data.get('nueva_fecha_final_actualizada')
            nuevo_plazo_meses = cleaned_data.get('nuevo_plazo_meses')
            
            if nueva_fecha_final is not None and nueva_fecha_final != '':
                raise forms.ValidationError(
                    'No se puede modificar la fecha final actualizada en un contrato con renovación automática. '
                    'Los ajustes de vigencia se realizan automáticamente mediante el sistema de renovaciones.'
                )
            
            if nuevo_plazo_meses is not None and nuevo_plazo_meses != '':
                raise forms.ValidationError(
                    'No se puede modificar el plazo en meses en un contrato con renovación automática. '
                    'Los ajustes de vigencia se realizan automáticamente mediante el sistema de renovaciones.'
                )
        
        # Validar que effective_from no sea futuro si está aprobado
        if estado == 'APROBADO' and effective_from:
            if effective_from > date.today():
                raise forms.ValidationError(
                    'Un Otro Sí aprobado no puede tener vigencia desde una fecha futura.'
                )
        
        # Validar que effective_to > effective_from
        if effective_from and effective_to:
            if effective_to <= effective_from:
                raise forms.ValidationError(
                    'La fecha de vigencia hasta debe ser posterior a la fecha desde.'
                )
        
        # Validar solapamiento de vigencias (solo para aprobados)
        if estado == 'APROBADO' and contrato and effective_from:
            from .utils_otrosi import validar_solapamiento_vigencias
            
            es_valido, mensaje = validar_solapamiento_vigencias(
                contrato=contrato,
                effective_from=effective_from,
                effective_to=effective_to,
                excluir_otrosi_id=self.instance.pk
            )
            
            if not es_valido:
                raise forms.ValidationError(f'Solapamiento de vigencias: {mensaje}')
        
        # Calcular fechas fin automáticamente si hay fecha inicio y meses pero no fecha fin
        from .utils import calcular_fecha_vencimiento
        
        polizas_config = [
            ('nuevo_fecha_inicio_vigencia_rce', 'nuevo_meses_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce'),
            ('nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_meses_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento'),
            ('nuevo_fecha_inicio_vigencia_arrendamiento', 'nuevo_meses_vigencia_arrendamiento', 'nuevo_fecha_fin_vigencia_arrendamiento'),
            ('nuevo_fecha_inicio_vigencia_todo_riesgo', 'nuevo_meses_vigencia_todo_riesgo', 'nuevo_fecha_fin_vigencia_todo_riesgo'),
            ('nuevo_fecha_inicio_vigencia_otra_1', 'nuevo_meses_vigencia_otra_1', 'nuevo_fecha_fin_vigencia_otra_1'),
        ]
        
        for fecha_inicio_field, meses_field, fecha_fin_field in polizas_config:
            fecha_inicio = cleaned_data.get(fecha_inicio_field)
            meses = cleaned_data.get(meses_field)
            fecha_fin = cleaned_data.get(fecha_fin_field)
            
            if fecha_inicio and meses and not fecha_fin:
                fecha_fin_calculada = calcular_fecha_vencimiento(fecha_inicio, meses)
                cleaned_data[fecha_fin_field] = fecha_fin_calculada
        
        # Validar que al menos un campo sea modificado
        campos_modificables = [
            'nuevo_valor_canon', 'nueva_modalidad_pago', 'nuevo_canon_minimo_garantizado',
            'nuevo_porcentaje_ventas', 'nuevo_tipo_condicion_ipc', 'nuevos_puntos_adicionales_ipc',
            'nueva_periodicidad_ipc', 'nueva_fecha_aumento_ipc',
            # Campos de pólizas
            'nuevo_exige_poliza_rce', 'nuevo_valor_asegurado_rce', 'nuevo_meses_vigencia_rce',
            'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
            'nuevo_exige_poliza_cumplimiento', 'nuevo_valor_asegurado_cumplimiento', 'nuevo_meses_vigencia_cumplimiento',
            'nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento',
            'nuevo_exige_poliza_arrendamiento', 'nuevo_valor_asegurado_arrendamiento', 'nuevo_meses_vigencia_arrendamiento',
            'nuevo_fecha_inicio_vigencia_arrendamiento', 'nuevo_fecha_fin_vigencia_arrendamiento',
            'nuevo_exige_poliza_todo_riesgo', 'nuevo_valor_asegurado_todo_riesgo', 'nuevo_meses_vigencia_todo_riesgo',
            'nuevo_fecha_inicio_vigencia_todo_riesgo', 'nuevo_fecha_fin_vigencia_todo_riesgo',
            'nuevo_exige_poliza_otra_1', 'nuevo_nombre_poliza_otra_1', 'nuevo_valor_asegurado_otra_1', 'nuevo_meses_vigencia_otra_1',
            'nuevo_fecha_inicio_vigencia_otra_1', 'nuevo_fecha_fin_vigencia_otra_1'
        ]
        
        # Excluir campos de vigencia si el contrato tiene renovación automática
        if not (contrato and contrato.prorroga_automatica):
            campos_modificables.extend(['nueva_fecha_final_actualizada', 'nuevo_plazo_meses'])
        
        # Verificar si hay cambios (incluyendo valores que son 0 o False)
        tiene_cambios = any(
            cleaned_data.get(campo) is not None and cleaned_data.get(campo) != '' 
            for campo in campos_modificables
        )
        tiene_modificacion_polizas = cleaned_data.get('modifica_polizas')
        tiene_clausulas = cleaned_data.get('clausulas_modificadas')
        
        if not tiene_cambios and not tiene_clausulas and not tiene_modificacion_polizas:
            raise forms.ValidationError(
                '⚠️ Debe modificar al menos un campo del contrato, especificar cláusulas modificadas, o marcar que modifica pólizas.'
            )
        
        return cleaned_data

