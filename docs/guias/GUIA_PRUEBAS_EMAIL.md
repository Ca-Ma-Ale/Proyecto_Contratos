# Guía de Pruebas de Envío de Alertas por Email

Esta guía te ayudará a probar el sistema de alertas por email antes de pasar a producción.

## Requisitos Previos

1. **Configuración de Email Activa**
   - Ir al admin de Django: `/admin/`
   - Navegar a: **Gestion > Configuraciones de Email**
   - Crear una configuración con tus datos SMTP
   - Activar la configuración

2. **Configuración de Alertas**
   - Ir a: **Gestion > Configuraciones de Alertas**
   - Crear configuraciones para los tipos de alerta que deseas probar
   - Configurar destinatarios en: **Gestion > Destinatarios de Alertas**

## Métodos de Prueba

### Método 1: Script Interactivo (Recomendado)

Ejecuta el script interactivo que te guiará paso a paso:

```bash
python scripts/prueba_envio_email.py
```

Este script te permite:
- Verificar la configuración de email
- Enviar un correo de prueba simple
- Listar configuraciones de alertas
- Probar el envío de alertas específicas

### Método 2: Correo de Prueba Rápido

Para enviar un correo de prueba simple rápidamente:

```bash
python scripts/prueba_email_rapida.py tu-email@ejemplo.com
```

### Método 3: Comando Django (Envío Real de Alertas)

Para probar el envío real de alertas usando el comando de producción:

```bash
# Enviar todas las alertas programadas para hoy
python manage.py enviar_alertas_email

# Enviar un tipo específico de alerta
python manage.py enviar_alertas_email --tipo VENCIMIENTO_CONTRATOS

# Forzar envío aunque no sea el día programado
python manage.py enviar_alertas_email --tipo ALERTAS_IPC --forzar

# Usar una fecha específica de referencia
python manage.py enviar_alertas_email --fecha 2025-01-15
```

## Tipos de Alertas Disponibles

- `VENCIMIENTO_CONTRATOS`: Contratos próximos a vencer
- `ALERTAS_IPC`: Alertas de ajuste IPC pendiente
- `POLIZAS_CRITICAS`: Pólizas vencidas o próximas a vencer
- `PREAVISO_RENOVACION`: Contratos que requieren preaviso
- `POLIZAS_REQUERIDAS`: Pólizas requeridas no aportadas
- `TERMINACION_ANTICIPADA`: Contratos en período de terminación anticipada
- `RENOVACION_AUTOMATICA`: Contratos con prórroga automática

## Verificación de Envíos

Todos los envíos se registran en el historial. Para verificar:

1. Ir al admin: `/admin/`
2. Navegar a: **Gestion > Historial de Envíos de Email**
3. Revisar el estado de cada envío:
   - **PENDIENTE**: En proceso
   - **ENVIADO**: Enviado exitosamente
   - **ERROR**: Error en el envío (ver mensaje de error)

## Solución de Problemas

### Error: "No hay configuración de email activa"

**Solución:**
1. Verificar que existe una configuración en el admin
2. Activar una configuración de email
3. Verificar que la contraseña está correctamente encriptada

### Error: "No hay destinatarios configurados"

**Solución:**
1. Ir a **Destinatarios de Alertas** en el admin
2. Agregar destinatarios para el tipo de alerta
3. Activar los destinatarios

### Los correos no se envían

**Verificaciones:**
1. Revisar configuración SMTP (credenciales correctas)
2. Para Gmail, usar "Contraseña de aplicación" en lugar de contraseña normal
3. Verificar que el firewall permite conexiones SMTP
4. Revisar el historial de envíos para ver mensajes de error específicos

### Los correos se envían pero no llegan

**Verificaciones:**
1. Revisar carpeta de spam
2. Verificar que el email remitente es válido
3. Verificar configuración SPF/DKIM del dominio (si aplica)

## Checklist Antes de Producción

- [ ] Configuración de email activa y probada
- [ ] Correo de prueba recibido exitosamente
- [ ] Todos los tipos de alerta configurados
- [ ] Destinatarios configurados para cada tipo de alerta
- [ ] Historial de envíos funcionando correctamente
- [ ] Templates de email personalizados (opcional)
- [ ] Programación de alertas configurada (frecuencia, días, hora)
- [ ] Prueba de envío de cada tipo de alerta realizada

## Próximos Pasos

Una vez que las pruebas sean exitosas:

1. Configurar tarea programada (cron o programador de tareas)
2. Monitorear el historial de envíos regularmente
3. Revisar y ajustar la programación según necesidades
4. Personalizar templates de email si es necesario

Ver documentación completa en: `docs/sistemas/SISTEMA_ALERTAS_EMAIL.md`

