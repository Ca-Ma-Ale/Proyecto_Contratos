from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from datetime import date

from gestion.utils import calcular_fecha_vencimiento


class AuditoriaMixin(models.Model):
    """
    Mixin para agregar campos de auditoría a los modelos.
    Registra quién creó, modificó y eliminó el registro, y cuándo.
    """
    creado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Creado Por',
        help_text='Usuario que creó el registro'
    )
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Creación',
        help_text='Fecha y hora de creación del registro'
    )
    modificado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Modificado Por',
        help_text='Usuario que realizó la última modificación'
    )
    fecha_modificacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Modificación',
        help_text='Fecha y hora de la última modificación'
    )
    eliminado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Eliminado Por',
        help_text='Usuario que eliminó el registro'
    )
    fecha_eliminacion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Eliminación',
        help_text='Fecha y hora de eliminación del registro'
    )

    class Meta:
        abstract = True

# Constantes globales para opciones de formularios
# Constantes hardcodeadas para compatibilidad (deprecated - usar modelos en BD)
TIPO_CONDICION_IPC_CHOICES = [
    ('IPC', 'IPC'),
    ('SALARIO_MINIMO', 'Porcentaje Salario Mínimo'),
]

PERIODICIDAD_IPC_CHOICES = [
    ('ANUAL', 'Anual'),
    ('FECHA_ESPECIFICA', 'Fecha Específica'),
]


# Funciones helper para obtener opciones desde la BD
def obtener_tipos_condicion_ipc_choices():
    """
    Obtiene las opciones de tipos de condición IPC desde la base de datos.
    Retorna una lista de tuplas (codigo, nombre) para usar en choices.
    """
    try:
        # Importar aquí para evitar problemas de importación circular
        # Los modelos se definen más adelante en el archivo
        tipos = TipoCondicionIPC.objects.filter(activo=True).order_by('orden', 'nombre')
        return [(tipo.codigo, tipo.nombre) for tipo in tipos]
    except (NameError, Exception):
        # Fallback a constantes si hay error (migración no aplicada, etc.)
        return TIPO_CONDICION_IPC_CHOICES


def obtener_periodicidades_ipc_choices():
    """
    Obtiene las opciones de periodicidades IPC desde la base de datos.
    Retorna una lista de tuplas (codigo, nombre) para usar en choices.
    """
    try:
        # Importar aquí para evitar problemas de importación circular
        from .models import PeriodicidadIPC
        periodicidades = PeriodicidadIPC.objects.filter(activo=True).order_by('orden', 'nombre')
        return [(p.codigo, p.nombre) for p in periodicidades]
    except Exception:
        # Fallback a constantes si hay error (migración no aplicada, etc.)
        return PERIODICIDAD_IPC_CHOICES


def obtener_nombre_tipo_condicion_ipc(codigo):
    """Obtiene el nombre de un tipo de condición IPC desde la BD"""
    if not codigo:
        return None
    try:
        # Importar aquí para evitar problemas de importación circular
        from .models import TipoCondicionIPC
        tipo = TipoCondicionIPC.objects.get(codigo=codigo, activo=True)
        return tipo.nombre
    except (TipoCondicionIPC.DoesNotExist, Exception):
        # Fallback a constantes
        return dict(TIPO_CONDICION_IPC_CHOICES).get(codigo, codigo)


def obtener_nombre_periodicidad_ipc(codigo):
    """Obtiene el nombre de una periodicidad IPC desde la BD"""
    if not codigo:
        return None
    try:
        # Importar aquí para evitar problemas de importación circular
        from .models import PeriodicidadIPC
        periodicidad = PeriodicidadIPC.objects.get(codigo=codigo, activo=True)
        return periodicidad.nombre
    except (PeriodicidadIPC.DoesNotExist, Exception):
        # Fallback a constantes
        return dict(PERIODICIDAD_IPC_CHOICES).get(codigo, codigo)

MESES_CHOICES = [
    ('ENERO', 'Enero'),
    ('FEBRERO', 'Febrero'),
    ('MARZO', 'Marzo'),
    ('ABRIL', 'Abril'),
    ('MAYO', 'Mayo'),
    ('JUNIO', 'Junio'),
    ('JULIO', 'Julio'),
    ('AGOSTO', 'Agosto'),
    ('SEPTIEMBRE', 'Septiembre'),
    ('OCTUBRE', 'Octubre'),
    ('NOVIEMBRE', 'Noviembre'),
    ('DICIEMBRE', 'Diciembre'),
]

# Constantes globales para tipos de pólizas (consolidadas)
POLIZA_TIPO_CHOICES = [
    ('Cumplimiento', 'Cumplimiento'),
    ('Poliza de Arrendamiento', 'Póliza de Arrendamiento'),
    ('RCE - Responsabilidad Civil', 'RCE - Responsabilidad Civil'),
    ('Arrendamiento', 'Arrendamiento'),
    ('Otra', 'Otra'),
]

POLIZA_ESTADO_CHOICES = [
    ('Aporte inicial', 'Aporte inicial'),
    ('Actualización', 'Actualización'),
    ('Prórroga', 'Prórroga'),
]


class PolizaMixin:
    """
    Mixin con métodos comunes para modelos de pólizas.
    Requiere que el modelo tenga un campo 'fecha_vencimiento'.
    """
    
    def obtener_estado_vigencia(self):
        """Retorna el estado de vigencia de la póliza usando la fecha efectiva"""
        fecha_efectiva = self.obtener_fecha_vencimiento_efectiva()
        if fecha_efectiva < date.today():
            return 'Vencida'
        else:
            return 'Vigente'
    
    def obtener_dias_para_vencer(self):
        """Retorna los días que faltan para que venza la póliza (puede ser negativo si ya venció)
        Usa la fecha de vencimiento efectiva (considerando colchón si aplica)"""
        fecha_efectiva = self.obtener_fecha_vencimiento_efectiva()
        diferencia = (fecha_efectiva - date.today()).days
        return diferencia
    
    def obtener_estado_legible(self):
        """Retorna un texto legible del estado de la póliza usando la fecha efectiva"""
        dias = self.obtener_dias_para_vencer()
        if dias < 0:
            return f'Vencida hace {abs(dias)} días'
        elif dias == 0:
            return 'Vence hoy'
        elif dias <= 30:
            return f'Vigente - Vence en {dias} días'
        else:
            return f'Vigente - Vence en {dias} días'


class ConfiguracionEmpresa(AuditoriaMixin):
    """Configuración de la empresa que usa el sistema"""
    nombre_empresa = models.CharField(max_length=200, verbose_name='Nombre de la Empresa')
    nit_empresa = models.CharField(max_length=20, verbose_name='NIT de la Empresa')
    representante_legal = models.CharField(max_length=100, verbose_name='Representante Legal')
    direccion = models.TextField(blank=True, null=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    activo = models.BooleanField(default=True, verbose_name='Configuración Activa')
    
    class Meta:
        verbose_name = 'Configuración de Empresa'
        verbose_name_plural = 'Configuraciones de Empresa'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return self.nombre_empresa
    
    def save(self, *args, **kwargs):
        # Solo permitir una configuración activa
        if self.activo:
            ConfiguracionEmpresa.objects.filter(activo=True).update(activo=False)
        super().save(*args, **kwargs)


class Tercero(AuditoriaMixin):
    TIPO_CHOICES = [
        ('ARRENDATARIO', 'Arrendatario'),
        ('PROVEEDOR', 'Proveedor'),
    ]
    
    nit = models.CharField(max_length=20, verbose_name='NIT')
    razon_social = models.CharField(max_length=200, verbose_name='Razón Social')
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='ARRENDATARIO',
        verbose_name='Tipo de Tercero'
    )
    nombre_rep_legal = models.CharField(max_length=100, verbose_name='Nombre Representante Legal')
    nombre_supervisor_op = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nombre Supervisor Operativo')
    email_supervisor_op = models.EmailField(max_length=254, blank=True, null=True, verbose_name='Email Supervisor Operativo')

    class Meta:
        verbose_name = 'Tercero'
        verbose_name_plural = 'Terceros'
        ordering = ['razon_social']
        constraints = [
            models.UniqueConstraint(fields=['nit', 'tipo'], name='unique_nit_por_tipo')
        ]

    def __str__(self):
        return self.razon_social

# Alias para compatibilidad hacia atrás
Arrendatario = Tercero


class Local(AuditoriaMixin):
    nombre_comercial_stand = models.CharField(max_length=100, unique=True, verbose_name='Nombre Comercial/Stand')
    ubicacion = models.CharField(max_length=200, default='No especificada', verbose_name='Ubicación', help_text='Ejemplo: Primer Piso, Sector A, Corredor Norte')
    total_area_m2 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Área Total (m²)')

    class Meta:
        verbose_name = 'Local'
        verbose_name_plural = 'Locales'
        ordering = ['nombre_comercial_stand']

    def __str__(self):
        return self.nombre_comercial_stand


class TipoContrato(AuditoriaMixin):
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre Tipo de Contrato')

    class Meta:
        verbose_name = 'Tipo de Contrato'
        verbose_name_plural = 'Tipos de Contrato'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


