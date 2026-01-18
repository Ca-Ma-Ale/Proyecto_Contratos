"""
Formulario para renovación automática de contratos
"""
from django import forms
from gestion.models import (
    Contrato, RenovacionAutomatica, MESES_CHOICES,
    obtener_tipos_condicion_ipc_choices, obtener_periodicidades_ipc_choices
)
from datetime import date
from gestion.utils_formateo import limpiar_valor_numerico, limpiar_datos_post_numericos
from gestion.forms import BaseModelForm


class DateInputHTML5(forms.DateInput):
    """Widget personalizado para campos de fecha HTML5"""
    input_type = 'date'
    
    def format_value(self, value):
        if value is None:
            return ''
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, str):
            if len(value) == 10 and value[4] == '-' and value[7] == '-':
                return value
            try:
                from datetime import datetime
                if '/' in value:
                    parts = value.split('/')
                    if len(parts) == 3:
                        d = datetime.strptime(value, '%d/%m/%Y')
                        return d.strftime('%Y-%m-%d')
            except:
                pass
        return super().format_value(value) if hasattr(super(), 'format_value') else value


class RenovacionAutomaticaForm(BaseModelForm):
    """Formulario para crear/editar renovación automática con condiciones de pólizas"""
    
    usar_duracion_inicial = forms.ChoiceField(
        choices=[('si', 'Sí'), ('no', 'No')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='¿Renovar por el mismo tiempo inicial?',
        initial='si',
        required=False
    )
    
    modifica_polizas = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='¿Modifica condiciones de pólizas?'
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
    
    def __init__(self, *args, **kwargs):
        self.contrato = kwargs.pop('contrato', None)
        self.contrato_id = kwargs.pop('contrato_id', None)
        
        if not self.contrato and self.contrato_id:
            try:
                self.contrato = Contrato.objects.get(id=self.contrato_id)
            except Contrato.DoesNotExist:
                self.contrato = None
        
        if 'data' in kwargs and kwargs['data']:
            data = kwargs['data'].copy()
            self._limpiar_datos_post(data)
            kwargs['data'] = data
        
        super().__init__(*args, **kwargs)
        
        if 'numero_renovacion' in self.fields:
            self.fields['numero_renovacion'].required = False
            self.fields['numero_renovacion'].disabled = True
        
        # Hacer que estos campos no sean requeridos en el formulario
        # Se establecen en la vista antes de guardar
        campos_establecidos_en_vista = [
            'estado', 'fecha_renovacion', 'effective_from', 
            'fecha_inicio_nueva_vigencia', 'fecha_final_anterior'
        ]
        for campo in campos_establecidos_en_vista:
            if campo in self.fields:
                self.fields[campo].required = False
        
        # Inicializar campos solo cuando se crea (no cuando se edita)
        if not self.instance.pk:
            from datetime import date
            if 'fecha_renovacion' in self.fields:
                self.fields['fecha_renovacion'].initial = date.today()
            if 'effective_from' in self.fields:
                self.fields['effective_from'].initial = date.today()
            if 'estado' in self.fields:
                self.fields['estado'].initial = 'BORRADOR'
        
        fecha_fields = [
            'fecha_renovacion', 'effective_from', 'effective_to',
            'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
            'nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento',
            'nuevo_fecha_inicio_vigencia_arrendamiento', 'nuevo_fecha_fin_vigencia_arrendamiento',
            'nuevo_fecha_inicio_vigencia_todo_riesgo', 'nuevo_fecha_fin_vigencia_todo_riesgo',
            'nuevo_fecha_inicio_vigencia_otra_1', 'nuevo_fecha_fin_vigencia_otra_1'
        ]
        for field_name in fecha_fields:
            if field_name in self.fields:
                self.fields[field_name].input_formats = ['%Y-%m-%d']
        
        campos_opcionales = [
            'meses_renovacion', 'descripcion', 'observaciones',
            'nuevo_valor_asegurado_rce', 'nuevo_valor_propietario_locatario_ocupante_rce',
            'nuevo_valor_patronal_rce', 'nuevo_valor_gastos_medicos_rce',
            'nuevo_valor_vehiculos_rce', 'nuevo_valor_contratistas_rce',
            'nuevo_valor_perjuicios_extrapatrimoniales_rce', 'nuevo_valor_dano_moral_rce',
            'nuevo_valor_lucro_cesante_rce', 'nuevo_meses_vigencia_rce',
            'nuevo_fecha_inicio_vigencia_rce', 'nuevo_fecha_fin_vigencia_rce',
            'nuevo_rce_cobertura_danos_materiales', 'nuevo_rce_cobertura_lesiones_personales',
            'nuevo_rce_cobertura_muerte_terceros', 'nuevo_rce_cobertura_danos_bienes_terceros',
            'nuevo_rce_cobertura_responsabilidad_patronal', 'nuevo_rce_cobertura_responsabilidad_cruzada',
            'nuevo_rce_cobertura_danos_contratistas', 'nuevo_rce_cobertura_danos_ejecucion_contrato',
            'nuevo_rce_cobertura_danos_predios_vecinos', 'nuevo_rce_cobertura_gastos_medicos',
            'nuevo_rce_cobertura_gastos_defensa', 'nuevo_rce_cobertura_perjuicios_patrimoniales',
            'nuevo_valor_asegurado_cumplimiento', 'nuevo_valor_remuneraciones_cumplimiento',
            'nuevo_valor_servicios_publicos_cumplimiento', 'nuevo_valor_iva_cumplimiento',
            'nuevo_valor_otros_cumplimiento', 'nuevo_meses_vigencia_cumplimiento',
            'nuevo_fecha_inicio_vigencia_cumplimiento', 'nuevo_fecha_fin_vigencia_cumplimiento',
            'nuevo_cumplimiento_amparo_cumplimiento_contrato', 'nuevo_cumplimiento_amparo_buen_manejo_anticipo',
            'nuevo_cumplimiento_amparo_amortizacion_anticipo', 'nuevo_cumplimiento_amparo_salarios_prestaciones',
            'nuevo_cumplimiento_amparo_aportes_seguridad_social', 'nuevo_cumplimiento_amparo_calidad_servicio',
            'nuevo_cumplimiento_amparo_estabilidad_obra', 'nuevo_cumplimiento_amparo_calidad_bienes',
            'nuevo_cumplimiento_amparo_multas', 'nuevo_cumplimiento_amparo_clausula_penal',
            'nuevo_cumplimiento_amparo_sanciones_incumplimiento',
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
    
    def _limpiar_datos_post(self, data):
        """Limpia los datos POST antes de la validación"""
        campos_numericos = [
            'nuevo_valor_asegurado_rce', 'nuevo_valor_propietario_locatario_ocupante_rce',
            'nuevo_valor_patronal_rce', 'nuevo_valor_gastos_medicos_rce',
            'nuevo_valor_vehiculos_rce', 'nuevo_valor_contratistas_rce',
            'nuevo_valor_perjuicios_extrapatrimoniales_rce', 'nuevo_valor_dano_moral_rce',
            'nuevo_valor_lucro_cesante_rce',
            'nuevo_rce_cobertura_danos_materiales', 'nuevo_rce_cobertura_lesiones_personales',
            'nuevo_rce_cobertura_muerte_terceros', 'nuevo_rce_cobertura_danos_bienes_terceros',
            'nuevo_rce_cobertura_responsabilidad_patronal', 'nuevo_rce_cobertura_responsabilidad_cruzada',
            'nuevo_rce_cobertura_danos_contratistas', 'nuevo_rce_cobertura_danos_ejecucion_contrato',
            'nuevo_rce_cobertura_danos_predios_vecinos', 'nuevo_rce_cobertura_gastos_medicos',
            'nuevo_rce_cobertura_gastos_defensa', 'nuevo_rce_cobertura_perjuicios_patrimoniales',
            'nuevo_valor_asegurado_cumplimiento', 'nuevo_valor_remuneraciones_cumplimiento',
            'nuevo_valor_servicios_publicos_cumplimiento', 'nuevo_valor_iva_cumplimiento',
            'nuevo_valor_otros_cumplimiento',
            'nuevo_cumplimiento_amparo_cumplimiento_contrato', 'nuevo_cumplimiento_amparo_buen_manejo_anticipo',
            'nuevo_cumplimiento_amparo_amortizacion_anticipo', 'nuevo_cumplimiento_amparo_salarios_prestaciones',
            'nuevo_cumplimiento_amparo_aportes_seguridad_social', 'nuevo_cumplimiento_amparo_calidad_servicio',
            'nuevo_cumplimiento_amparo_estabilidad_obra', 'nuevo_cumplimiento_amparo_calidad_bienes',
            'nuevo_cumplimiento_amparo_multas', 'nuevo_cumplimiento_amparo_clausula_penal',
            'nuevo_cumplimiento_amparo_sanciones_incumplimiento',
            'nuevo_valor_asegurado_arrendamiento', 'nuevo_valor_remuneraciones_arrendamiento',
            'nuevo_valor_servicios_publicos_arrendamiento', 'nuevo_valor_iva_arrendamiento',
            'nuevo_valor_otros_arrendamiento',
            'nuevo_valor_asegurado_todo_riesgo', 'nuevo_valor_asegurado_otra_1'
        ]
        return limpiar_datos_post_numericos(data, campos_numericos)
    
    def limpiar_valor_numerico(self, value, campo_nombre="campo"):
        """Función para limpiar valores numéricos con formateo"""
        try:
            return limpiar_valor_numerico(value, campo_nombre)
        except ValueError as e:
            raise forms.ValidationError(str(e))
    
    def _clean_campo_monetario(self, campo_nombre):
        """Método auxiliar para limpiar campos monetarios"""
        valor = self.cleaned_data.get(campo_nombre)
        if not valor:
            return None
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
    
    def clean_nuevo_valor_asegurado_todo_riesgo(self):
        return self._clean_campo_monetario('nuevo_valor_asegurado_todo_riesgo')
    
    def clean_nuevo_valor_asegurado_otra_1(self):
        return self._clean_campo_monetario('nuevo_valor_asegurado_otra_1')
    
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
    
    def clean_numero_renovacion(self):
        """Forzar número automático: ignorar cualquier valor enviado."""
        if self.instance and self.instance.pk:
            return self.instance.numero_renovacion
        return None
    
    def clean(self):
        cleaned_data = super().clean()
        usar_duracion_inicial = cleaned_data.get('usar_duracion_inicial')
        meses_renovacion = cleaned_data.get('meses_renovacion')
        
        if not self.instance.pk:
            if usar_duracion_inicial == 'no' and not meses_renovacion:
                raise forms.ValidationError({
                    'meses_renovacion': 'Debe especificar el número de meses para la renovación cuando no usa la duración inicial.'
                })
            
            if meses_renovacion and meses_renovacion <= 0:
                raise forms.ValidationError({
                    'meses_renovacion': 'El número de meses debe ser mayor a cero.'
                })
        
        from gestion.utils import calcular_fecha_vencimiento
        
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
        
        return cleaned_data
    
    class Meta:
        model = RenovacionAutomatica
        exclude = [
            'contrato', 'creado_por', 'fecha_creacion', 'aprobado_por', 'fecha_aprobacion', 
            'modificado_por', 'fecha_modificacion', 'anulado_por', 'fecha_anulacion', 'version',
            'fecha_inicio_nueva_vigencia', 'fecha_final_anterior', 'usar_duracion_inicial',
            'estado', 'fecha_renovacion', 'effective_from'
        ]
        widgets = {
            'fecha_renovacion': DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'effective_from': DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'effective_to': DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'nueva_fecha_final_actualizada': DateInputHTML5(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'numero_renovacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Se genera automáticamente', 'readonly': 'readonly'}),
            'meses_renovacion': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

