# Sistema de Alertas por Correo Electrónico

## Descripción

Sistema completo de envío de alertas por correo electrónico con parametrización completa. Permite configurar tipos de alertas, frecuencia de envío (diario, semanal, mensual), días de la semana, destinatarios y más.

## Características

- ✅ Parametrización completa desde el admin de Django
- ✅ Múltiples tipos de alertas configurables
- ✅ Programación flexible (inmediato, diario, semanal, mensual)
- ✅ Selección de días de la semana para envío semanal
- ✅ Múltiples destinatarios por tipo de alerta
- ✅ Filtro de solo alertas críticas
- ✅ Templates HTML personalizados por tipo de alerta
- ✅ Historial completo de envíos
- ✅ Auditoría de todos los envíos

## Instalación

### 1. Aplicar Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Configurar Servidor SMTP

1. Ir al admin de Django: `/admin/`
2. Navegar a **Gestion > Configuraciones de Email**
3. Crear una nueva configuración:
   - **Nombre**: Nombre descriptivo (ej: "Gmail Principal")
   - **Servidor SMTP**: `smtp.gmail.com` (o tu servidor)
   - **Puerto SMTP**: `587` (TLS) o `465` (SSL)
   - **Usar TLS**: Activar si usas puerto 587
   - **Usar SSL**: Activar si usas puerto 465
   - **Usuario/Email**: Tu email o usuario SMTP
   - **Contraseña**: Contraseña o token de aplicación
   - **Email Remitente**: Email que aparecerá como remitente
   - **Nombre del Remitente**: Nombre que aparecerá (opcional)
   - **Configuración Activa**: Activar esta configuración

**Nota**: Solo una configuración puede estar activa a la vez.

### 3. Configurar Tipos de Alertas

1. Ir a **Gestion > Configuraciones de Alertas**
2. Para cada tipo de alerta que quieras usar:
   - **Tipo de Alerta**: Seleccionar el tipo
   - **Alerta Activa**: Activar
   - **Frecuencia de Envío**: 
     - `INMEDIATO`: Se envía siempre que se ejecute el comando
     - `DIARIO`: Se envía todos los días
     - `SEMANAL`: Se envía en los días de la semana seleccionados
     - `MENSUAL`: Se envía el día 1 de cada mes
   - **Días de la Semana**: Para frecuencia semanal, seleccionar días (0=Lunes, 6=Domingo)
   - **Hora de Envío**: Hora del día para enviar (ej: 08:00)
   - **Solo Alertas Críticas**: Activar para enviar solo alertas críticas
   - **Asunto Personalizado**: Opcional, dejar vacío para usar asunto por defecto

**Ejemplo: Enviar todos los lunes a las 8:00 AM**
- Frecuencia: `SEMANAL`
- Días de la Semana: `[0]` (Lunes)
- Hora de Envío: `08:00`

### 4. Configurar Destinatarios

1. Ir a **Gestion > Destinatarios de Alertas**
2. Para cada tipo de alerta, agregar destinatarios:
   - **Configuración de Alerta**: Seleccionar el tipo de alerta
   - **Email Destinatario**: Email del destinatario
   - **Nombre**: Nombre del destinatario (opcional)
   - **Activo**: Activar

## Uso

### Envío Manual

Para enviar todas las alertas programadas para hoy:

```bash
python manage.py enviar_alertas_email
```

Para enviar un tipo específico de alerta:

```bash
python manage.py enviar_alertas_email --tipo VENCIMIENTO_CONTRATOS
```

Para forzar el envío aunque no sea el día programado:

```bash
python manage.py enviar_alertas_email --tipo ALERTAS_IPC --forzar
```

Para usar una fecha de referencia específica:

```bash
python manage.py enviar_alertas_email --fecha 2025-01-15
```

### Programación Automática (Cron)