class TipoServicio(AuditoriaMixin):
    """Tipos de servicios para contratos de proveedores (Mantenimiento, Seguridad, Aseo, Tecnología, etc.)"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre Tipo de Servicio')

    class Meta:
        verbose_name = 'Tipo de Servicio'
        verbose_name_plural = 'Tipos de Servicio'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


class Contrato(models.Model):
    MODALIDAD_CHOICES = [
        ('Fijo', 'Fijo'),
        ('Variable Puro', 'Variable Puro'),
        ('Hibrido (Min Garantizado)', 'Híbrido (Min Garantizado)'),
    ]
    
    TIPO_CONTRATO_CHOICES = [
        ('CLIENTE', 'Cliente'),
        ('PROVEEDOR', 'Proveedor'),
    ]

    # Datos Generales del Contrato
    num_contrato = models.CharField(max_length=50, unique=True, verbose_name='Número de Contrato')
    tipo_contrato_cliente_proveedor = models.CharField(
        max_length=20,
        choices=TIPO_CONTRATO_CHOICES,
        default='CLIENTE',
        verbose_name='Tipo de Contrato'
    )
    objeto_destinacion = models.TextField(verbose_name='Objeto y Destinación')
    tipo_contrato = models.ForeignKey(TipoContrato, on_delete=models.PROTECT, related_name='contratos', blank=True, null=True, verbose_name='Tipo de Contrato (Cliente)')
    tipo_servicio = models.ForeignKey('TipoServicio', on_delete=models.PROTECT, related_name='contratos', blank=True, null=True, verbose_name='Tipo de Servicio (Proveedor)')
    
    # Partes Involucradas
    nit_concedente = models.CharField(max_length=20, verbose_name='NIT Concedente')
    rep_legal_concedente = models.CharField(max_length=100, verbose_name='Representante Legal Concedente')
    marca_comercial = models.CharField(max_length=100, blank=True, null=True, verbose_name='Marca Comercial')
    supervisor_concedente = models.CharField(max_length=100, blank=True, null=True, verbose_name='Supervisor Concedente')
    supervisor_contraparte = models.CharField(max_length=100, blank=True, null=True, verbose_name='Supervisor Contraparte')
    
    # Vigencia y Plazos
    fecha_firma = models.DateField(verbose_name='Fecha de Firma')
    duracion_inicial_meses = models.IntegerField(default=12, verbose_name='Duración Inicial (Meses)')
    fecha_inicial_contrato = models.DateField(verbose_name='Fecha Inicial del Contrato')
    fecha_final_inicial = models.DateField(verbose_name='Fecha Final Inicial')
    fecha_final_actualizada = models.DateField(blank=True, null=True, verbose_name='Fecha Final Actualizada')
    prorroga_automatica = models.BooleanField(default=False, verbose_name='Prórroga Automática')
    dias_preaviso_no_renovacion = models.IntegerField(default=60, verbose_name='Días Preaviso No Renovación')
    dias_terminacion_anticipada = models.IntegerField(
        default=60,
        validators=[MinValueValidator(0)],
        verbose_name='Terminación Anticipada (Días)'
    )
    vigente = models.BooleanField(default=True, verbose_name='Vigente')
    
    # Campos para renovación automática
    ultima_renovacion_automatica_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Última Renovación Automática Por',
        help_text='Usuario que aprobó la última renovación automática'
    )
    fecha_ultima_renovacion_automatica = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha Última Renovación Automática',
        help_text='Fecha y hora de la última renovación automática aprobada'
    )
    total_renovaciones_automaticas = models.IntegerField(
        default=0,
        verbose_name='Total Renovaciones Automáticas',
        help_text='Número total de renovaciones automáticas realizadas'
    )
    
    # Condiciones Financieras (se manejarán en módulo separado)
    modalidad_pago = models.CharField(max_length=30, choices=MODALIDAD_CHOICES, blank=True, null=True, verbose_name='Modalidad de Pago')
    valor_canon_fijo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Valor Canon Fijo')
    canon_minimo_garantizado = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Canon Mínimo Garantizado')
    porcentaje_ventas = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Porcentaje de Ventas (%)')
    reporta_ventas = models.BooleanField(default=False, verbose_name='Reporta Ventas')
    dia_limite_reporte_ventas = models.IntegerField(blank=True, null=True, verbose_name='Día Límite Reporte de Ventas')
    cobra_servicios_publicos_aparte = models.BooleanField(default=False, verbose_name='Cobra Servicios Públicos Aparte')
    tiene_clausula_sarlaft = models.BooleanField(default=False, verbose_name='Tiene Cláusula SARLAFT')
    tiene_clausula_proteccion_datos = models.BooleanField(default=False, verbose_name='Tiene Cláusula de Protección de Datos')
    cobro_administracion = models.BooleanField(default=False, verbose_name='Cobro Administración')
    interes_mora_pagos = models.CharField(max_length=255, blank=True, null=True, verbose_name='Interés de Mora por Pagos')
    
    # Condiciones IPC
    tipo_condicion_ipc = models.CharField(
        max_length=20, 
        choices=TIPO_CONDICION_IPC_CHOICES,  # Mantener para migraciones, pero usar obtener_tipos_condicion_ipc_choices() en formularios
        blank=True, 
        null=True, 
        verbose_name='Tipo de Condición IPC'
    )
    puntos_adicionales_ipc = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Puntos Adicionales')
    porcentaje_salario_minimo = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        default=0,
        verbose_name='Porcentaje Salario Mínimo (%)',
        help_text='Porcentaje del Salario Mínimo Legal Vigente a aplicar (solo para contratos con tipo SALARIO_MINIMO)'
    )
    periodicidad_ipc = models.CharField(
        max_length=20, 
        choices=PERIODICIDAD_IPC_CHOICES,  # Mantener para migraciones, pero usar obtener_periodicidades_ipc_choices() en formularios
        blank=True, 
        null=True, 
        verbose_name='Periodicidad Ajuste'
    )
    fecha_aumento_ipc = models.DateField(blank=True, null=True, verbose_name='Fecha de Aumento IPC', help_text='Fecha exacta en que se aplica el ajuste por IPC (ej: si el contrato inicia el 15 de junio, el ajuste será el 15 de junio de cada año)')
    
    # Periodos Especiales
    tiene_periodo_gracia = models.BooleanField(default=False, verbose_name='Tiene Periodo de Gracia')
    fecha_inicio_periodo_gracia = models.DateField(blank=True, null=True, verbose_name='Fecha Inicio Periodo de Gracia')
    fecha_fin_periodo_gracia = models.DateField(blank=True, null=True, verbose_name='Fecha Fin Periodo de Gracia')
    condicion_gracia = models.TextField(blank=True, null=True, verbose_name='Condición de Gracia')
    
    # --- REQUERIMIENTOS DE PÓLIZAS (Enfoque Fijo) ---
    
    # Póliza RCE
    exige_poliza_rce = models.BooleanField(default=False, verbose_name="¿Exige Póliza RCE?")
    valor_asegurado_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Valor Asegurado RCE")
    valor_propietario_locatario_ocupante_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="PLO (Propietario, Locatario y Ocupante) Asegurado")
    valor_patronal_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Patronal Asegurado")
    valor_gastos_medicos_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Gastos Médicos de Terceros Asegurados")
    valor_vehiculos_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Vehículos Propios y No Propios Asegurados")
    valor_contratistas_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Contratistas y Subcontratistas Asegurados")
    valor_perjuicios_extrapatrimoniales_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Perjuicios Extrapatrimoniales Asegurados")
    valor_dano_moral_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daño Moral Asegurado")
    valor_lucro_cesante_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Lucro Cesante Asegurado")
    meses_vigencia_rce = models.IntegerField(null=True, blank=True, verbose_name="Meses de Vigencia RCE")
    fecha_inicio_vigencia_rce = models.DateField(null=True, blank=True, verbose_name="Fecha Inicio Vigencia RCE")
    fecha_fin_vigencia_rce = models.DateField(null=True, blank=True, verbose_name="Fecha Fin Vigencia RCE")
    
    # Póliza RCE - Coberturas (solo para PROVEEDOR)
    rce_cobertura_danos_materiales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños materiales a terceros")
    rce_cobertura_lesiones_personales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Lesiones personales a terceros")
    rce_cobertura_muerte_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Muerte de terceros")
    rce_cobertura_danos_bienes_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños a bienes de terceros")
    rce_cobertura_responsabilidad_patronal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Responsabilidad patronal (si aplica)")
    rce_cobertura_responsabilidad_cruzada = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Responsabilidad cruzada (si aplica)")
    rce_cobertura_danos_contratistas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños causados por contratistas y subcontratistas (si aplica)")
    rce_cobertura_danos_ejecucion_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños durante la ejecución del contrato")
    rce_cobertura_danos_predios_vecinos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños en predios vecinos (si aplica)")
    rce_cobertura_gastos_medicos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Gastos médicos (si aplica)")
    rce_cobertura_gastos_defensa = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Gastos de defensa (si aplica)")
    rce_cobertura_perjuicios_patrimoniales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Perjuicios patrimoniales consecuenciales (si aplica)")
    
    # Póliza Cumplimiento
    exige_poliza_cumplimiento = models.BooleanField(default=False, verbose_name="¿Exige Póliza de Cumplimiento?")
    valor_asegurado_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Valor Asegurado Cumplimiento")
    valor_remuneraciones_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Remuneraciones Mensuales Aseguradas (Cumplimiento)")
    valor_servicios_publicos_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Servicios Públicos Asegurados (Cumplimiento)")
    valor_iva_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="IVA Asegurado (Cumplimiento)")
    valor_otros_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Cuota de Administración Asegurada (Cumplimiento)")
    meses_vigencia_cumplimiento = models.IntegerField(null=True, blank=True, verbose_name="Meses de Vigencia Cumplimiento")
    fecha_inicio_vigencia_cumplimiento = models.DateField(null=True, blank=True, verbose_name="Fecha Inicio Vigencia Cumplimiento")
    fecha_fin_vigencia_cumplimiento = models.DateField(null=True, blank=True, verbose_name="Fecha Fin Vigencia Cumplimiento")
    
    # Póliza de Cumplimiento - Amparos (solo para PROVEEDOR)
    cumplimiento_amparo_cumplimiento_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Cumplimiento del contrato")
    cumplimiento_amparo_buen_manejo_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Buen manejo y correcta inversión del anticipo (si aplica)")
    cumplimiento_amparo_amortizacion_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Correcta amortización del anticipo (si aplica)")
    cumplimiento_amparo_salarios_prestaciones = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Salarios, prestaciones sociales e indemnizaciones laborales")
    cumplimiento_amparo_aportes_seguridad_social = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Aportes al sistema de seguridad social")
    cumplimiento_amparo_calidad_servicio = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Calidad del servicio")
    cumplimiento_amparo_estabilidad_obra = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Estabilidad de la obra (si aplica)")
    cumplimiento_amparo_calidad_bienes = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Calidad y correcto funcionamiento de bienes (si aplica)")
    cumplimiento_amparo_multas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Multas (si aplica)")
    cumplimiento_amparo_clausula_penal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Cláusula penal pecuniaria (si aplica)")
    cumplimiento_amparo_sanciones_incumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Sanciones por incumplimiento (si aplica)")
    
    # Póliza de Arrendamiento
    exige_poliza_arrendamiento = models.BooleanField(default=False, verbose_name="¿Exige Póliza de Arrendamiento?")
    valor_asegurado_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Valor Asegurado Póliza de Arrendamiento")
    valor_remuneraciones_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Remuneraciones Mensuales Aseguradas (Arrendamiento)")
    valor_servicios_publicos_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Servicios Públicos Asegurados (Arrendamiento)")
    valor_iva_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="IVA Asegurado (Arrendamiento)")
    valor_otros_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Cuota de Administración Asegurada (Arrendamiento)")
    meses_vigencia_arrendamiento = models.IntegerField(null=True, blank=True, verbose_name="Meses de Vigencia Póliza de Arrendamiento")
    fecha_inicio_vigencia_arrendamiento = models.DateField(null=True, blank=True, verbose_name="Fecha Inicio Vigencia Póliza de Arrendamiento")
    fecha_fin_vigencia_arrendamiento = models.DateField(null=True, blank=True, verbose_name="Fecha Fin Vigencia Póliza de Arrendamiento")
    
    # Póliza Todo Riesgo
    exige_poliza_todo_riesgo = models.BooleanField(default=False, verbose_name="¿Exige Póliza Todo Riesgo?")
    valor_asegurado_todo_riesgo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Valor Asegurado Todo Riesgo")
    meses_vigencia_todo_riesgo = models.IntegerField(null=True, blank=True, verbose_name="Meses de Vigencia Todo Riesgo")
    fecha_inicio_vigencia_todo_riesgo = models.DateField(null=True, blank=True, verbose_name="Fecha Inicio Vigencia Todo Riesgo")
    fecha_fin_vigencia_todo_riesgo = models.DateField(null=True, blank=True, verbose_name="Fecha Fin Vigencia Todo Riesgo")
    
    # Otras Pólizas (Opcional)
    exige_poliza_otra_1 = models.BooleanField(default=False, verbose_name="¿Exige Otras Pólizas?")
    nombre_poliza_otra_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Nombre Otras Pólizas")
    valor_asegurado_otra_1 = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Valor Asegurado Otras Pólizas")
    meses_vigencia_otra_1 = models.IntegerField(null=True, blank=True, verbose_name="Meses de Vigencia Otras Pólizas")
    fecha_inicio_vigencia_otra_1 = models.DateField(null=True, blank=True, verbose_name="Fecha Inicio Vigencia Otras Pólizas")
    fecha_fin_vigencia_otra_1 = models.DateField(null=True, blank=True, verbose_name="Fecha Fin Vigencia Otras Pólizas")
    
    # Sanciones y Penalidades
    clausula_penal_incumplimiento = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Cláusula Penal por Incumplimiento')
    penalidad_terminacion_anticipada = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Penalidad por Terminación Anticipada')
    multa_mora_no_restitucion = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='Multa por Mora en No Restitución')
    
    # Relaciones
    arrendatario = models.ForeignKey('Tercero', on_delete=models.CASCADE, related_name='contratos_arrendatario', blank=True, null=True, verbose_name='Arrendatario')
    proveedor = models.ForeignKey('Tercero', on_delete=models.CASCADE, related_name='contratos_proveedor', blank=True, null=True, verbose_name='Proveedor')
    local = models.ForeignKey(Local, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Local')
    
    # Auditoría
    creado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Creado Por',
        help_text='Usuario que creó el contrato'
    )
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Creación',
        help_text='Fecha y hora de creación del contrato'
    )
    modificado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Modificado Por',
        help_text='Usuario que realizó la última modificación'
    )
    fecha_modificacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Modificación',
        help_text='Fecha y hora de la última modificación'
    )
    eliminado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Eliminado Por',
        help_text='Usuario que eliminó el contrato'
    )
    fecha_eliminacion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Eliminación',
        help_text='Fecha y hora de eliminación del contrato'
    )
    url_archivo = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='URL del Archivo Digital',
        help_text='Enlace al archivo digital del contrato (OneDrive, Google Drive, etc.)'
    )

    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        ordering = ['-fecha_inicial_contrato']

    def __str__(self):
        return self.num_contrato
    
    def obtener_tercero(self):
        """Retorna el tercero asociado al contrato (arrendatario o proveedor)"""
        if self.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
            return self.proveedor
        return self.arrendatario
    
    def obtener_nombre_tercero(self):
        """Retorna el nombre del tercero asociado al contrato"""
        tercero = self.obtener_tercero()
        return tercero.razon_social if tercero else 'Sin tercero asignado'
    
    @property
    def total_renovaciones_automaticas_activas(self):
        """Retorna el total de renovaciones automáticas existentes (no eliminadas)"""
        return self.renovaciones_automaticas.count()
    
    def calcular_fechas_polizas(self):
        """Calcula automáticamente las fechas de vigencia de las pólizas basándose en la fecha de inicio del contrato"""
        
        # Póliza RCE
        if self.exige_poliza_rce and self.meses_vigencia_rce:
            self.fecha_inicio_vigencia_rce = self.fecha_inicial_contrato
            self.fecha_fin_vigencia_rce = calcular_fecha_vencimiento(self.fecha_inicial_contrato, self.meses_vigencia_rce)
        
        # Póliza Cumplimiento
        if self.exige_poliza_cumplimiento and self.meses_vigencia_cumplimiento:
            self.fecha_inicio_vigencia_cumplimiento = self.fecha_inicial_contrato
            self.fecha_fin_vigencia_cumplimiento = calcular_fecha_vencimiento(self.fecha_inicial_contrato, self.meses_vigencia_cumplimiento)
        
        # Póliza de Arrendamiento
        if self.exige_poliza_arrendamiento and self.meses_vigencia_arrendamiento:
            self.fecha_inicio_vigencia_arrendamiento = self.fecha_inicial_contrato
            self.fecha_fin_vigencia_arrendamiento = calcular_fecha_vencimiento(self.fecha_inicial_contrato, self.meses_vigencia_arrendamiento)
        
        # Póliza Todo Riesgo
        if self.exige_poliza_todo_riesgo and self.meses_vigencia_todo_riesgo:
            self.fecha_inicio_vigencia_todo_riesgo = self.fecha_inicial_contrato
            self.fecha_fin_vigencia_todo_riesgo = calcular_fecha_vencimiento(self.fecha_inicial_contrato, self.meses_vigencia_todo_riesgo)
        
        # Otras Pólizas
        if self.exige_poliza_otra_1 and self.meses_vigencia_otra_1:
            self.fecha_inicio_vigencia_otra_1 = self.fecha_inicial_contrato
            self.fecha_fin_vigencia_otra_1 = calcular_fecha_vencimiento(self.fecha_inicial_contrato, self.meses_vigencia_otra_1)
    
    def get_condiciones_ipc_display(self):
        """Retorna las condiciones del IPC formateadas"""
        if self.tipo_condicion_ipc and self.puntos_adicionales_ipc:
            return f"{self.get_tipo_condicion_ipc_display()} + {self.puntos_adicionales_ipc} puntos"
        elif self.tipo_condicion_ipc:
            return self.get_tipo_condicion_ipc_display()
        return "No definido"
    
    
    def save(self, *args, **kwargs):
        """Override save para calcular automáticamente las fechas de pólizas"""
        self.calcular_fechas_polizas()
        
        # Si la periodicidad es ANUAL y no hay fecha_aumento_ipc pero hay fecha_inicial_contrato,
        # establecer fecha_aumento_ipc = fecha_inicial_contrato (misma fecha)
        if self.periodicidad_ipc == 'ANUAL' and not self.fecha_aumento_ipc and self.fecha_inicial_contrato:
            self.fecha_aumento_ipc = self.fecha_inicial_contrato
        
        super().save(*args, **kwargs)


class RequerimientoPoliza(AuditoriaMixin):
    """Modelo para las condiciones exigidas de pólizas (parte del contrato)"""
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='requerimientos_poliza', verbose_name='Contrato')
    tipo = models.CharField(max_length=30, choices=POLIZA_TIPO_CHOICES, verbose_name='Tipo de Póliza Requerida')
    valor_asegurado_requerido = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor Asegurado Requerido')
    vigencia_requerida_meses = models.IntegerField(verbose_name='Vigencia Requerida (meses)')
    condiciones_especiales = models.TextField(blank=True, null=True, verbose_name='Condiciones Especiales')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')

    class Meta:
        verbose_name = 'Requerimiento de Póliza'
        verbose_name_plural = 'Requerimientos de Póliza'
        ordering = ['tipo']

    def __str__(self):
        return f"{self.tipo} - ${self.valor_asegurado_requerido:,.2f}"


# Mantener el modelo Poliza para compatibilidad (deprecated)
class Poliza(PolizaMixin, AuditoriaMixin):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='polizas', verbose_name='Contrato')
    otrosi = models.ForeignKey('OtroSi', on_delete=models.CASCADE, null=True, blank=True, related_name='polizas', verbose_name='Otro Sí', help_text='Otro Sí al que pertenece esta póliza')
    renovacion_automatica = models.ForeignKey('RenovacionAutomatica', on_delete=models.CASCADE, null=True, blank=True, related_name='polizas', verbose_name='Renovación Automática', help_text='Renovación Automática a la que pertenece esta póliza')
    
    # Campo para identificar el documento origen
    DOCUMENTO_ORIGEN_CHOICES = [
        ('CONTRATO', 'Contrato Base'),
        ('OTROSI', 'Otro Sí'),
        ('RENOVACION', 'Renovación Automática'),
    ]
    documento_origen_tipo = models.CharField(
        max_length=20,
        choices=DOCUMENTO_ORIGEN_CHOICES,
        default='CONTRATO',
        verbose_name='Tipo de Documento Origen',
        help_text='Tipo de documento al que pertenece esta póliza'
    )
    
    # Campos de colchón (meses adicionales)
    tiene_colchon = models.BooleanField(
        default=False,
        verbose_name='Tiene Colchón',
        help_text='Indica si esta póliza tiene meses adicionales como colchón de seguridad'
    )
    meses_colchon = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name='Meses Colchón',
        help_text='Meses adicionales agregados como colchón de seguridad'
    )
    fecha_vencimiento_real = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha Vencimiento Real',
        help_text='Fecha real de vencimiento (sin colchón). Se calcula automáticamente basada en la fecha final del contrato.'
    )
    
    tipo = models.CharField(max_length=30, choices=POLIZA_TIPO_CHOICES, verbose_name='Tipo de Póliza')
    numero_poliza = models.CharField(max_length=50, verbose_name='Número de Póliza')
    valor_asegurado = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Valor Asegurado')
    valor_propietario_locatario_ocupante_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='PLO (Propietario, Locatario y Ocupante) Asegurado'
    )
    valor_patronal_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Patronal Asegurado'
    )
    valor_gastos_medicos_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Gastos Médicos de Terceros Asegurados'
    )
    valor_vehiculos_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Vehículos Propios y No Propios Asegurados'
    )
    valor_contratistas_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Contratistas y Subcontratistas Asegurados'
    )
    valor_perjuicios_extrapatrimoniales_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Perjuicios Extrapatrimoniales Asegurados'
    )
    valor_dano_moral_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Daño Moral Asegurado'
    )
    valor_lucro_cesante_rce = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Lucro Cesante Asegurado'
    )
    valor_remuneraciones_cumplimiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Remuneraciones Mensuales Aseguradas (Cumplimiento)'
    )
    valor_servicios_publicos_cumplimiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Servicios Públicos Asegurados (Cumplimiento)'
    )
    valor_iva_cumplimiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='IVA Asegurado (Cumplimiento)'
    )
    valor_otros_cumplimiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Cuota de Administración Asegurada (Cumplimiento)'
    )
    valor_remuneraciones_arrendamiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Remuneraciones Mensuales Aseguradas (Arrendamiento)'
    )
    valor_servicios_publicos_arrendamiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Servicios Públicos Asegurados (Arrendamiento)'
    )
    valor_iva_arrendamiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='IVA Asegurado (Arrendamiento)'
    )
    valor_otros_arrendamiento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Cuota de Administración Asegurada (Arrendamiento)'
    )
    # Campos RCE - Coberturas para PROVEEDOR
    rce_cobertura_danos_materiales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños materiales a terceros")
    rce_cobertura_lesiones_personales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Lesiones personales a terceros")
    rce_cobertura_muerte_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Muerte de terceros")
    rce_cobertura_danos_bienes_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños a bienes de terceros")
    rce_cobertura_responsabilidad_patronal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Responsabilidad patronal (si aplica)")
    rce_cobertura_responsabilidad_cruzada = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Responsabilidad cruzada (si aplica)")
    rce_cobertura_danos_contratistas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños causados por contratistas y subcontratistas (si aplica)")
    rce_cobertura_danos_ejecucion_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños durante la ejecución del contrato")
    rce_cobertura_danos_predios_vecinos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Daños en predios vecinos (si aplica)")
    rce_cobertura_gastos_medicos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Gastos médicos (si aplica)")
    rce_cobertura_gastos_defensa = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Gastos de defensa (si aplica)")
    rce_cobertura_perjuicios_patrimoniales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Perjuicios patrimoniales consecuenciales (si aplica)")
    # Campos Cumplimiento - Amparos para PROVEEDOR
    cumplimiento_amparo_cumplimiento_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Cumplimiento del contrato")
    cumplimiento_amparo_buen_manejo_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Buen manejo y correcta inversión del anticipo (si aplica)")
    cumplimiento_amparo_amortizacion_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Correcta amortización del anticipo (si aplica)")
    cumplimiento_amparo_salarios_prestaciones = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Salarios, prestaciones sociales e indemnizaciones laborales")
    cumplimiento_amparo_aportes_seguridad_social = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Aportes al sistema de seguridad social")
    cumplimiento_amparo_calidad_servicio = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Calidad del servicio")
    cumplimiento_amparo_estabilidad_obra = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Estabilidad de la obra (si aplica)")
    cumplimiento_amparo_calidad_bienes = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Calidad y correcto funcionamiento de bienes (si aplica)")
    cumplimiento_amparo_multas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Multas (si aplica)")
    cumplimiento_amparo_clausula_penal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Cláusula penal pecuniaria (si aplica)")
    cumplimiento_amparo_sanciones_incumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Sanciones por incumplimiento (si aplica)")
    fecha_inicio_vigencia = models.DateField(blank=True, null=True, verbose_name='Fecha de Inicio de Vigencia')
    fecha_vencimiento = models.DateField(verbose_name='Fecha de Vencimiento')
    estado_aportado = models.CharField(max_length=20, choices=POLIZA_ESTADO_CHOICES, default='Aporte inicial', verbose_name='Tipo de Entrega')
    aseguradora = models.CharField(max_length=100, blank=True, null=True, verbose_name='Aseguradora')
    cobertura = models.CharField(max_length=200, blank=True, null=True, verbose_name='Características de la Póliza')
    condiciones = models.TextField(blank=True, null=True, verbose_name='Condiciones de la Póliza')
    garantias = models.TextField(blank=True, null=True, verbose_name='Cláusulas de Garantías')
    url_archivo = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='URL del Archivo Digital',
        help_text='Enlace al archivo digital de la póliza (OneDrive, Google Drive, etc.)'
    )

    class Meta:
        verbose_name = 'Póliza (Deprecated)'
        verbose_name_plural = 'Pólizas (Deprecated)'
        ordering = ['-fecha_vencimiento']

    def __str__(self):
        return self.numero_poliza
    
    def clean(self):
        """Validar que solo un documento esté asignado y consistencia de datos"""
        from django.core.exceptions import ValidationError
        
        documentos_asignados = sum([
            bool(self.otrosi),
            bool(self.renovacion_automatica),
            self.documento_origen_tipo == 'CONTRATO'
        ])
        
        # Validar consistencia de documento_origen_tipo
        if self.otrosi and self.documento_origen_tipo != 'OTROSI':
            self.documento_origen_tipo = 'OTROSI'
        elif self.renovacion_automatica and self.documento_origen_tipo != 'RENOVACION':
            self.documento_origen_tipo = 'RENOVACION'
        elif not self.otrosi and not self.renovacion_automatica:
            self.documento_origen_tipo = 'CONTRATO'
        
        # Validar colchón
        if self.tiene_colchon and (not self.meses_colchon or self.meses_colchon <= 0):
            raise ValidationError({
                'meses_colchon': 'Si la póliza tiene colchón, debe especificar los meses adicionales (mayor a 0).'
            })
        
        if not self.tiene_colchon and self.meses_colchon and self.meses_colchon > 0:
            self.tiene_colchon = True
    
    def save(self, *args, **kwargs):
        """Auto-asignar documento_origen_tipo y calcular fecha_vencimiento_real antes de guardar"""
        from datetime import date, timedelta
        
        # Auto-asignar documento_origen_tipo según relaciones
        if self.otrosi:
            self.documento_origen_tipo = 'OTROSI'
        elif self.renovacion_automatica:
            self.documento_origen_tipo = 'RENOVACION'
        else:
            self.documento_origen_tipo = 'CONTRATO'
        
        # Calcular fecha_vencimiento_real si tiene colchón
        # Usar la fecha final del documento origen específico, no la fecha final vigente del contrato
        if self.tiene_colchon and self.contrato:
            try:
                fecha_final = None
                
                # Si pertenece a un Otro Sí específico, usar su fecha final
                if self.otrosi:
                    # Prioridad: effective_to > nueva_fecha_final_actualizada > fecha final del contrato antes del Otro Sí
                    if self.otrosi.effective_to:
                        fecha_final = self.otrosi.effective_to
                    elif self.otrosi.nueva_fecha_final_actualizada:
                        fecha_final = self.otrosi.nueva_fecha_final_actualizada
                    else:
                        # Si no tiene fecha específica, usar la fecha final vigente antes del Otro Sí
                        fecha_antes_otrosi = self.otrosi.effective_from - timedelta(days=1) if self.otrosi.effective_from else date.today()
                        from gestion.services.alertas import _obtener_fecha_final_contrato
                        fecha_final = _obtener_fecha_final_contrato(self.contrato, fecha_antes_otrosi)
                
                # Si pertenece a una Renovación Automática específica, usar su fecha final
                elif self.renovacion_automatica:
                    if self.renovacion_automatica.nueva_fecha_final_actualizada:
                        fecha_final = self.renovacion_automatica.nueva_fecha_final_actualizada
                    elif self.renovacion_automatica.effective_to:
                        fecha_final = self.renovacion_automatica.effective_to
                    else:
                        # Si no tiene fecha específica, usar la fecha final vigente antes de la renovación
                        fecha_antes_renovacion = self.renovacion_automatica.effective_from - timedelta(days=1) if self.renovacion_automatica.effective_from else date.today()
                        from gestion.services.alertas import _obtener_fecha_final_contrato
                        fecha_final = _obtener_fecha_final_contrato(self.contrato, fecha_antes_renovacion)
                
                # Si pertenece al contrato base, usar la fecha final inicial del contrato
                # NO usar fecha final vigente que puede haber sido modificada por Otros Sí o Renovaciones posteriores
                else:
                    fecha_final = self.contrato.fecha_final_inicial
                
                if fecha_final:
                    self.fecha_vencimiento_real = fecha_final
            except Exception:
                # Si hay error al calcular, no establecer fecha_vencimiento_real
                pass
        
        super().save(*args, **kwargs)
    
    def obtener_documento_origen(self):
        """Retorna el documento al que pertenece esta póliza"""
        if self.otrosi:
            return self.otrosi
        elif self.renovacion_automatica:
            return self.renovacion_automatica
        return self.contrato
    
    def obtener_numero_documento_origen(self):
        """Retorna el número/identificador del documento origen"""
        if self.otrosi:
            return self.otrosi.numero_otrosi
        elif self.renovacion_automatica:
            return self.renovacion_automatica.numero_renovacion
        return self.contrato.num_contrato
    
    def obtener_fecha_vencimiento_efectiva(self, fecha_referencia=None):
        """Retorna la fecha de vencimiento efectiva para alertas y cálculos"""
        # Verificar si los campos de colchón existen (compatibilidad con migraciones pendientes)
        if hasattr(self, 'tiene_colchon') and hasattr(self, 'fecha_vencimiento_real'):
            if self.tiene_colchon and self.fecha_vencimiento_real:
                return self.fecha_vencimiento_real
        return self.fecha_vencimiento
    
    def necesita_renovacion_por_contrato(self, fecha_final_contrato_nueva):
        """
        Determina si la póliza necesita renovación porque el contrato se renovó.
        Retorna True si la fecha_final_contrato_nueva es posterior a fecha_vencimiento_real.
        """
        if not self.tiene_colchon:
            return False
        if not self.fecha_vencimiento_real:
            return False
        return fecha_final_contrato_nueva > self.fecha_vencimiento_real
    
    def cumple_requisitos_contrato(self):
        """
        Valida si la póliza cumple con los requisitos del documento al que pertenece.
        Considera el documento origen (Contrato, OtroSi o RenovacionAutomatica).
        Usa los requisitos específicos del documento origen de la póliza.
        """
        from datetime import date
        from gestion.views.utils import (
            _construir_requisitos_poliza_desde_contrato_base,
            _construir_requisitos_poliza_desde_otrosi,
            _construir_requisitos_poliza_desde_renovacion
        )
        
        contrato = self.contrato
        cumple = True
        observaciones = []
        
        # Obtener requisitos según el documento origen específico de la póliza
        documento = self.obtener_documento_origen()
        requisitos = {}
        
        if documento == contrato:
            # Si el documento es el contrato base
            requisitos = _construir_requisitos_poliza_desde_contrato_base(contrato)
        elif hasattr(documento, 'numero_otrosi'):
            # Si el documento es un Otro Sí
            requisitos = _construir_requisitos_poliza_desde_otrosi(contrato, documento)
        elif hasattr(documento, 'numero_renovacion'):
            # Si el documento es una Renovación Automática
            requisitos = _construir_requisitos_poliza_desde_renovacion(contrato, documento)
        else:
            # Fallback: usar contrato base
            requisitos = _construir_requisitos_poliza_desde_contrato_base(contrato)
        
        # Convertir requisitos al formato esperado por la validación
        polizas_requeridas = {}
        
        if requisitos.get('rce', {}).get('exigida'):
            detalles_rce = requisitos['rce'].get('detalles', {})
            polizas_requeridas['RCE - Responsabilidad Civil'] = {
                'valor_requerido': requisitos['rce'].get('valor'),
                'fecha_fin_requerida': requisitos['rce'].get('fecha_fin'),
                'detalles': detalles_rce
            }
        
        if requisitos.get('cumplimiento', {}).get('exigida'):
            detalles_cumpl = requisitos['cumplimiento'].get('detalles', {})
            polizas_requeridas['Cumplimiento'] = {
                'valor_requerido': requisitos['cumplimiento'].get('valor'),
                'fecha_fin_requerida': requisitos['cumplimiento'].get('fecha_fin'),
                'detalles': detalles_cumpl
            }
        
        if requisitos.get('arrendamiento', {}).get('exigida'):
            detalles_arr = requisitos['arrendamiento'].get('detalles', {})
            polizas_requeridas['Poliza de Arrendamiento'] = {
                'valor_requerido': requisitos['arrendamiento'].get('valor'),
                'fecha_fin_requerida': requisitos['arrendamiento'].get('fecha_fin'),
                'detalles': detalles_arr
            }
        
        if requisitos.get('todo_riesgo', {}).get('exigida'):
            polizas_requeridas['Arrendamiento'] = {
                'valor_requerido': requisitos['todo_riesgo'].get('valor'),
                'fecha_fin_requerida': requisitos['todo_riesgo'].get('fecha_fin'),
                'detalles': {}
            }
        
        if requisitos.get('otra', {}).get('exigida'):
            polizas_requeridas['Otra'] = {
                'valor_requerido': requisitos['otra'].get('valor'),
                'fecha_fin_requerida': requisitos['otra'].get('fecha_fin'),
                'nombre': requisitos['otra'].get('nombre'),
                'detalles': {}
            }
        
        def verificar_detalle(valor_poliza, valor_requerido, etiqueta):
            if valor_requerido is not None:
                if valor_poliza is None or valor_poliza < valor_requerido:
                    observaciones.append(
                        f"{etiqueta} insuficiente. Requerido: ${valor_requerido:,.2f}, Actual: ${0 if valor_poliza is None else valor_poliza:,.2f}"
                    )
                    return False
            return True
        
        # Validar según el tipo de póliza usando los requisitos del último Otro Sí vigente
        if self.tipo == 'RCE - Responsabilidad Civil':
            if 'RCE - Responsabilidad Civil' in polizas_requeridas:
                req_rce = polizas_requeridas['RCE - Responsabilidad Civil']
                valor_requerido = req_rce.get('valor_requerido')
                fecha_fin_requerida = req_rce.get('fecha_fin_requerida')
                detalles = req_rce.get('detalles', {})
                
                if valor_requerido and self.valor_asegurado < valor_requerido:
                    cumple = False
                    observaciones.append(f"Valor asegurado RCE insuficiente. Requerido: ${valor_requerido:,.2f}, Actual: ${self.valor_asegurado:,.2f}")
                
                if fecha_fin_requerida and self.fecha_vencimiento < fecha_fin_requerida:
                    cumple = False
                    observaciones.append(f"Vigencia RCE insuficiente. Requerida hasta: {fecha_fin_requerida.strftime('%Y-%m-%d')}, Actual: {self.fecha_vencimiento.strftime('%Y-%m-%d')}")
                
                # Validar detalles según tipo de contrato
                if contrato.tipo_contrato_cliente_proveedor == 'CLIENTE':
                    detalles_rce = [
                        (self.valor_propietario_locatario_ocupante_rce, detalles.get('plo'), "PLO (Propietario, Locatario y Ocupante)"),
                        (self.valor_patronal_rce, detalles.get('patronal'), "Patronal"),
                        (self.valor_gastos_medicos_rce, detalles.get('gastos_medicos'), "Gastos Médicos de Terceros"),
                        (self.valor_vehiculos_rce, detalles.get('vehiculos'), "Vehículos Propios y No Propios"),
                        (self.valor_contratistas_rce, detalles.get('contratistas'), "Contratistas y Subcontratistas"),
                        (self.valor_perjuicios_extrapatrimoniales_rce, detalles.get('perjuicios'), "Perjuicios Extrapatrimoniales"),
                        (self.valor_dano_moral_rce, detalles.get('dano_moral'), "Daño Moral"),
                        (self.valor_lucro_cesante_rce, detalles.get('lucro_cesante'), "Lucro Cesante"),
                    ]
                elif contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
                    detalles_rce = [
                        (self.rce_cobertura_danos_materiales, detalles.get('danos_materiales'), "Daños materiales a terceros"),
                        (self.rce_cobertura_lesiones_personales, detalles.get('lesiones_personales'), "Lesiones personales a terceros"),
                        (self.rce_cobertura_muerte_terceros, detalles.get('muerte_terceros'), "Muerte de terceros"),
                        (self.rce_cobertura_danos_bienes_terceros, detalles.get('danos_bienes_terceros'), "Daños a bienes de terceros"),
                        (self.rce_cobertura_responsabilidad_patronal, detalles.get('responsabilidad_patronal'), "Responsabilidad patronal"),
                        (self.rce_cobertura_responsabilidad_cruzada, detalles.get('responsabilidad_cruzada'), "Responsabilidad cruzada"),
                        (self.rce_cobertura_danos_contratistas, detalles.get('danos_contratistas'), "Daños causados por contratistas y subcontratistas"),
                        (self.rce_cobertura_danos_ejecucion_contrato, detalles.get('danos_ejecucion_contrato'), "Daños durante la ejecución del contrato"),
                        (self.rce_cobertura_danos_predios_vecinos, detalles.get('danos_predios_vecinos'), "Daños en predios vecinos"),
                        (self.rce_cobertura_gastos_medicos, detalles.get('gastos_medicos_cobertura'), "Gastos médicos"),
                        (self.rce_cobertura_gastos_defensa, detalles.get('gastos_defensa'), "Gastos de defensa"),
                        (self.rce_cobertura_perjuicios_patrimoniales, detalles.get('perjuicios_patrimoniales'), "Perjuicios patrimoniales consecuenciales"),
                    ]
                else:
                    detalles_rce = []
                
                for valor_poliza, valor_requerido, etiqueta in detalles_rce:
                    if not verificar_detalle(valor_poliza, valor_requerido, etiqueta):
                        cumple = False
        
        elif self.tipo == 'Cumplimiento':
            if 'Cumplimiento' in polizas_requeridas:
                req_cumpl = polizas_requeridas['Cumplimiento']
                valor_requerido = req_cumpl.get('valor_requerido')
                fecha_fin_requerida = req_cumpl.get('fecha_fin_requerida')
                detalles = req_cumpl.get('detalles', {})
                
                if valor_requerido and self.valor_asegurado < valor_requerido:
                    cumple = False
                    observaciones.append(f"Valor asegurado Cumplimiento insuficiente. Requerido: ${valor_requerido:,.2f}, Actual: ${self.valor_asegurado:,.2f}")
                
                if fecha_fin_requerida and self.fecha_vencimiento < fecha_fin_requerida:
                    cumple = False
                    observaciones.append(f"Vigencia Cumplimiento insuficiente. Requerida hasta: {fecha_fin_requerida.strftime('%Y-%m-%d')}, Actual: {self.fecha_vencimiento.strftime('%Y-%m-%d')}")
                
                # Validar detalles según tipo de contrato
                if contrato.tipo_contrato_cliente_proveedor == 'CLIENTE':
                    detalles_cumplimiento = [
                        (self.valor_remuneraciones_cumplimiento, detalles.get('remuneraciones'), "Remuneraciones Mensuales"),
                        (self.valor_servicios_publicos_cumplimiento, detalles.get('servicios_publicos'), "Servicios Públicos"),
                        (self.valor_iva_cumplimiento, detalles.get('iva'), "IVA"),
                        (self.valor_otros_cumplimiento, detalles.get('cuota_admon'), "Cuota de administración"),
                    ]
                elif contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR':
                    detalles_cumplimiento = [
                        (self.cumplimiento_amparo_cumplimiento_contrato, detalles.get('cumplimiento_contrato'), "Cumplimiento del contrato"),
                        (self.cumplimiento_amparo_buen_manejo_anticipo, detalles.get('buen_manejo_anticipo'), "Buen manejo y correcta inversión del anticipo"),
                        (self.cumplimiento_amparo_amortizacion_anticipo, detalles.get('amortizacion_anticipo'), "Correcta amortización del anticipo"),
                        (self.cumplimiento_amparo_salarios_prestaciones, detalles.get('salarios_prestaciones'), "Salarios, prestaciones sociales e indemnizaciones laborales"),
                        (self.cumplimiento_amparo_aportes_seguridad_social, detalles.get('aportes_seguridad_social'), "Aportes al sistema de seguridad social"),
                        (self.cumplimiento_amparo_calidad_servicio, detalles.get('calidad_servicio'), "Calidad del servicio"),
                        (self.cumplimiento_amparo_estabilidad_obra, detalles.get('estabilidad_obra'), "Estabilidad de la obra"),
                        (self.cumplimiento_amparo_calidad_bienes, detalles.get('calidad_bienes'), "Calidad y correcto funcionamiento de bienes"),
                        (self.cumplimiento_amparo_multas, detalles.get('multas'), "Multas"),
                        (self.cumplimiento_amparo_clausula_penal, detalles.get('clausula_penal'), "Cláusula penal pecuniaria"),
                        (self.cumplimiento_amparo_sanciones_incumplimiento, detalles.get('sanciones_incumplimiento'), "Sanciones por incumplimiento"),
                    ]
                else:
                    detalles_cumplimiento = []
                
                for valor_poliza, valor_requerido, etiqueta in detalles_cumplimiento:
                    if not verificar_detalle(valor_poliza, valor_requerido, etiqueta):
                        cumple = False
        
        elif self.tipo == 'Arrendamiento':
            if 'Arrendamiento' in polizas_requeridas:
                req_tr = polizas_requeridas['Arrendamiento']
                valor_requerido = req_tr.get('valor_requerido')
                fecha_fin_requerida = req_tr.get('fecha_fin_requerida')
                
                if valor_requerido and self.valor_asegurado < valor_requerido:
                    cumple = False
                    observaciones.append(f"Valor asegurado Todo Riesgo insuficiente. Requerido: ${valor_requerido:,.2f}, Actual: ${self.valor_asegurado:,.2f}")
                
                if fecha_fin_requerida and self.fecha_vencimiento < fecha_fin_requerida:
                    cumple = False
                    observaciones.append(f"Vigencia Todo Riesgo insuficiente. Requerida hasta: {fecha_fin_requerida.strftime('%Y-%m-%d')}, Actual: {self.fecha_vencimiento.strftime('%Y-%m-%d')}")
        
        elif self.tipo == 'Poliza de Arrendamiento':
            if 'Poliza de Arrendamiento' in polizas_requeridas:
                req_arr = polizas_requeridas['Poliza de Arrendamiento']
                valor_requerido = req_arr.get('valor_requerido')
                fecha_fin_requerida = req_arr.get('fecha_fin_requerida')
                detalles = req_arr.get('detalles', {})
                
                if valor_requerido and self.valor_asegurado < valor_requerido:
                    cumple = False
                    observaciones.append(f"Valor asegurado Póliza de Arrendamiento insuficiente. Requerido: ${valor_requerido:,.2f}, Actual: ${self.valor_asegurado:,.2f}")
                
                if fecha_fin_requerida and self.fecha_vencimiento < fecha_fin_requerida:
                    cumple = False
                    observaciones.append(f"Vigencia Póliza de Arrendamiento insuficiente. Requerida hasta: {fecha_fin_requerida.strftime('%Y-%m-%d')}, Actual: {self.fecha_vencimiento.strftime('%Y-%m-%d')}")
                
                detalles_arrendamiento = [
                    (self.valor_remuneraciones_arrendamiento, detalles.get('remuneraciones'), "Remuneraciones Mensuales"),
                    (self.valor_servicios_publicos_arrendamiento, detalles.get('servicios_publicos'), "Servicios Públicos"),
                    (self.valor_iva_arrendamiento, detalles.get('iva'), "IVA"),
                    (self.valor_otros_arrendamiento, detalles.get('cuota_admon'), "Cuota de administración"),
                ]
                
                for valor_poliza, valor_requerido, etiqueta in detalles_arrendamiento:
                    if not verificar_detalle(valor_poliza, valor_requerido, etiqueta):
                        cumple = False
        
        elif self.tipo == 'Otra':
            if 'Otra' in polizas_requeridas:
                req_otra = polizas_requeridas['Otra']
                valor_requerido = req_otra.get('valor_requerido')
                fecha_fin_requerida = req_otra.get('fecha_fin_requerida')
                
                if valor_requerido and self.valor_asegurado < valor_requerido:
                    cumple = False
                    nombre_poliza = req_otra.get('nombre', 'Otra')
                    observaciones.append(f"Valor asegurado {nombre_poliza} insuficiente. Requerido: ${valor_requerido:,.2f}, Actual: ${self.valor_asegurado:,.2f}")
                
                if fecha_fin_requerida and self.fecha_vencimiento < fecha_fin_requerida:
                    cumple = False
                    observaciones.append(f"Vigencia insuficiente. Requerida hasta: {fecha_fin_requerida.strftime('%Y-%m-%d')}, Actual: {self.fecha_vencimiento.strftime('%Y-%m-%d')}")
        
        # Validar que la póliza no esté vencida respecto a la fecha de HOY
        fecha_hoy = date.today()
        if self.fecha_vencimiento < fecha_hoy:
            cumple = False
            dias_vencida = (fecha_hoy - self.fecha_vencimiento).days
            observaciones.append(f"⚠️ ADVERTENCIA: La póliza está vencida desde el {self.fecha_vencimiento.strftime('%Y-%m-%d')} (hace {dias_vencida} día(s)).")
            observaciones.append(f"   Si es para alimentar la base de datos, puede continuar. De lo contrario, revise las fechas.")
        
        return {
            'cumple': cumple,
            'observaciones': observaciones
        }


class SeguimientoContrato(models.Model):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='seguimientos',
        verbose_name='Contrato'
    )
    detalle = models.TextField(verbose_name='Detalle del seguimiento')
    registrado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Registrado por'
    )
    fecha_registro = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de registro'
    )

    class Meta:
        verbose_name = 'Seguimiento de Contrato'
        verbose_name_plural = 'Seguimientos de Contrato'
        ordering = ['-fecha_registro']

    def __str__(self):
        registrado = self.registrado_por or 'Registro'
        return f'{registrado} - {self.fecha_registro:%Y-%m-%d %H:%M}'


class RenovacionAutomatica(models.Model):
    """
    Modelo para registrar eventos de renovación automática de contratos.
    Funciona como un OtroSi pero con otro nombre, implementando efecto cadena.
    Incluye todas las condiciones de pólizas actualizadas.
    """
    
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('EN_REVISION', 'En Revisión'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('ANULADO', 'Anulado'),
    ]
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='renovaciones_automaticas',
        verbose_name='Contrato'
    )
    
    # Metadatos
    numero_renovacion = models.CharField(max_length=50, verbose_name='Número de Renovación', default='RA-TEMP')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR', verbose_name='Estado')
    version = models.IntegerField(default=1, verbose_name='Versión')
    
    # Vigencias
    fecha_renovacion = models.DateField(
        verbose_name='Fecha de Renovación',
        help_text='Fecha en que se autorizó la renovación'
    )
    effective_from = models.DateField(
        verbose_name='Vigencia Desde',
        help_text='Fecha desde la cual aplican los cambios',
        default=date.today
    )
    effective_to = models.DateField(
        blank=True,
        null=True,
        verbose_name='Vigencia Hasta',
        help_text='Fecha hasta la cual aplican los cambios (opcional)'
    )
    
    # Campos de renovación
    fecha_inicio_nueva_vigencia = models.DateField(
        verbose_name='Fecha Inicio Nueva Vigencia',
        help_text='Fecha desde la cual inicia la nueva vigencia'
    )
    nueva_fecha_final_actualizada = models.DateField(
        blank=True,
        null=True,
        verbose_name='Nueva Fecha Final',
        help_text='Nueva fecha final del contrato después de la renovación'
    )
    meses_renovacion = models.IntegerField(
        verbose_name='Meses de Renovación',
        help_text='Número de meses por los cuales se renovó el contrato'
    )
    usar_duracion_inicial = models.BooleanField(
        default=True,
        verbose_name='Usó Duración Inicial',
        help_text='Indica si se usó la duración inicial del contrato para la renovación'
    )
    fecha_final_anterior = models.DateField(
        verbose_name='Fecha Final Anterior',
        help_text='Fecha final del contrato antes de la renovación'
    )
    
    # Descripciones
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción',
        help_text='Descripción de la renovación automática'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas adicionales sobre la renovación'
    )
    
    # Auditoría
    creado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Creado Por')
    fecha_creacion = models.DateTimeField(default=timezone.now, verbose_name='Fecha de Creación')
    aprobado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Aprobado Por')
    fecha_aprobacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Aprobación')
    modificado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Última Modificación Por')
    fecha_modificacion = models.DateTimeField(default=timezone.now, verbose_name='Fecha de Última Modificación')
    anulado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Anulado Por')
    fecha_anulacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Anulación')
    
    # Campos de Pólizas - RCE
    nuevo_exige_poliza_rce = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza RCE?")
    nuevo_valor_asegurado_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado RCE")
    nuevo_valor_propietario_locatario_ocupante_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo PLO (Propietario, Locatario y Ocupante) Asegurado")
    nuevo_valor_patronal_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Patronal Asegurado")
    nuevo_valor_gastos_medicos_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Gastos Médicos de Terceros Asegurados")
    nuevo_valor_vehiculos_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Vehículos Propios y No Propios Asegurados")
    nuevo_valor_contratistas_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Contratistas y Subcontratistas Asegurados")
    nuevo_valor_perjuicios_extrapatrimoniales_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Perjuicios Extrapatrimoniales Asegurados")
    nuevo_valor_dano_moral_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daño Moral Asegurado")
    nuevo_valor_lucro_cesante_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Lucro Cesante Asegurado")
    # Campos RCE - Coberturas para PROVEEDOR
    nuevo_rce_cobertura_danos_materiales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños materiales a terceros")
    nuevo_rce_cobertura_lesiones_personales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Lesiones personales a terceros")
    nuevo_rce_cobertura_muerte_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Muerte de terceros")
    nuevo_rce_cobertura_danos_bienes_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños a bienes de terceros")
    nuevo_rce_cobertura_responsabilidad_patronal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Responsabilidad patronal (si aplica)")
    nuevo_rce_cobertura_responsabilidad_cruzada = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Responsabilidad cruzada (si aplica)")
    nuevo_rce_cobertura_danos_contratistas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños causados por contratistas y subcontratistas (si aplica)")
    nuevo_rce_cobertura_danos_ejecucion_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños durante la ejecución del contrato")
    nuevo_rce_cobertura_danos_predios_vecinos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños en predios vecinos (si aplica)")
    nuevo_rce_cobertura_gastos_medicos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Gastos médicos (si aplica)")
    nuevo_rce_cobertura_gastos_defensa = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Gastos de defensa (si aplica)")
    nuevo_rce_cobertura_perjuicios_patrimoniales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Perjuicios patrimoniales consecuenciales (si aplica)")
    nuevo_meses_vigencia_rce = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia RCE")
    nuevo_fecha_inicio_vigencia_rce = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia RCE")
    nuevo_fecha_fin_vigencia_rce = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia RCE")
    
    # Póliza Cumplimiento
    nuevo_exige_poliza_cumplimiento = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza de Cumplimiento?")
    nuevo_valor_asegurado_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Cumplimiento")
    nuevo_valor_remuneraciones_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Remuneraciones Mensuales Aseguradas (Cumplimiento)")
    nuevo_valor_servicios_publicos_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Servicios Públicos Asegurados (Cumplimiento)")
    nuevo_valor_iva_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo IVA Asegurado (Cumplimiento)")
    nuevo_valor_otros_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cuota de Administración Asegurada (Cumplimiento)")
    # Campos Cumplimiento - Amparos para PROVEEDOR
    nuevo_cumplimiento_amparo_cumplimiento_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cumplimiento del contrato")
    nuevo_cumplimiento_amparo_buen_manejo_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Buen manejo y correcta inversión del anticipo (si aplica)")
    nuevo_cumplimiento_amparo_amortizacion_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Correcta amortización del anticipo (si aplica)")
    nuevo_cumplimiento_amparo_salarios_prestaciones = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Salarios, prestaciones sociales e indemnizaciones laborales")
    nuevo_cumplimiento_amparo_aportes_seguridad_social = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Aportes al sistema de seguridad social")
    nuevo_cumplimiento_amparo_calidad_servicio = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Calidad del servicio")
    nuevo_cumplimiento_amparo_estabilidad_obra = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Estabilidad de la obra (si aplica)")
    nuevo_cumplimiento_amparo_calidad_bienes = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Calidad y correcto funcionamiento de bienes (si aplica)")
    nuevo_cumplimiento_amparo_multas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Multas (si aplica)")
    nuevo_cumplimiento_amparo_clausula_penal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cláusula penal pecuniaria (si aplica)")
    nuevo_cumplimiento_amparo_sanciones_incumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Sanciones por incumplimiento (si aplica)")
    nuevo_meses_vigencia_cumplimiento = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Cumplimiento")
    nuevo_fecha_inicio_vigencia_cumplimiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Cumplimiento")
    nuevo_fecha_fin_vigencia_cumplimiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Cumplimiento")
    
    # Póliza de Arrendamiento
    nuevo_exige_poliza_arrendamiento = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza de Arrendamiento?")
    nuevo_valor_asegurado_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Póliza de Arrendamiento")
    nuevo_valor_remuneraciones_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Remuneraciones Mensuales Aseguradas (Arrendamiento)")
    nuevo_valor_servicios_publicos_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Servicios Públicos Asegurados (Arrendamiento)")
    nuevo_valor_iva_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo IVA Asegurado (Arrendamiento)")
    nuevo_valor_otros_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cuota de Administración Asegurada (Arrendamiento)")
    nuevo_meses_vigencia_arrendamiento = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Póliza de Arrendamiento")
    nuevo_fecha_inicio_vigencia_arrendamiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Póliza de Arrendamiento")
    nuevo_fecha_fin_vigencia_arrendamiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Póliza de Arrendamiento")
    
    # Póliza Todo Riesgo
    nuevo_exige_poliza_todo_riesgo = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza Todo Riesgo?")
    nuevo_valor_asegurado_todo_riesgo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Todo Riesgo")
    nuevo_meses_vigencia_todo_riesgo = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Todo Riesgo")
    nuevo_fecha_inicio_vigencia_todo_riesgo = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Todo Riesgo")
    nuevo_fecha_fin_vigencia_todo_riesgo = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Todo Riesgo")
    
    # Otras Pólizas (Opcional)
    nuevo_exige_poliza_otra_1 = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Otras Pólizas?")
    nuevo_nombre_poliza_otra_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Nuevo Nombre Otras Pólizas")
    nuevo_valor_asegurado_otra_1 = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Otras Pólizas")
    nuevo_meses_vigencia_otra_1 = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Otras Pólizas")
    nuevo_fecha_inicio_vigencia_otra_1 = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Otras Pólizas")
    nuevo_fecha_fin_vigencia_otra_1 = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Otras Pólizas")
    
    modifica_polizas = models.BooleanField(
        default=False,
        verbose_name='¿Modifica Pólizas?',
        help_text='Indica si esta renovación actualiza las condiciones de pólizas del contrato'
    )

    class Meta:
        verbose_name = 'Renovación Automática'
        verbose_name_plural = 'Renovaciones Automáticas'
        ordering = ['-fecha_aprobacion', '-effective_from', '-version']
        indexes = [
            models.Index(fields=['contrato', '-fecha_aprobacion', '-effective_from']),
            models.Index(fields=['contrato', 'estado', '-effective_from']),
        ]

    def __str__(self):
        return f'Renovación {self.numero_renovacion} - {self.contrato.num_contrato} ({self.meses_renovacion} meses)'
    
    def get_estado_vigencia(self, fecha_referencia=None):
        """
        Retorna el estado de vigencia de la renovación automática.
        
        Returns:
        - 'VIGENTE': Si está vigente en la fecha de referencia
        - 'PENDIENTE': Si aún no ha iniciado su vigencia
        - 'VENCIDO': Si ya pasó su fecha de fin
        - None: Si no está aprobado
        """
        from datetime import date
        if fecha_referencia is None:
            fecha_referencia = date.today()
        
        if self.estado != 'APROBADO':
            return None
        
        if self.effective_to and fecha_referencia > self.effective_to:
            return 'VENCIDO'
        
        if self.effective_from > fecha_referencia:
            return 'PENDIENTE'
        
        if self.effective_from <= fecha_referencia:
            if self.effective_to is None or fecha_referencia <= self.effective_to:
                return 'VIGENTE'
        
        return 'VENCIDO'
    
    def is_vigente(self, fecha_referencia=None):
        """Determina si esta renovación automática está vigente en una fecha dada"""
        from datetime import date
        if fecha_referencia is None:
            fecha_referencia = date.today()
        
        if self.estado != 'APROBADO':
            return False
        
        if fecha_referencia < self.effective_from:
            return False
        
        if self.effective_to and fecha_referencia > self.effective_to:
            return False
        
        return True
    
    def save(self, *args, **kwargs):
        """Override save para validaciones y auto-incremento de versión"""
        if not self.pk:
            ultima_renovacion = RenovacionAutomatica.objects.filter(contrato=self.contrato).order_by('-version').first()
            if ultima_renovacion:
                self.version = ultima_renovacion.version + 1
            else:
                self.version = 1
            
            if not self.numero_renovacion or self.numero_renovacion == 'RA-TEMP':
                # Obtener el número más alto de renovación existente para este contrato
                # Extraer números de renovaciones existentes (formato RA-X)
                import re
                renovaciones_existentes = RenovacionAutomatica.objects.filter(
                    contrato=self.contrato
                ).exclude(numero_renovacion__in=['', 'RA-TEMP', None]).values_list('numero_renovacion', flat=True)
                
                numeros_existentes = []
                for num in renovaciones_existentes:
                    if num:
                        match = re.search(r'RA-(\d+)', str(num))
                        if match:
                            numeros_existentes.append(int(match.group(1)))
                
                # Si hay números existentes, usar el máximo + 1, sino empezar en 1
                if numeros_existentes:
                    siguiente_numero = max(numeros_existentes) + 1
                else:
                    siguiente_numero = 1
                
                self.numero_renovacion = f"RA-{siguiente_numero}"
        
        super().save(*args, **kwargs)


class SeguimientoPoliza(models.Model):
    TIPO_SEGUIMIENTO_CHOICES = POLIZA_TIPO_CHOICES

    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='seguimientos_poliza',
        verbose_name='Contrato',
        blank=True,
        null=True
    )
    poliza = models.ForeignKey(
        Poliza,
        on_delete=models.CASCADE,
        related_name='seguimientos',
        verbose_name='Póliza',
        blank=True,
        null=True
    )
    poliza_tipo = models.CharField(
        max_length=30,
        choices=TIPO_SEGUIMIENTO_CHOICES,
        verbose_name='Tipo de Póliza',
        blank=True,
        null=True
    )
    detalle = models.TextField(verbose_name='Detalle del seguimiento')
    registrado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Registrado por'
    )
    fecha_registro = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de registro'
    )

    class Meta:
        verbose_name = 'Seguimiento de Póliza'
        verbose_name_plural = 'Seguimientos de Póliza'
        ordering = ['-fecha_registro']

    def __str__(self):
        registrado = self.registrado_por or 'Registro'
        tipo = self.poliza_tipo or (self.poliza.get_tipo_display() if self.poliza else None)
        tipo_display = tipo or 'Póliza'
        return f'{tipo_display} - {registrado} - {self.fecha_registro:%Y-%m-%d %H:%M}'

    def clean(self):
        tiene_referencia_poliza = bool(self.poliza)

        if not tiene_referencia_poliza and not self.contrato:
            raise ValidationError('Debe asociar el seguimiento a un contrato cuando no se vinculada una póliza.')


        if tiene_referencia_poliza:
            if self.poliza and not self.contrato:
                self.contrato = self.poliza.contrato

            if not self.poliza_tipo and self.poliza:
                self.poliza_tipo = self.poliza.tipo
        else:
            if not self.poliza_tipo:
                raise ValidationError('Debe indicar el tipo de póliza del seguimiento.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class OtroSi(models.Model):
    """
    Modelo mejorado de Otro Sí (Addenda) que modifica el contrato original.
    El Otrosí vigente siempre tiene precedencia sobre el contrato base.
    """
    
    TIPO_CHOICES = [
        ('AMENDMENT', 'Modificación General'),
        ('RENEWAL', 'Renovación'),
        ('IPC_UPDATE', 'Actualización IPC'),
        ('CANON_CHANGE', 'Cambio de Canon'),
        ('PLAZO_EXTENSION', 'Extensión de Plazo'),
        ('POLIZAS_UPDATE', 'Actualización de Pólizas'),
        ('OTRO', 'Otro'),
    ]
    
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('EN_REVISION', 'En Revisión'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('ANULADO', 'Anulado'),
    ]
    
    # Relación con contrato
    contrato = models.ForeignKey(
        Contrato, 
        on_delete=models.CASCADE, 
        related_name='otrosi', 
        verbose_name='Contrato'
    )
    
    # Metadatos del Otrosí
    numero_otrosi = models.CharField(max_length=50, verbose_name='Número de Otro Sí', default='OS-TEMP')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='AMENDMENT', verbose_name='Tipo')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR', verbose_name='Estado')
    version = models.IntegerField(default=1, verbose_name='Versión')
    
    # Vigencias
    fecha_otrosi = models.DateField(verbose_name='Fecha del Otro Sí')
    effective_from = models.DateField(verbose_name='Vigencia Desde', help_text='Fecha desde la cual aplican los cambios', default=date.today)
    effective_to = models.DateField(blank=True, null=True, verbose_name='Vigencia Hasta', help_text='Fecha hasta la cual aplican los cambios (opcional)')
    
    # Campos que pueden ser modificados (nullable = no se modifica)
    # Financieros
    nuevo_valor_canon = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True, verbose_name='Nuevo Valor Canon')
    nueva_modalidad_pago = models.CharField(max_length=30, blank=True, null=True, verbose_name='Nueva Modalidad de Pago')
    nuevo_canon_minimo_garantizado = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True, verbose_name='Nuevo Canon Mínimo')
    nuevo_porcentaje_ventas = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Nuevo % Ventas')
    
    # Plazo
    nueva_fecha_final_actualizada = models.DateField(blank=True, null=True, verbose_name='Nueva Fecha Final')
    nuevo_plazo_meses = models.IntegerField(blank=True, null=True, verbose_name='Nuevo Plazo (Meses)')
    
    # IPC
    nuevo_tipo_condicion_ipc = models.CharField(
        max_length=20, 
        choices=TIPO_CONDICION_IPC_CHOICES,  # Mantener para migraciones, pero usar obtener_tipos_condicion_ipc_choices() en formularios
        blank=True, 
        null=True, 
        verbose_name='Nuevo Tipo IPC'
    )
    nuevos_puntos_adicionales_ipc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Nuevos Puntos IPC')
    nueva_periodicidad_ipc = models.CharField(
        max_length=20, 
        choices=PERIODICIDAD_IPC_CHOICES,  # Mantener para migraciones, pero usar obtener_periodicidades_ipc_choices() en formularios
        blank=True, 
        null=True, 
        verbose_name='Nueva Periodicidad IPC'
    )
    nueva_fecha_aumento_ipc = models.DateField(blank=True, null=True, verbose_name='Nueva Fecha Aumento IPC', help_text='Nueva fecha exacta en que se aplica el ajuste por IPC')
    
    # Descripciones y justificaciones
    descripcion = models.TextField(verbose_name='Descripción de los cambios')
    clausulas_modificadas = models.TextField(blank=True, null=True, verbose_name='Cláusulas Modificadas', help_text='Detalle de cláusulas específicas modificadas')
    justificacion_legal = models.TextField(blank=True, null=True, verbose_name='Justificación Legal/Contractual')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    
    # Indicador de modificación de pólizas
    modifica_polizas = models.BooleanField(default=False, verbose_name='¿Modifica Pólizas?', help_text='Indica si este Otro Sí actualiza pólizas del contrato')
    notas_polizas = models.TextField(blank=True, null=True, verbose_name='Notas sobre Pólizas', help_text='Descripción de las modificaciones en pólizas')
    
    # --- CAMPOS DE PÓLIZAS MODIFICADOS (independientes del contrato base) ---
    
    # Póliza RCE
    nuevo_exige_poliza_rce = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza RCE?")
    nuevo_valor_asegurado_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado RCE")
    nuevo_valor_propietario_locatario_ocupante_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo PLO (Propietario, Locatario y Ocupante) Asegurado")
    nuevo_valor_patronal_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Patronal Asegurado")
    nuevo_valor_gastos_medicos_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Gastos Médicos de Terceros Asegurados")
    nuevo_valor_vehiculos_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Vehículos Propios y No Propios Asegurados")
    nuevo_valor_contratistas_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Contratistas y Subcontratistas Asegurados")
    nuevo_valor_perjuicios_extrapatrimoniales_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Perjuicios Extrapatrimoniales Asegurados")
    nuevo_valor_dano_moral_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daño Moral Asegurado")
    nuevo_valor_lucro_cesante_rce = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Lucro Cesante Asegurado")
    # Campos RCE - Coberturas para PROVEEDOR
    nuevo_rce_cobertura_danos_materiales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños materiales a terceros")
    nuevo_rce_cobertura_lesiones_personales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Lesiones personales a terceros")
    nuevo_rce_cobertura_muerte_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Muerte de terceros")
    nuevo_rce_cobertura_danos_bienes_terceros = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños a bienes de terceros")
    nuevo_rce_cobertura_responsabilidad_patronal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Responsabilidad patronal (si aplica)")
    nuevo_rce_cobertura_responsabilidad_cruzada = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Responsabilidad cruzada (si aplica)")
    nuevo_rce_cobertura_danos_contratistas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños causados por contratistas y subcontratistas (si aplica)")
    nuevo_rce_cobertura_danos_ejecucion_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños durante la ejecución del contrato")
    nuevo_rce_cobertura_danos_predios_vecinos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Daños en predios vecinos (si aplica)")
    nuevo_rce_cobertura_gastos_medicos = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Gastos médicos (si aplica)")
    nuevo_rce_cobertura_gastos_defensa = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Gastos de defensa (si aplica)")
    nuevo_rce_cobertura_perjuicios_patrimoniales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Perjuicios patrimoniales consecuenciales (si aplica)")
    nuevo_meses_vigencia_rce = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia RCE")
    nuevo_fecha_inicio_vigencia_rce = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia RCE")
    nuevo_fecha_fin_vigencia_rce = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia RCE")
    
    # Póliza Cumplimiento
    nuevo_exige_poliza_cumplimiento = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza de Cumplimiento?")
    nuevo_valor_asegurado_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Cumplimiento")
    nuevo_valor_remuneraciones_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Remuneraciones Mensuales Aseguradas (Cumplimiento)")
    nuevo_valor_servicios_publicos_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Servicios Públicos Asegurados (Cumplimiento)")
    nuevo_valor_iva_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo IVA Asegurado (Cumplimiento)")
    nuevo_valor_otros_cumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cuota de Administración Asegurada (Cumplimiento)")
    # Campos Cumplimiento - Amparos para PROVEEDOR
    nuevo_cumplimiento_amparo_cumplimiento_contrato = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cumplimiento del contrato")
    nuevo_cumplimiento_amparo_buen_manejo_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Buen manejo y correcta inversión del anticipo (si aplica)")
    nuevo_cumplimiento_amparo_amortizacion_anticipo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Correcta amortización del anticipo (si aplica)")
    nuevo_cumplimiento_amparo_salarios_prestaciones = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Salarios, prestaciones sociales e indemnizaciones laborales")
    nuevo_cumplimiento_amparo_aportes_seguridad_social = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Aportes al sistema de seguridad social")
    nuevo_cumplimiento_amparo_calidad_servicio = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Calidad del servicio")
    nuevo_cumplimiento_amparo_estabilidad_obra = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Estabilidad de la obra (si aplica)")
    nuevo_cumplimiento_amparo_calidad_bienes = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Calidad y correcto funcionamiento de bienes (si aplica)")
    nuevo_cumplimiento_amparo_multas = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Multas (si aplica)")
    nuevo_cumplimiento_amparo_clausula_penal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cláusula penal pecuniaria (si aplica)")
    nuevo_cumplimiento_amparo_sanciones_incumplimiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Sanciones por incumplimiento (si aplica)")
    nuevo_meses_vigencia_cumplimiento = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Cumplimiento")
    nuevo_fecha_inicio_vigencia_cumplimiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Cumplimiento")
    nuevo_fecha_fin_vigencia_cumplimiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Cumplimiento")
    
    # Póliza de Arrendamiento
    nuevo_exige_poliza_arrendamiento = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza de Arrendamiento?")
    nuevo_valor_asegurado_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Póliza de Arrendamiento")
    nuevo_valor_remuneraciones_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Remuneraciones Mensuales Aseguradas (Arrendamiento)")
    nuevo_valor_servicios_publicos_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Servicios Públicos Asegurados (Arrendamiento)")
    nuevo_valor_iva_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo IVA Asegurado (Arrendamiento)")
    nuevo_valor_otros_arrendamiento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Cuota de Administración Asegurada (Arrendamiento)")
    nuevo_meses_vigencia_arrendamiento = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Póliza de Arrendamiento")
    nuevo_fecha_inicio_vigencia_arrendamiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Póliza de Arrendamiento")
    nuevo_fecha_fin_vigencia_arrendamiento = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Póliza de Arrendamiento")
    
    # Póliza Todo Riesgo
    nuevo_exige_poliza_todo_riesgo = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Póliza Todo Riesgo?")
    nuevo_valor_asegurado_todo_riesgo = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Todo Riesgo")
    nuevo_meses_vigencia_todo_riesgo = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Todo Riesgo")
    nuevo_fecha_inicio_vigencia_todo_riesgo = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Todo Riesgo")
    nuevo_fecha_fin_vigencia_todo_riesgo = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Todo Riesgo")
    
    # Otras Pólizas (Opcional)
    nuevo_exige_poliza_otra_1 = models.BooleanField(blank=True, null=True, verbose_name="¿Exige Otras Pólizas?")
    nuevo_nombre_poliza_otra_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Nuevo Nombre Otras Pólizas")
    nuevo_valor_asegurado_otra_1 = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="Nuevo Valor Asegurado Otras Pólizas")
    nuevo_meses_vigencia_otra_1 = models.IntegerField(null=True, blank=True, verbose_name="Nuevos Meses de Vigencia Otras Pólizas")
    nuevo_fecha_inicio_vigencia_otra_1 = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Inicio Vigencia Otras Pólizas")
    nuevo_fecha_fin_vigencia_otra_1 = models.DateField(null=True, blank=True, verbose_name="Nueva Fecha Fin Vigencia Otras Pólizas")
    
    # Auditoría
    creado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Creado Por')
    fecha_creacion = models.DateTimeField(default=timezone.now, verbose_name='Fecha de Creación')
    aprobado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Aprobado Por')
    fecha_aprobacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Aprobación')
    modificado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Última Modificación Por')
    fecha_modificacion = models.DateTimeField(default=timezone.now, verbose_name='Fecha de Última Modificación')
    eliminado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Eliminado Por',
        help_text='Usuario que eliminó el Otro Sí'
    )
    fecha_eliminacion = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Eliminación',
        help_text='Fecha y hora de eliminación del Otro Sí'
    )
    url_archivo = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='URL del Archivo Digital',
        help_text='Enlace al archivo digital del Otro Sí (OneDrive, Google Drive, etc.)'
    )

    class Meta:
        verbose_name = 'Otro Sí'
        verbose_name_plural = 'Otros Sí'
        ordering = ['-effective_from', '-version']
        unique_together = [['contrato', 'numero_otrosi']]

    def __str__(self):
        return f"{self.numero_otrosi} - {self.get_tipo_display()} ({self.effective_from})"
    
    def get_estado_vigencia(self, fecha_referencia=None):
        """
        Determina el estado de vigencia del Otro Sí.
        
        Retorna:
        - 'VIGENTE': Si está aprobado y actualmente en vigencia
        - 'VENCIDO': Si está aprobado pero ya pasó su fecha de vigencia
        - 'PENDIENTE': Si está aprobado pero aún no ha iniciado su vigencia
        - None: Si no está aprobado
        """
        from datetime import date
        if fecha_referencia is None:
            fecha_referencia = date.today()
        
        # Solo los aprobados tienen estado de vigencia
        if self.estado != 'APROBADO':
            return None
        
        # Si tiene fecha de fin y ya pasó, está vencido
        if self.effective_to and fecha_referencia > self.effective_to:
            return 'VENCIDO'
        
        # Si la fecha de inicio es en el futuro, está pendiente
        if self.effective_from > fecha_referencia:
            return 'PENDIENTE'
        
        # Si está dentro del rango de vigencia, está vigente
        if self.effective_from <= fecha_referencia:
            if self.effective_to is None or fecha_referencia <= self.effective_to:
                return 'VIGENTE'
        
        return 'VENCIDO'
    
    def is_vigente(self, fecha_referencia=None):
        """Determina si este Otrosí está vigente en una fecha dada"""
        from datetime import date
        if fecha_referencia is None:
            fecha_referencia = date.today()
        
        # Debe estar aprobado
        if self.estado != 'APROBADO':
            return False
        
        # La fecha de referencia debe ser >= effective_from
        if fecha_referencia < self.effective_from:
            return False
        
        # Si hay effective_to, la fecha debe ser <= effective_to
        if self.effective_to and fecha_referencia > self.effective_to:
            return False
        
        return True
    
    def get_cambios_resumen(self):
        """Retorna un resumen de los campos que fueron modificados"""
        cambios = []
        
        # Determinar etiquetas según el tipo de contrato
        es_proveedor = self.contrato.tipo_contrato_cliente_proveedor == 'PROVEEDOR'
        etiqueta_canon = "Valor Mensual" if es_proveedor else "Canon"
        etiqueta_canon_minimo = "Valor Mínimo" if es_proveedor else "Canon Mínimo"
        
        if self.nuevo_valor_canon:
            # Formatear con separador de miles
            valor_formateado = f"{int(self.nuevo_valor_canon):,}".replace(",", ".")
            cambios.append(f"{etiqueta_canon}: ${valor_formateado}")
        if self.nuevo_canon_minimo_garantizado:
            valor_formateado = f"{int(self.nuevo_canon_minimo_garantizado):,}".replace(",", ".")
            cambios.append(f"{etiqueta_canon_minimo}: ${valor_formateado}")
        if self.nuevo_porcentaje_ventas:
            cambios.append(f"% Ventas: {self.nuevo_porcentaje_ventas}%")
        if self.nueva_fecha_final_actualizada:
            cambios.append(f"Fecha Final: {self.nueva_fecha_final_actualizada}")
        if self.nueva_modalidad_pago:
            cambios.append(f"Modalidad: {self.nueva_modalidad_pago}")
        if self.nuevo_plazo_meses:
            cambios.append(f"Plazo: {self.nuevo_plazo_meses} meses")
        if self.nuevo_tipo_condicion_ipc:
            cambios.append(f"IPC: {self.get_nuevo_tipo_condicion_ipc_display()}")
        if self.nuevos_puntos_adicionales_ipc:
            cambios.append(f"Puntos IPC: {self.nuevos_puntos_adicionales_ipc}")
        if self.nueva_periodicidad_ipc:
            cambios.append(f"Periodicidad IPC: {self.get_nueva_periodicidad_ipc_display()}")
        if self.nueva_fecha_aumento_ipc:
            cambios.append(f"Fecha Aumento IPC: {self.nueva_fecha_aumento_ipc.strftime('%d/%m/%Y')}")
        if self.modifica_polizas:
            cambios.append("✓ Incluye modificación de pólizas")
        
        return cambios if cambios else ['Sin cambios específicos registrados']
    
    def save(self, *args, **kwargs):
        """Override save para validaciones y auto-incremento de versión"""
        if not self.pk:  # Nuevo registro
            # Auto-incrementar versión
            ultimo_otrosi = OtroSi.objects.filter(contrato=self.contrato).order_by('-version').first()
            if ultimo_otrosi:
                self.version = ultimo_otrosi.version + 1
            else:
                self.version = 1
            
            # Generar número secuencial basado en el conteo de Otro Sí del contrato
            if not self.numero_otrosi or self.numero_otrosi == 'OS-TEMP':
                cantidad_otrosi = OtroSi.objects.filter(contrato=self.contrato).count()
                self.numero_otrosi = f"OS-{cantidad_otrosi + 1}"
        
        super().save(*args, **kwargs)


class InformeVentas(models.Model):
    """
    Modelo para controlar los informes de ventas mensuales requeridos por contrato.
    Cada contrato que reporta ventas debe tener un informe por cada mes.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ENTREGADO', 'Entregado'),
    ]
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='informes_ventas',
        verbose_name='Contrato'
    )
    mes = models.IntegerField(
        choices=[(i, ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][i-1]) for i in range(1, 13)],
        verbose_name='Mes',
        help_text='Mes del informe'
    )
    año = models.IntegerField(
        verbose_name='Año',
        help_text='Año del informe'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    fecha_entrega = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de Entrega',
        help_text='Fecha en que se entregó el informe'
    )
    fecha_limite = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha Límite',
        help_text='Fecha límite para entregar el informe'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas adicionales sobre el informe'
    )
    registrado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Registrado por'
    )
    fecha_registro = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de registro'
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de actualización'
    )
    url_archivo = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='URL del Archivo Digital',
        help_text='Enlace al archivo digital del informe de ventas (OneDrive, Google Drive, etc.)'
    )

    class Meta:
        verbose_name = 'Informe de Ventas'
        verbose_name_plural = 'Informes de Ventas'
        ordering = ['-año', '-mes', 'contrato']
        unique_together = [['contrato', 'mes', 'año']]
        indexes = [
            models.Index(fields=['contrato', 'año', 'mes']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        meses_dict = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        mes_nombre = meses_dict.get(self.mes, f'Mes {self.mes}')
        return f"{self.contrato.num_contrato} - {mes_nombre}/{self.año} - {self.get_estado_display()}"

    def get_mes_display(self):
        """Retorna el nombre del mes"""
        meses_dict = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        return meses_dict.get(self.mes, f'Mes {self.mes}')

    def marcar_como_entregado(self, fecha_entrega=None):
        """Marca el informe como entregado"""
        self.estado = 'ENTREGADO'
        if fecha_entrega:
            self.fecha_entrega = fecha_entrega
        else:
            self.fecha_entrega = date.today()
        self.save()

    def marcar_como_pendiente(self):
        """Marca el informe como pendiente"""
        self.estado = 'PENDIENTE'
        self.fecha_entrega = None
        self.save()

    def esta_vencido(self):
        """Verifica si el informe está vencido (pendiente y pasó la fecha límite)"""
        if self.estado == 'PENDIENTE' and self.fecha_limite:
            return date.today() > self.fecha_limite
        return False

    def dias_vencido(self):
        """Retorna los días que lleva vencido el informe (0 si no está vencido)"""
        if self.esta_vencido():
            return (date.today() - self.fecha_limite).days
        return 0


class CalculoFacturacionVentas(models.Model):
    """
    Modelo para guardar los cálculos históricos de facturación por ventas.
    Permite consultar posteriormente los cálculos realizados y generar reportes.
    """
    MODALIDAD_CALCULO_CHOICES = [
        ('VARIABLE_PURO', 'Variable Puro'),
        ('HIBRIDO_MIN_GARANTIZADO', 'Híbrido (Min Garantizado)'),
    ]
    
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='calculos_facturacion',
        verbose_name='Contrato'
    )
    informe_ventas = models.ForeignKey(
        InformeVentas,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calculos_facturacion',
        verbose_name='Informe de Ventas',
        help_text='Informe de ventas asociado (opcional)'
    )
    mes = models.IntegerField(
        choices=[(i, ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][i-1]) for i in range(1, 13)],
        verbose_name='Mes',
        help_text='Mes al que corresponden las ventas'
    )
    año = models.IntegerField(
        verbose_name='Año',
        help_text='Año al que corresponden las ventas'
    )
    
    # Datos de entrada
    ventas_totales = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Ventas Totales'
    )
    devoluciones = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name='Devoluciones'
    )
    base_neta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Base Neta',
        help_text='Ventas Totales - Devoluciones'
    )
    
    # Valores vigentes usados en el cálculo
    modalidad_contrato = models.CharField(
        max_length=30,
        choices=MODALIDAD_CALCULO_CHOICES,
        verbose_name='Modalidad del Contrato'
    )
    porcentaje_ventas_vigente = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Porcentaje de Ventas Vigente (%)',
        help_text='Porcentaje vigente al momento del cálculo'
    )
    canon_minimo_garantizado_vigente = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Canon Mínimo Garantizado Vigente',
        help_text='Mínimo garantizado vigente (solo para Híbrido)'
    )
    canon_fijo_vigente = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Canon Fijo Vigente',
        help_text='Canon fijo vigente (si aplica)'
    )
    
    # Resultados del cálculo
    valor_calculado_porcentaje = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Valor Calculado (Base × %)',
        help_text='Base neta × Porcentaje'
    )
    valor_a_facturar_variable = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Valor a Facturar Variable',
        help_text='Valor variable a facturar (después de aplicar mínimo garantizado si aplica)'
    )
    excedente_sobre_minimo = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Excedente sobre Mínimo',
        help_text='Excedente sobre el mínimo garantizado (solo para Híbrido)'
    )
    aplica_variable = models.BooleanField(
        default=False,
        verbose_name='¿Aplica Variable?',
        help_text='Indica si se aplica facturación variable o solo el mínimo garantizado'
    )
    
    # Información de auditoría
    otrosi_referencia = models.ForeignKey(
        'OtroSi',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calculos_facturacion',
        verbose_name='Otro Sí de Referencia',
        help_text='Otro Sí vigente usado para el cálculo'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas adicionales sobre el cálculo'
    )
    calculado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Calculado por'
    )
    fecha_calculo = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Cálculo'
    )

    class Meta:
        verbose_name = 'Cálculo de Facturación por Ventas'
        verbose_name_plural = 'Cálculos de Facturación por Ventas'
        ordering = ['-fecha_calculo', '-año', '-mes']
        indexes = [
            models.Index(fields=['contrato', 'año', 'mes']),
            models.Index(fields=['fecha_calculo']),
        ]

    def __str__(self):
        meses_dict = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        mes_nombre = meses_dict.get(self.mes, f'Mes {self.mes}')
        return f"{self.contrato.num_contrato} - {mes_nombre}/{self.año} - ${self.valor_a_facturar_variable:,.2f}"

    def get_mes_display(self):
        """Retorna el nombre del mes"""
        meses_dict = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        return meses_dict.get(self.mes, f'Mes {self.mes}')
    
    def get_desglose_completo(self):
        """Retorna un diccionario con el desglose completo del cálculo"""
        return {
            'ventas_totales': self.ventas_totales,
            'devoluciones': self.devoluciones,
            'base_neta': self.base_neta,
            'porcentaje_aplicado': self.porcentaje_ventas_vigente,
            'valor_calculado_porcentaje': self.valor_calculado_porcentaje,
            'modalidad': self.get_modalidad_contrato_display(),
            'canon_minimo_garantizado': self.canon_minimo_garantizado_vigente,
            'excedente_sobre_minimo': self.excedente_sobre_minimo,
            'aplica_variable': self.aplica_variable,
            'valor_a_facturar_variable': self.valor_a_facturar_variable,
            'canon_fijo': self.canon_fijo_vigente,
        }


