# Scripts de Automatización

Esta carpeta contiene scripts para automatizar tareas del sistema.

## 📋 Scripts Disponibles

### `backup_daily.sh` (Linux/Unix)
Script para automatizar backups diarios en sistemas Linux/Unix usando cron.

**Configuración:**
1. Editar el script y configurar las rutas del proyecto
2. Dar permisos de ejecución: `chmod +x backup_daily.sh`
3. Agregar a crontab: `crontab -e`
4. Agregar línea: `0 2 * * * /ruta/al/script/backup_daily.sh`

### `backup_daily.bat` (Windows)
Script para automatizar backups diarios en Windows usando Tareas Programadas.

**Configuración:**
1. Editar el script y configurar las rutas del proyecto
2. Abrir Programador de Tareas (taskschd.msc)
3. Crear nueva tarea que ejecute este script
4. Configurar horario deseado

### `aplicar_decoradores.py`
Script de referencia que muestra cómo aplicar decoradores de seguridad a las vistas.

**Uso:**
```bash
python scripts/aplicar_decoradores.py
```

Este script muestra una guía de qué decoradores aplicar a cada vista. Es solo referencia, no modifica archivos automáticamente.

### `configurar_email.py`
Script interactivo para configurar el sistema de alertas por email paso a paso.

**Uso:**
```bash
python scripts/configurar_email.py
```

Este script guía la configuración de:
- Clave de encriptación (si no está configurada)
- Servidor SMTP y credenciales
- Tipos de alertas y programación
- Destinatarios por tipo de alerta

**Recomendado para primera configuración.**

### `verificar_configuracion_email.py`
Script para verificar el estado actual de la configuración de email.

**Uso:**
```bash
python scripts/verificar_configuracion_email.py
```

Muestra el estado de:
- Clave de encriptación
- Configuración SMTP activa
- Configuraciones de alertas y destinatarios

## 📚 Documentación

Para más detalles, consultar:
- `docs/guias/GUIA_BACKUPS_AUTOMATICOS.md` - Guía completa de backups
- `docs/guias/GUIA_PRODUCCION.md` - Guía de producción (incluye sección sobre decoradores)
- `docs/guias/CONFIGURAR_EMAIL_PASO_A_PASO.md` - Guía paso a paso para configurar email
- `docs/guias/CONFIGURACION_RAPIDA_EMAIL.md` - Guía rápida de configuración de email
- `docs/guias/GUIA_PRUEBAS_EMAIL.md` - Guía de pruebas de envío de alertas por email
- `docs/sistemas/SISTEMA_ALERTAS_EMAIL.md` - Documentación completa del sistema de alertas

## ⚙️ Uso Manual

También puedes ejecutar backups manualmente usando el comando Django:

```bash
python manage.py backup_database
```

Ver todas las opciones:
```bash
python manage.py backup_database --help
```