#### Windows (Programador de Tareas)

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Configurar:
   - **Nombre**: "Enviar Alertas Contratos"
   - **Desencadenador**: Semanal, Lunes, 8:00 AM
   - **Acción**: Iniciar programa
   - **Programa**: `C:\ruta\al\venv\Scripts\python.exe`
   - **Argumentos**: `manage.py enviar_alertas_email`
   - **Iniciar en**: Ruta del proyecto

#### Linux/Mac (Cron)

Editar crontab:

```bash
crontab -e
```

Agregar línea para enviar todos los lunes a las 8:00 AM:

```cron
0 8 * * 1 cd /ruta/al/proyecto && /ruta/al/venv/bin/python manage.py enviar_alertas_email
```

**Ejemplos de expresiones cron:**

- Todos los días a las 8:00 AM: `0 8 * * *`
- Todos los lunes a las 8:00 AM: `0 8 * * 1`
- Lunes y viernes a las 8:00 AM: `0 8 * * 1,5`
- Primer día del mes a las 8:00 AM: `0 8 1 * *`

### PythonAnywhere

En PythonAnywhere, usar las tareas programadas:

1. Ir a **Tasks**
2. Crear nueva tarea:
   - **Command**: `python3.10 /home/tuusuario/mysite/manage.py enviar_alertas_email`
   - **Hour**: 8
   - **Minute**: 0
   - **Day of week**: Monday (o el día que prefieras)

## Tipos de Alertas Disponibles

1. **VENCIMIENTO_CONTRATOS**: Contratos próximos a vencer
2. **ALERTAS_IPC**: Alertas de ajuste IPC pendiente
3. **POLIZAS_CRITICAS**: Pólizas vencidas o próximas a vencer
4. **PREAVISO_RENOVACION**: Contratos que requieren preaviso
5. **POLIZAS_REQUERIDAS**: Pólizas requeridas no aportadas
6. **TERMINACION_ANTICIPADA**: Contratos en período de terminación anticipada
7. **RENOVACION_AUTOMATICA**: Contratos con prórroga automática

## Verificación de Envíos

El historial de todos los envíos se guarda en **Gestion > Historial de Envíos de Email**. Puedes ver:

- Tipo de alerta enviada
- Destinatario
- Estado (Pendiente, Enviado, Error)
- Fecha de envío
- Cantidad de alertas incluidas
- Mensaje de error (si hubo)

## Solución de Problemas

### Error: "No hay configuración de email activa"

- Verificar que existe una configuración de email en el admin
- Activar una configuración de email

### Error: "No hay destinatarios configurados"

- Verificar que el tipo de alerta tiene destinatarios activos
- Ir a Destinatarios de Alertas y agregar destinatarios

### Los correos no se envían

1. Verificar configuración SMTP (credenciales correctas)
2. Para Gmail, usar "Contraseña de aplicación" en lugar de contraseña normal
3. Verificar que el firewall permite conexiones SMTP
4. Revisar el historial de envíos para ver mensajes de error

### Los correos se envían pero no llegan

1. Verificar carpeta de spam
2. Verificar que el email remitente es válido
3. Verificar configuración SPF/DKIM del dominio (si aplica)

## Personalización de Templates

Los templates HTML están en `templates/gestion/emails/`:

- `alerta_generica.html`: Template genérico (fallback)
- `alerta_vencimiento_contratos.html`: Para vencimiento de contratos
- `alerta_alertas_ipc.html`: Para alertas IPC
- `alerta_polizas_criticas.html`: Para pólizas críticas
- `alerta_preaviso_renovacion.html`: Para preaviso de renovación
- `alerta_polizas_requeridas.html`: Para pólizas requeridas
- `alerta_terminacion_anticipada.html`: Para terminación anticipada
- `alerta_renovacion_automatica.html`: Para renovación automática

Puedes personalizar estos templates según tus necesidades.

## Seguridad

- Las contraseñas SMTP se almacenan en texto plano en la BD (considerar encriptación para producción)
- Usar tokens de aplicación en lugar de contraseñas reales cuando sea posible
- Revisar regularmente el historial de envíos
- Limitar acceso al admin solo a usuarios autorizados