class IPCHistorico(models.Model):
    """
    Modelo para almacenar el histórico de valores del IPC certificado por el DANE.
    Un registro por año, validando que no se dupliquen años.
    """
    año = models.IntegerField(
        unique=True,
        verbose_name='Año',
        help_text='Año del IPC certificado por el DANE'
    )
    valor_ipc = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Valor IPC (%)',
        help_text='Valor del IPC en porcentaje (ej: 5.2 para 5.2%)'
    )
    fecha_certificacion = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de Certificación',
        help_text='Fecha en que el DANE certificó este valor'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas adicionales sobre este valor de IPC'
    )
    creado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Creado Por'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    modificado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Modificado Por'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Modificación'
    )

    class Meta:
        verbose_name = 'IPC Histórico'
        verbose_name_plural = 'IPC Histórico'
        ordering = ['-año']
        indexes = [
            models.Index(fields=['año']),
        ]

    def __str__(self):
        return f"IPC {self.año}: {self.valor_ipc}%"

    def clean(self):
        """Validación personalizada"""
        from django.core.exceptions import ValidationError
        
        # Validar que el año sea razonable
        if self.año is not None and (self.año < 1900 or self.año > 2100):
            raise ValidationError({'año': 'El año debe estar entre 1900 y 2100'})
        
        # Validar que el valor del IPC sea positivo
        if self.valor_ipc is not None and self.valor_ipc < 0:
            raise ValidationError({'valor_ipc': 'El valor del IPC debe ser positivo'})

    def save(self, *args, **kwargs):
        """Override save para validaciones"""
        self.full_clean()
        super().save(*args, **kwargs)


class CalculoIPC(models.Model):
    """
    Modelo para almacenar los cálculos de ajuste de canon por IPC realizados.
    Respalda los cálculos sin crear Otro Sí automáticamente.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APLICADO', 'Aplicado'),
        ('ANULADO', 'Anulado'),
    ]

    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='calculos_ipc',
        verbose_name='Contrato'
    )
    año_aplicacion = models.IntegerField(
        verbose_name='Año de Aplicación',
        help_text='Año para el cual se aplica el ajuste por IPC'
    )
    fecha_aplicacion = models.DateField(
        verbose_name='Fecha de Aplicación',
        help_text='Fecha exacta en que se aplica el ajuste por IPC'
    )
    ipc_historico = models.ForeignKey(
        IPCHistorico,
        on_delete=models.PROTECT,
        related_name='calculos_ipc',
        verbose_name='IPC Histórico',
        help_text='Valor del IPC certificado por el DANE para este año'
    )
    
    # Valores de entrada
    canon_anterior = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Canon Anterior',
        help_text='Canon base sobre el cual se calcula el ajuste'
    )
    canon_anterior_manual = models.BooleanField(
        default=False,
        verbose_name='Canon Anterior Manual',
        help_text='Indica si el canon anterior fue ingresado manualmente'
    )
    fuente_canon_anterior = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Fuente del Canon Anterior',
        help_text='Indica de dónde proviene el canon anterior (Otro Sí, cálculo previo, manual)'
    )
    puntos_adicionales = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Puntos Adicionales IPC',
        help_text='Puntos adicionales pactados en el contrato'
    )
    
    # Valores calculados
    porcentaje_total_aplicar = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Porcentaje Total a Aplicar (%)',
        help_text='IPC + Puntos Adicionales'
    )
    valor_incremento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Valor del Incremento',
        help_text='Valor en pesos del incremento'
    )
    nuevo_canon = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Nuevo Canon',
        help_text='Canon Anterior * (1 + (IPC + Puntos Adicionales)/100)'
    )
    
    # Información adicional
    periodicidad_contrato = models.CharField(
        max_length=20,
        choices=PERIODICIDAD_IPC_CHOICES,
        blank=True,
        null=True,
        verbose_name='Periodicidad del Contrato',
        help_text='Periodicidad configurada en el contrato'
    )
    fecha_aumento_contrato = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de Aumento del Contrato',
        help_text='Fecha exacta configurada en el contrato para el aumento por IPC'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas adicionales sobre este cálculo'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    
    # Auditoría
    calculado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Calculado Por'
    )
    fecha_calculo = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Cálculo'
    )
    aplicado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Aplicado Por'
    )
    fecha_aplicacion_real = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Aplicación Real',
        help_text='Fecha y hora en que se aplicó el cálculo'
    )

    class Meta:
        verbose_name = 'Cálculo de IPC'
        verbose_name_plural = 'Cálculos de IPC'
        ordering = ['-fecha_aplicacion', '-fecha_calculo']
        indexes = [
            models.Index(fields=['contrato', 'fecha_aplicacion']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_calculo']),
        ]
        unique_together = [['contrato', 'fecha_aplicacion']]

    def __str__(self):
        fecha_display = self.fecha_aplicacion.strftime('%d/%m/%Y') if self.fecha_aplicacion else ''
        return f"{self.contrato.num_contrato} - IPC {fecha_display} - ${self.nuevo_canon:,.2f}"

    def get_desglose_calculo(self):
        """Retorna un diccionario con el desglose completo del cálculo"""
        return {
            'canon_anterior': self.canon_anterior,
            'canon_anterior_manual': self.canon_anterior_manual,
            'fuente_canon_anterior': self.fuente_canon_anterior,
            'valor_ipc': self.ipc_historico.valor_ipc,
            'puntos_adicionales': self.puntos_adicionales,
            'porcentaje_total_aplicar': self.porcentaje_total_aplicar,
            'valor_incremento': self.valor_incremento,
            'nuevo_canon': self.nuevo_canon,
        }


class TipoCondicionIPC(models.Model):
    """
    Modelo para gestionar los tipos de condición IPC disponibles en el sistema.
    Permite agregar, editar y eliminar tipos de condición IPC.
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código',
        help_text='Código único del tipo de condición'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre',
        help_text='Nombre descriptivo del tipo de condición'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción',
        help_text='Descripción detallada del tipo de condición'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si este tipo está disponible para usar'
    )
    orden = models.IntegerField(
        default=0,
        verbose_name='Orden',
        help_text='Orden de visualización'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Modificación'
    )

    class Meta:
        verbose_name = 'Tipo de Condición IPC'
        verbose_name_plural = 'Tipos de Condición IPC'
        ordering = ['orden', 'nombre']
        indexes = [
            models.Index(fields=['activo', 'orden']),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.nombre.upper().replace(' ', '_').replace('-', '_')
        super().save(*args, **kwargs)




class PeriodicidadIPC(models.Model):
    """
    Modelo para gestionar las periodicidades de ajuste IPC disponibles.
    Permite agregar, editar y eliminar periodicidades.
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código',
        help_text='Código único de la periodicidad'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre',
        help_text='Nombre descriptivo de la periodicidad'
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción',
        help_text='Descripción detallada de la periodicidad'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si esta periodicidad está disponible para usar'
    )
    orden = models.IntegerField(
        default=0,
        verbose_name='Orden',
        help_text='Orden de visualización'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Modificación'
    )

    class Meta:
        verbose_name = 'Periodicidad IPC'
        verbose_name_plural = 'Periodicidades IPC'
        ordering = ['orden', 'nombre']
        indexes = [
            models.Index(fields=['activo', 'orden']),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.nombre.upper().replace(' ', '_').replace('-', '_')
        super().save(*args, **kwargs)


class SalarioMinimoHistorico(models.Model):
    """
    Modelo para almacenar el histórico de valores del Salario Mínimo Legal Vigente (SMLV).
    Un registro por año, validando que no se dupliquen años.
    """
    año = models.IntegerField(
        unique=True,
        verbose_name='Año',
        help_text='Año del Salario Mínimo Legal Vigente'
    )
    valor_salario_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor Salario Mínimo ($)',
        help_text='Valor del Salario Mínimo Legal Vigente en pesos colombianos'
    )
    variacion_porcentual = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name='Variación Porcentual (%)',
        help_text='Variación porcentual calculada automáticamente comparando con el año anterior'
    )
    fecha_decreto = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de Decreto',
        help_text='Fecha en que se decretó este valor'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas adicionales sobre este valor de Salario Mínimo'
    )
    creado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Creado Por'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    modificado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Modificado Por'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Modificación'
    )

    class Meta:
        verbose_name = 'Salario Mínimo Histórico'
        verbose_name_plural = 'Salario Mínimo Histórico'
        ordering = ['-año']
        indexes = [
            models.Index(fields=['año']),
        ]

    def __str__(self):
        return f"SMLV {self.año}: ${self.valor_salario_minimo:,.2f}"

    def clean(self):
        """Validación personalizada"""
        from django.core.exceptions import ValidationError
        
        # Validar que el año sea razonable
        if self.año is not None and (self.año < 1900 or self.año > 2100):
            raise ValidationError({'año': 'El año debe estar entre 1900 y 2100'})
        
        # Validar que el valor del salario mínimo sea positivo
        if self.valor_salario_minimo is not None and self.valor_salario_minimo < 0:
            raise ValidationError({'valor_salario_minimo': 'El valor del Salario Mínimo debe ser positivo'})
    
    def calcular_variacion_porcentual(self):
        """
        Calcula la variación porcentual comparando con el salario mínimo del año anterior.
        Si no hay año anterior, retorna None.
        """
        from decimal import Decimal
        
        if not self.valor_salario_minimo or not self.año:
            return None
        
        # Buscar el salario mínimo del año anterior
        año_anterior = self.año - 1
        try:
            smlv_anterior = SalarioMinimoHistorico.objects.get(año=año_anterior)
            if not smlv_anterior.valor_salario_minimo or smlv_anterior.valor_salario_minimo <= 0:
                return None
            
            # Calcular variación: ((valor_actual - valor_anterior) / valor_anterior) * 100
            variacion = ((self.valor_salario_minimo - smlv_anterior.valor_salario_minimo) / 
                        smlv_anterior.valor_salario_minimo) * Decimal('100')
            # Redondear a 2 decimales
            return variacion.quantize(Decimal('0.01'))
        except SalarioMinimoHistorico.DoesNotExist:
            # No hay año anterior, es el primer registro
            return None

    def save(self, *args, **kwargs):
        """Override save para calcular variación porcentual y validaciones"""
        # Calcular variación porcentual antes de guardar
        self.variacion_porcentual = self.calcular_variacion_porcentual()
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalcular variación de los años siguientes si este registro fue actualizado
        año_siguiente = self.año + 1
        try:
            smlv_siguiente = SalarioMinimoHistorico.objects.get(año=año_siguiente)
            smlv_siguiente.variacion_porcentual = smlv_siguiente.calcular_variacion_porcentual()
            smlv_siguiente.save(update_fields=['variacion_porcentual'])
        except SalarioMinimoHistorico.DoesNotExist:
            pass


class CalculoSalarioMinimo(models.Model):
    """
    Modelo para almacenar los cálculos de ajuste de canon por Salario Mínimo realizados.
    Respalda los cálculos sin crear Otro Sí automáticamente.
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APLICADO', 'Aplicado'),
        ('ANULADO', 'Anulado'),
    ]

    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='calculos_salario_minimo',
        verbose_name='Contrato'
    )
    año_aplicacion = models.IntegerField(
        verbose_name='Año de Aplicación',
        help_text='Año para el cual se aplica el ajuste por Salario Mínimo'
    )
    fecha_aplicacion = models.DateField(
        verbose_name='Fecha de Aplicación',
        help_text='Fecha exacta en que se aplica el ajuste por Salario Mínimo'
    )
    salario_minimo_historico = models.ForeignKey(
        SalarioMinimoHistorico,
        on_delete=models.PROTECT,
        related_name='calculos_salario_minimo',
        verbose_name='Salario Mínimo Histórico',
        help_text='Valor del Salario Mínimo Legal Vigente para este año'
    )
    
    # Valores de entrada
    canon_anterior = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Canon Anterior',
        help_text='Canon base sobre el cual se calcula el ajuste'
    )
    canon_anterior_manual = models.BooleanField(
        default=False,
        verbose_name='Canon Anterior Manual',
        help_text='Indica si el canon anterior fue ingresado manualmente'
    )
    fuente_canon_anterior = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Fuente del Canon Anterior',
        help_text='Indica de dónde proviene el canon anterior (Otro Sí, cálculo previo, manual)'
    )
    porcentaje_salario_minimo = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Porcentaje Salario Mínimo (%)',
        help_text='Porcentaje del Salario Mínimo pactado en el contrato'
    )
    puntos_adicionales = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Puntos Adicionales (%)',
        help_text='Puntos adicionales pactados en el contrato'
    )
    
    # Valores calculados
    porcentaje_total_aplicar = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name='Porcentaje Total a Aplicar (%)',
        help_text='Porcentaje Salario Mínimo + Puntos Adicionales'
    )
    valor_incremento = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Valor del Incremento',
        help_text='Valor en pesos del incremento'
    )
    nuevo_canon = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name='Nuevo Canon',
        help_text='Canon Anterior * (1 + (Porcentaje Salario Mínimo + Puntos Adicionales)/100)'
    )
    
    # Información adicional
    periodicidad_contrato = models.CharField(
        max_length=20,
        choices=PERIODICIDAD_IPC_CHOICES,
        blank=True,
        null=True,
        verbose_name='Periodicidad del Contrato',
        help_text='Periodicidad configurada en el contrato'
    )
    fecha_aumento_contrato = models.DateField(
        blank=True,
        null=True,
        verbose_name='Fecha de Aumento del Contrato',
        help_text='Fecha exacta configurada en el contrato para el aumento por Salario Mínimo'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones',
        help_text='Notas adicionales sobre este cálculo'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    
    # Auditoría
    calculado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Calculado Por'
    )
    fecha_calculo = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Cálculo'
    )
    aplicado_por = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Aplicado Por'
    )
    fecha_aplicacion_real = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Aplicación Real',
        help_text='Fecha y hora en que se aplicó el cálculo'
    )

    class Meta:
        verbose_name = 'Cálculo de Salario Mínimo'
        verbose_name_plural = 'Cálculos de Salario Mínimo'
        ordering = ['-fecha_aplicacion', '-fecha_calculo']
        indexes = [
            models.Index(fields=['contrato', 'fecha_aplicacion']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_calculo']),
        ]
        unique_together = [['contrato', 'fecha_aplicacion']]

    def __str__(self):
        fecha_display = self.fecha_aplicacion.strftime('%d/%m/%Y') if self.fecha_aplicacion else ''
        return f"{self.contrato.num_contrato} - SMLV {fecha_display} - ${self.nuevo_canon:,.2f}"

    def get_desglose_calculo(self):
        """Retorna un diccionario con el desglose completo del cálculo"""
        return {
            'canon_anterior': self.canon_anterior,
            'canon_anterior_manual': self.canon_anterior_manual,
            'fuente_canon_anterior': self.fuente_canon_anterior,
            'valor_salario_minimo': self.salario_minimo_historico.valor_salario_minimo,
            'porcentaje_salario_minimo': self.porcentaje_salario_minimo,
            'puntos_adicionales': self.puntos_adicionales,
            'porcentaje_total_aplicar': self.porcentaje_total_aplicar,
            'valor_incremento': self.valor_incremento,
            'nuevo_canon': self.nuevo_canon,
        }


class ClienteLicense(models.Model):
    """
    Modelo para la licencia global de la organización
    Una única licencia es compartida por todos los usuarios de la organización
    """
    license_key = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Clave de Licencia',
        help_text='Clave de licencia de Firebase (compartida por todos los usuarios de la organización)'
    )
    is_primary = models.BooleanField(
        default=True,
        verbose_name='Licencia Principal',
        help_text='Indica si esta es la licencia principal activa de la organización. Solo debe haber una licencia principal.'
    )
    customer_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Nombre del Cliente/Organización',
        help_text='Nombre de la organización asociada a esta licencia'
    )
    customer_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name='Email del Cliente',
        help_text='Email de contacto de la organización'
    )
    expiration_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Expiración',
        help_text='Fecha de expiración de la licencia'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activa',
        help_text='Indica si la licencia está activa localmente'
    )
    last_verification = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Última Verificación',
        help_text='Última vez que se verificó la licencia con Firebase'
    )
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('valid', 'Válida'),
            ('expired', 'Expirada'),
            ('invalid', 'Inválida'),
            ('revoked', 'Revocada'),
            ('pending', 'Pendiente'),
        ],
        default='pending',
        verbose_name='Estado de Verificación',
        help_text='Estado actual de la verificación'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Modificación'
    )

    class Meta:
        verbose_name = 'Licencia de Organización'
        verbose_name_plural = 'Licencias de Organización'
        ordering = ['-fecha_modificacion']
        indexes = [
            models.Index(fields=['license_key']),
            models.Index(fields=['is_primary', 'is_active']),
            models.Index(fields=['is_active', 'verification_status']),
        ]
        
    def save(self, *args, **kwargs):
        # Asegurar que solo haya una licencia principal
        if self.is_primary:
            ClienteLicense.objects.filter(is_primary=True).exclude(pk=self.pk if self.pk else None).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_name or 'Organización'} - {self.license_key}"

    def is_expired(self):
        """Verifica si la licencia está expirada"""
        if not self.expiration_date:
            return True
        return timezone.now() > self.expiration_date

    def needs_verification(self):
        """Verifica si necesita verificación (más de 24 horas desde última verificación)"""
        if not self.last_verification:
            return True
        return (timezone.now() - self.last_verification).total_seconds() > 86400  # 24 horas

    def dias_para_vencimiento(self):
        """Calcula los días restantes hasta el vencimiento de la licencia"""
        if not self.expiration_date:
            return None
        ahora = timezone.now()
        diferencia = (self.expiration_date - ahora).total_seconds() / 86400  # Convertir a días
        return int(diferencia)

    def esta_vigente(self):
        """Verifica si la licencia está vigente (no expirada y activa)"""
        if not self.expiration_date:
            return False
        ahora = timezone.now()
        return ahora <= self.expiration_date and self.is_active and self.verification_status == 'valid'

    def obtener_estado_detallado(self):
        """Obtiene un estado detallado de la licencia con información de vencimiento"""
        if self.verification_status == 'revoked':
            return {
                'estado': 'Revocada',
                'vigente': False,
                'dias_vencimiento': None,
                'mensaje': 'La licencia ha sido revocada o cancelada'
            }
        
        if not self.expiration_date:
            return {
                'estado': 'Sin fecha de expiración',
                'vigente': False,
                'dias_vencimiento': None,
                'mensaje': 'No hay fecha de expiración configurada'
            }
        
        dias = self.dias_para_vencimiento()
        
        if dias is None:
            return {
                'estado': 'Desconocido',
                'vigente': False,
                'dias_vencimiento': None,
                'mensaje': 'No se puede calcular el estado'
            }
        
        if dias < 0:
            return {
                'estado': 'Expirada',
                'vigente': False,
                'dias_vencimiento': dias,
                'mensaje': f'La licencia expiró hace {abs(dias)} día(s)'
            }
        elif dias == 0:
            return {
                'estado': 'Vence hoy',
                'vigente': True,
                'dias_vencimiento': 0,
                'mensaje': 'La licencia vence hoy'
            }
        elif dias <= 30:
            return {
                'estado': 'Vigente - Próxima a vencer',
                'vigente': True,
                'dias_vencimiento': dias,
                'mensaje': f'La licencia vence en {dias} día(s)'
            }
        else:
            return {
                'estado': 'Vigente',
                'vigente': True,
                'dias_vencimiento': dias,
                'mensaje': f'La licencia vence en {dias} día(s)'
            }


