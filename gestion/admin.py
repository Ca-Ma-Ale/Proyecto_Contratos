from django.contrib import admin
from .models import (
    Tercero, Arrendatario, Local, TipoContrato, TipoServicio, Contrato, Poliza, OtroSi, 
    InformeVentas, CalculoFacturacionVentas, IPCHistorico, CalculoIPC,
    SalarioMinimoHistorico, CalculoSalarioMinimo,
    TipoCondicionIPC, PeriodicidadIPC, ClienteLicense,
    ConfiguracionEmail, ConfiguracionAlerta, DestinatarioAlerta, HistorialEnvioEmail,
    Clausula, ClausulaObligatoria, ClausulaContrato
)
from .forms import ConfiguracionEmailForm


@admin.register(ClienteLicense)
class ClienteLicenseAdmin(admin.ModelAdmin):
    list_display = ('license_key', 'customer_name', 'is_primary', 'verification_status', 'expiration_date', 'last_verification', 'is_active')
    list_filter = ('verification_status', 'is_active', 'is_primary')
    search_fields = ('license_key', 'customer_name', 'customer_email')
    readonly_fields = ('last_verification', 'fecha_creacion', 'fecha_modificacion')
    fieldsets = (
        ('Información de Licencia', {
            'fields': ('license_key', 'is_primary', 'customer_name', 'customer_email')
        }),
        ('Estado', {
            'fields': ('verification_status', 'is_active', 'expiration_date', 'last_verification')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
)


admin.site.register(Tercero)
admin.site.register(Local)
admin.site.register(TipoContrato)
admin.site.register(TipoServicio)
admin.site.register(Contrato)
admin.site.register(Poliza)
admin.site.register(OtroSi)
admin.site.register(InformeVentas)
admin.site.register(CalculoFacturacionVentas)
admin.site.register(IPCHistorico)
admin.site.register(CalculoIPC)
admin.site.register(SalarioMinimoHistorico)
admin.site.register(CalculoSalarioMinimo)
admin.site.register(TipoCondicionIPC)
admin.site.register(PeriodicidadIPC)
admin.site.register(Clausula)
admin.site.register(ClausulaObligatoria)
admin.site.register(ClausulaContrato)


@admin.register(ConfiguracionEmail)
class ConfiguracionEmailAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email_from', 'email_host', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'fecha_creacion')
    search_fields = ('nombre', 'email_from', 'email_host')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por', 'password_display')
    
    form = ConfiguracionEmailForm
    
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'activo')
        }),
        ('Configuración SMTP', {
            'fields': ('email_host', 'email_port', 'email_use_tls', 'email_use_ssl')
        }),
        ('Credenciales', {
            'fields': ('email_host_user', 'password_input', 'password_display'),
            'description': 'La contraseña se encripta automáticamente al guardar. Deje en blanco para mantener la actual.'
        }),
        ('Remitente', {
            'fields': ('email_from', 'nombre_remitente')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'modificado_por', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def password_display(self, obj):
        """Muestra si hay contraseña configurada (sin mostrar el valor)"""
        if obj.pk and obj.email_host_password:
            return "✓ Contraseña configurada (encriptada)"
        return "⚠ No hay contraseña configurada"
    password_display.short_description = 'Estado de Contraseña'
    
    def save_model(self, request, obj, form, change):
        """Encripta la contraseña antes de guardar"""
        # Obtener la contraseña del formulario
        password_input = form.cleaned_data.get('password_input', '').strip()
        
        if password_input:
            # Nueva contraseña proporcionada
            obj.set_password(password_input)
        # Si change=True y no hay password_input, mantener la contraseña actual (no hacer nada)
        # La validación de contraseña requerida se hace en el formulario
        
        super().save_model(request, obj, form, change)


@admin.register(ConfiguracionAlerta)
class ConfiguracionAlertaAdmin(admin.ModelAdmin):
    list_display = ('tipo_alerta', 'activo', 'frecuencia', 'hora_envio', 'solo_criticas', 'get_dias_semana_display')
    list_filter = ('activo', 'frecuencia', 'solo_criticas')
    search_fields = ('tipo_alerta', 'asunto')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por')
    fieldsets = (
        ('Configuración General', {
            'fields': ('tipo_alerta', 'activo', 'asunto')
        }),
        ('Programación', {
            'fields': ('frecuencia', 'dias_semana', 'hora_envio'),
            'description': 'Para frecuencia SEMANAL, ingrese los días como lista JSON: [0] para Lunes, [1] para Martes, etc. Ejemplo: [0, 3] para Lunes y Jueves. (0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo)'
        }),
        ('Filtros', {
            'fields': ('solo_criticas',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'modificado_por', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_dias_semana_display(self, obj):
        """Muestra los días de la semana de forma legible"""
        if not obj.dias_semana:
            return '-'
        dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        return ', '.join([dias_nombres[d] for d in obj.dias_semana if 0 <= d <= 6])
    get_dias_semana_display.short_description = 'Días de la Semana'


@admin.register(DestinatarioAlerta)
class DestinatarioAlertaAdmin(admin.ModelAdmin):
    list_display = ('configuracion_alerta', 'email', 'nombre', 'activo')
    list_filter = ('activo', 'configuracion_alerta')
    search_fields = ('email', 'nombre', 'configuracion_alerta__tipo_alerta')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por')
    fieldsets = (
        ('Información', {
            'fields': ('configuracion_alerta', 'email', 'nombre', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'modificado_por', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HistorialEnvioEmail)
class HistorialEnvioEmailAdmin(admin.ModelAdmin):
    list_display = ('tipo_alerta', 'destinatario', 'estado', 'fecha_envio', 'cantidad_alertas', 'fecha_creacion')
    list_filter = ('estado', 'tipo_alerta', 'fecha_creacion')
    search_fields = ('destinatario', 'asunto', 'error_mensaje')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'modificado_por')
    date_hierarchy = 'fecha_creacion'
    fieldsets = (
        ('Información del Envío', {
            'fields': ('tipo_alerta', 'destinatario', 'asunto', 'estado', 'fecha_envio', 'cantidad_alertas')
        }),
        ('Error', {
            'fields': ('error_mensaje',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'modificado_por', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )