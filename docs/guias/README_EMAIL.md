# Configuración de Alertas por Email

Toda la documentación relacionada con la configuración y uso del sistema de alertas por email.

## 🚀 Inicio Rápido

1. **[Índice de Configuración](INDICE_CONFIGURACION_EMAIL.md)** - Empieza aquí para encontrar lo que necesitas
2. **[Configuración Rápida](CONFIGURACION_RAPIDA_EMAIL.md)** - Configuración en 5 minutos
3. **[Configuración Paso a Paso](CONFIGURAR_EMAIL_PASO_A_PASO.md)** - Guía detallada completa

## 📚 Documentación Completa

- **[Guía de Pruebas](GUIA_PRUEBAS_EMAIL.md)** - Cómo probar el sistema
- **[Sistema de Alertas Email](../sistemas/SISTEMA_ALERTAS_EMAIL.md)** - Documentación técnica completa

## 🛠️ Comandos Útiles

### Configuración Masiva

```bash
# Configurar todas las alertas de una vez
python manage.py configurar_alertas_default --frecuencia SEMANAL --dias 0 --hora 08:00

# Agregar destinatario a todas las alertas
python manage.py configurar_destinatarios_default email@ejemplo.com --nombre "Nombre"
```

### Verificación y Pruebas

```bash
# Verificar estado de configuración
python scripts/verificar_configuracion_email.py

# Enviar alertas manualmente
python manage.py enviar_alertas_email --tipo VENCIMIENTO_CONTRATOS --forzar
```

### Configuración Interactiva

```bash
# Script interactivo de configuración
python scripts/configurar_email.py
```

## 📍 Ubicaciones Importantes

- **Admin Email**: `/admin/gestion/configuracionemail/`
- **Admin Alertas**: `/admin/gestion/configuracionalerta/`
- **Admin Destinatarios**: `/admin/gestion/destinatarioalerta/`
- **Historial Envíos**: `/admin/gestion/historialenvioemail/`

## ✅ Estado Actual

- ✅ Email SMTP configurado
- ✅ 7 tipos de alertas configurados
- ✅ Destinatarios configurados
- ✅ Sistema probado y funcionando