# ============================================================================
# MODELOS DE CONFIGURACIÓN DE ALERTAS POR EMAIL
# ============================================================================

TIPO_ALERTA_CHOICES = [
    ('VENCIMIENTO_CONTRATOS', 'Vencimiento de Contratos'),
    ('ALERTAS_IPC', 'Alertas IPC'),
    ('ALERTAS_SALARIO_MINIMO', 'Alertas de Ajuste de Salario Mínimo'),
    ('POLIZAS_CRITICAS', 'Pólizas Críticas'),
    ('PREAVISO_RENOVACION', 'Preaviso de Renovación'),
    ('POLIZAS_REQUERIDAS', 'Pólizas Requeridas No Aportadas'),
    ('TERMINACION_ANTICIPADA', 'Terminación Anticipada'),
    ('RENOVACION_AUTOMATICA', 'Renovación Automática'),
]

FRECUENCIA_ENVIO_CHOICES = [
    ('INMEDIATO', 'Inmediato'),
    ('DIARIO', 'Diario'),
    ('SEMANAL', 'Semanal'),
    ('MENSUAL', 'Mensual'),
]

DIAS_SEMANA_CHOICES = [
    (0, 'Lunes'),
    (1, 'Martes'),
    (2, 'Miércoles'),
    (3, 'Jueves'),
    (4, 'Viernes'),
    (5, 'Sábado'),
    (6, 'Domingo'),
]

ESTADO_ENVIO_CHOICES = [
    ('PENDIENTE', 'Pendiente'),
    ('ENVIADO', 'Enviado'),
    ('ERROR', 'Error'),
    ('CANCELADO', 'Cancelado'),
]


class ConfiguracionEmail(AuditoriaMixin):
    """Configuración de servidor SMTP para envío de correos"""
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Configuración',
        help_text='Nombre descriptivo para identificar esta configuración'
    )
    email_host = models.CharField(
        max_length=255,
        verbose_name='Servidor SMTP',
        help_text='Ejemplo: smtp.gmail.com'
    )
    email_port = models.IntegerField(
        default=587,
        verbose_name='Puerto SMTP',
        help_text='Puerto del servidor SMTP (587 para TLS, 465 para SSL)'
    )
    email_use_tls = models.BooleanField(
        default=True,
        verbose_name='Usar TLS',
        help_text='Activar si el servidor requiere TLS'
    )
    email_use_ssl = models.BooleanField(
        default=False,
        verbose_name='Usar SSL',
        help_text='Activar si el servidor requiere SSL'
    )
    email_host_user = models.EmailField(
        verbose_name='Usuario/Email',
        help_text='Email o usuario para autenticación SMTP'
    )
    email_host_password = models.TextField(
        verbose_name='Contraseña Encriptada',
        help_text='Contraseña o token de aplicación (encriptada automáticamente)'
    )
    email_from = models.EmailField(
        verbose_name='Email Remitente',
        help_text='Email que aparecerá como remitente'
    )
    nombre_remitente = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Nombre del Remitente',
        help_text='Nombre que aparecerá junto al email remitente'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Configuración Activa',
        help_text='Solo una configuración puede estar activa'
    )
    
    class Meta:
        verbose_name = 'Configuración de Email'
        verbose_name_plural = 'Configuraciones de Email'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} ({self.email_from})"
    
    def set_password(self, plain_password: str):
        """
        Encripta y guarda la contraseña de email.
        
        Args:
            plain_password: Contraseña en texto plano
        """
        from gestion.utils_encryption import encrypt_value
        try:
            self.email_host_password = encrypt_value(plain_password)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error encriptando contraseña de email: {e}", exc_info=True)
            raise ValueError(f"No se pudo encriptar la contraseña: {str(e)}")
    
    def get_password(self) -> str:
        """
        Desencripta y retorna la contraseña de email.
        
        Returns:
            str: Contraseña desencriptada
            
        Raises:
            ValueError: Si no se puede desencriptar
        """
        from gestion.utils_encryption import decrypt_value
        try:
            return decrypt_value(self.email_host_password)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error desencriptando contraseña de email: {e}", exc_info=True)
            raise ValueError(f"No se pudo desencriptar la contraseña: {str(e)}")
    
    def save(self, *args, **kwargs):
        if self.activo:
            ConfiguracionEmail.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_activa(cls):
        """Obtiene la configuración de email activa"""
        return cls.objects.filter(activo=True).first()


class ConfiguracionAlerta(AuditoriaMixin):
    """Configuración de tipos de alerta y programación de envío"""
    tipo_alerta = models.CharField(
        max_length=50,
        choices=TIPO_ALERTA_CHOICES,
        unique=True,
        verbose_name='Tipo de Alerta',
        help_text='Tipo de alerta a configurar'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Alerta Activa',
        help_text='Activar o desactivar este tipo de alerta'
    )
    frecuencia = models.CharField(
        max_length=20,
        choices=FRECUENCIA_ENVIO_CHOICES,
        default='SEMANAL',
        verbose_name='Frecuencia de Envío',
        help_text='Con qué frecuencia se enviará esta alerta'
    )
    dias_semana = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Días de la Semana',
        help_text='Días de la semana para envío (0=Lunes, 6=Domingo). Solo aplica para frecuencia semanal.'
    )
    hora_envio = models.TimeField(
        default='08:00',
        verbose_name='Hora de Envío',
        help_text='Hora del día para enviar las alertas'
    )
    solo_criticas = models.BooleanField(
        default=False,
        verbose_name='Solo Alertas Críticas',
        help_text='Enviar solo alertas de nivel crítico (danger)'
    )
    asunto = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Asunto Personalizado',
        help_text='Asunto del correo (dejar vacío para usar asunto por defecto)'
    )
    
    class Meta:
        verbose_name = 'Configuración de Alerta'
        verbose_name_plural = 'Configuraciones de Alertas'
        ordering = ['tipo_alerta']
    
    def __str__(self):
        return f"{self.get_tipo_alerta_display()} - {self.get_frecuencia_display()}"
    
    def debe_enviar_hoy(self, fecha_referencia=None):
        """Verifica si debe enviarse la alerta en la fecha indicada"""
        from datetime import datetime
        fecha = fecha_referencia or timezone.now().date()
        dia_semana = fecha.weekday()
        
        if not self.activo:
            return False
        
        if self.frecuencia == 'INMEDIATO':
            return True
        elif self.frecuencia == 'DIARIO':
            return True
        elif self.frecuencia == 'SEMANAL':
            return dia_semana in (self.dias_semana or [])
        elif self.frecuencia == 'MENSUAL':
            return fecha.day == 1
        
        return False


