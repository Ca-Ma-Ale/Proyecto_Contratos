# Índice de Configuración de Email

Guía rápida para encontrar la documentación de configuración de alertas por email.

## 📋 Documentación Disponible

### Para Configuración Inicial

1. **[Configuración Rápida](CONFIGURACION_RAPIDA_EMAIL.md)**
   - Configuración en 5 minutos
   - Pasos esenciales
   - Ejemplos comunes

2. **[Configuración Paso a Paso](CONFIGURAR_EMAIL_PASO_A_PASO.md)**
   - Guía detallada con capturas
   - Instrucciones completas
   - Solución de problemas

### Para Pruebas y Verificación

3. **[Guía de Pruebas](GUIA_PRUEBAS_EMAIL.md)**
   - Cómo probar el sistema
   - Scripts de prueba
   - Verificación de envíos

### Documentación Técnica

4. **[Sistema de Alertas Email](../sistemas/SISTEMA_ALERTAS_EMAIL.md)**
   - Documentación completa del sistema
   - API y funciones
   - Personalización avanzada

## 🚀 Inicio Rápido

### Primera Vez

1. Leer: [Configuración Rápida](CONFIGURACION_RAPIDA_EMAIL.md)
2. Ejecutar: `python scripts/configurar_email.py`
3. Verificar: `python scripts/verificar_configuracion_email.py`

### Configuración Masiva

```bash
# Configurar todas las alertas
python manage.py configurar_alertas_default --frecuencia SEMANAL --dias 0 --hora 08:00

# Agregar destinatario a todas las alertas
python manage.py configurar_destinatarios_default email@ejemplo.com --nombre "Nombre"
```

### Comandos Útiles

```bash
# Verificar estado
python scripts/verificar_configuracion_email.py

# Enviar alertas manualmente
python manage.py enviar_alertas_email --tipo VENCIMIENTO_CONTRATOS --forzar

# Ver historial de envíos
# Ir a: /admin/gestion/historialenvioemail/
```

## 📁 Ubicación de Archivos

- **Scripts de configuración**: `scripts/configurar_email.py`
- **Script de verificación**: `scripts/verificar_configuracion_email.py`
- **Comandos Django**: `gestion/management/commands/`
  - `configurar_alertas_default.py`
  - `configurar_destinatarios_default.py`
  - `enviar_alertas_email.py`

## 🔗 Enlaces Rápidos

- Admin de Email: `/admin/gestion/configuracionemail/`
- Admin de Alertas: `/admin/gestion/configuracionalerta/`
- Admin de Destinatarios: `/admin/gestion/destinatarioalerta/`
- Historial de Envíos: `/admin/gestion/historialenvioemail/`