class DestinatarioAlerta(AuditoriaMixin):
    """Destinatarios por tipo de alerta"""
    configuracion_alerta = models.ForeignKey(
        ConfiguracionAlerta,
        on_delete=models.CASCADE,
        related_name='destinatarios',
        verbose_name='Configuración de Alerta'
    )
    email = models.EmailField(
        verbose_name='Email Destinatario'
    )
    nombre = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Nombre',
        help_text='Nombre del destinatario'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    class Meta:
        verbose_name = 'Destinatario de Alerta'
        verbose_name_plural = 'Destinatarios de Alertas'
        unique_together = [['configuracion_alerta', 'email']]
        ordering = ['configuracion_alerta', 'email']
    
    def __str__(self):
        nombre_display = self.nombre or self.email
        return f"{self.configuracion_alerta.get_tipo_alerta_display()} - {nombre_display}"


class HistorialEnvioEmail(AuditoriaMixin):
    """Historial de envíos de correos de alertas"""
    tipo_alerta = models.CharField(
        max_length=50,
        choices=TIPO_ALERTA_CHOICES,
        verbose_name='Tipo de Alerta'
    )
    destinatario = models.EmailField(
        verbose_name='Email Destinatario'
    )
    asunto = models.CharField(
        max_length=500,
        verbose_name='Asunto'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_ENVIO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    fecha_envio = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Envío'
    )
    error_mensaje = models.TextField(
        blank=True,
        null=True,
        verbose_name='Mensaje de Error',
        help_text='Mensaje de error si el envío falló'
    )
    cantidad_alertas = models.IntegerField(
        default=0,
        verbose_name='Cantidad de Alertas',
        help_text='Cantidad de alertas incluidas en el correo'
    )
    
    class Meta:
        verbose_name = 'Historial de Envío de Email'
        verbose_name_plural = 'Historial de Envíos de Email'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['tipo_alerta', '-fecha_creacion']),
            models.Index(fields=['estado', '-fecha_creacion']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_alerta_display()} - {self.destinatario} - {self.get_estado_display()}"


class Clausula(AuditoriaMixin):
    """Modelo para almacenar las cláusulas disponibles en el sistema"""
    titulo = models.CharField(max_length=255, verbose_name='Título de la Cláusula')
    activa = models.BooleanField(default=True, verbose_name='Activa')
    orden = models.IntegerField(default=0, verbose_name='Orden de Visualización')
    
    class Meta:
        verbose_name = 'Cláusula'
        verbose_name_plural = 'Cláusulas'
        ordering = ['orden', 'titulo']
    
    def __str__(self):
        return self.titulo


class ClausulaObligatoria(AuditoriaMixin):
    """Define qué cláusulas son obligatorias para cada tipo de contrato/subtipo"""
    TIPO_CONTRATO_CHOICES = [
        ('CLIENTE', 'Cliente'),
        ('PROVEEDOR', 'Proveedor'),
    ]
    
    clausula = models.ForeignKey(Clausula, on_delete=models.CASCADE, related_name='obligatorias', verbose_name='Cláusula')
    tipo_contrato_cliente_proveedor = models.CharField(
        max_length=20,
        choices=TIPO_CONTRATO_CHOICES,
        verbose_name='Tipo de Contrato'
    )
    tipo_contrato = models.ForeignKey(
        TipoContrato,
        on_delete=models.CASCADE,
        related_name='clausulas_obligatorias',
        blank=True,
        null=True,
        verbose_name='Tipo de Contrato (Cliente)',
        help_text='Si se deja vacío, aplica a todos los tipos de cliente'
    )
    tipo_servicio = models.ForeignKey(
        TipoServicio,
        on_delete=models.CASCADE,
        related_name='clausulas_obligatorias',
        blank=True,
        null=True,
        verbose_name='Tipo de Servicio (Proveedor)',
        help_text='Si se deja vacío, aplica a todos los tipos de proveedor'
    )
    activa = models.BooleanField(default=True, verbose_name='Activa')
    
    class Meta:
        verbose_name = 'Cláusula Obligatoria'
        verbose_name_plural = 'Cláusulas Obligatorias'
        ordering = ['tipo_contrato_cliente_proveedor', 'tipo_contrato', 'tipo_servicio', 'clausula']
        unique_together = [
            ['clausula', 'tipo_contrato_cliente_proveedor', 'tipo_contrato', 'tipo_servicio']
        ]
    
    def __str__(self):
        tipo_detalle = ''
        if self.tipo_contrato_cliente_proveedor == 'CLIENTE':
            tipo_detalle = f' - {self.tipo_contrato.nombre if self.tipo_contrato else "Todos los tipos"}'
        else:
            tipo_detalle = f' - {self.tipo_servicio.nombre if self.tipo_servicio else "Todos los tipos"}'
        return f"{self.clausula.titulo} ({self.get_tipo_contrato_cliente_proveedor_display()}{tipo_detalle})"


class ClausulaContrato(AuditoriaMixin):
    """Relación entre contratos y las cláusulas que tienen"""
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='clausulas', verbose_name='Contrato')
    clausula = models.ForeignKey(Clausula, on_delete=models.CASCADE, related_name='contratos', verbose_name='Cláusula')
    
    class Meta:
        verbose_name = 'Cláusula de Contrato'
        verbose_name_plural = 'Cláusulas de Contratos'
        unique_together = [['contrato', 'clausula']]
        ordering = ['contrato', 'clausula']
    
    def __str__(self):
        return f"{self.contrato.num_contrato} - {self.clausula.titulo}"

