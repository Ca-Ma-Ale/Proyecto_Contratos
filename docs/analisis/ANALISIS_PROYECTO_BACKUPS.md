# 📊 Análisis del Proyecto y Gestión de Backups en Producción

## 🔍 Análisis del Proyecto

### Descripción General

**Sistema de Gestión de Contratos de Arrendamiento** - Aplicación web desarrollada con Django 5.0+ para la gestión completa de contratos comerciales de arrendamiento.

### Arquitectura y Tecnologías

- **Framework:** Django 5.0+
- **Lenguaje:** Python 3.10+
- **Base de Datos:** SQLite (desarrollo) / MySQL compatible (producción)
- **Frontend:** Bootstrap 5.3, Font Awesome 6.0
- **Plataforma de Deployment:** PythonAnywhere (recomendada)

### Módulos Principales

1. **Gestión de Contratos**
   - Contratos simples (canon fijo)
   - Contratos complejos (cánones híbridos, periodos de gracia)
   - Modalidades flexibles de pago

2. **Dashboard de Alertas**
   - Vencimientos de contratos
   - Estado de pólizas
   - Preavisos de renovación
   - Recordatorios de reportes

3. **Módulo Otro Sí**
   - Modificaciones contractuales
   - Actualización automática de contratos

4. **Gestión de Pólizas**
   - Seguros de cumplimiento, RCE, arrendamiento
   - Estados calculados automáticamente

5. **Sistema de Autenticación**
   - Login/logout con control de acceso
   - Protección contra fuerza bruta (django-axes)
   - Control de sesiones seguro

### Estado del Proyecto

✅ **COMPLETO Y FUNCIONANDO**
- Sistema de autenticación implementado
- Módulos principales operativos
- Formateo automático en todos los módulos
- Dashboard con alertas avanzadas
- Listo para producción

---

## 💾 Sistema de Gestión de Backups

### Arquitectura del Sistema de Backups

El proyecto incluye un sistema completo y automatizado de backups con las siguientes características:

#### 1. Comando Django Personalizado

**Ubicación:** `gestion/management/commands/backup_database.py`

**Funcionalidades:**
- Backup en formato JSON (dumpdata de Django)
- Backup en formato SQLite (copia directa del archivo)
- Soporte para ambos formatos simultáneamente
- Limpieza automática de backups antiguos
- Integración con servicio de backup remoto

**Uso básico:**
```bash
python manage.py backup_database
```

**Opciones disponibles:**
```bash
# Formato específico
python manage.py backup_database --format json
python manage.py backup_database --format sqlite
python manage.py backup_database --format both  # Por defecto

# Configuración de retención
python manage.py backup_database --keep-days 30  # Por defecto: 30 días

# Directorio personalizado
python manage.py backup_database --output-dir /ruta/backups

# Envío remoto
python manage.py backup_database --remote
python manage.py backup_database --no-remote
```

#### 2. Servicio de Backup Remoto

**Ubicación:** `gestion/services/backup_remote.py`

**Destinos soportados:**
- **OneDrive:** Copia directa a carpeta sincronizada
- **Google Drive:** Copia directa a carpeta sincronizada
- **SFTP/SCP:** Envío a servidor remoto
- **AWS S3:** Almacenamiento en la nube
- **Copia Local:** Para sincronización automática con servicios de nube

**Características:**
- Configuración mediante variables de entorno
- Notificaciones por email opcionales
- Manejo de errores robusto
- Callbacks de éxito/error

#### 3. Scripts de Automatización

**Linux/Unix:** `scripts/backup_daily.sh`
- Configurable para ejecución con cron
- Soporte para envío remoto automático

**Windows:** `scripts/backup_daily.bat`
- Configurable para Tareas Programadas de Windows
- Soporte para envío remoto automático

---

## 🚀 Gestión de Backups en Producción (Después del Deployment)

### Escenario: PythonAnywhere

Una vez desplegado el proyecto en PythonAnywhere, el sistema de backups se gestiona de la siguiente manera:

### 1. Configuración Inicial Post-Deployment

#### Paso 1: Crear Directorio de Backups

```bash
# Conectarse a PythonAnywhere vía SSH o Bash Console
cd ~/Proyecto_Contratos
mkdir -p backups
chmod 755 backups
```

#### Paso 2: Configurar Variables de Entorno

Editar el archivo `.env` en PythonAnywhere:

```env
# Habilitar backup remoto (opcional pero recomendado)
BACKUP_REMOTE_ENABLED=True

# Elegir destino remoto
BACKUP_REMOTE_DESTINATION=sftp  # o onedrive, s3, local_copy

# Configuración SFTP (ejemplo)
BACKUP_SFTP_HOST=servidor-backup.empresa.com
BACKUP_SFTP_USER=backup_user
BACKUP_SFTP_PASSWORD=password_seguro
BACKUP_SFTP_PATH=/backups/contratos
BACKUP_SFTP_PORT=22

# Notificaciones por email (opcional)
BACKUP_EMAIL_NOTIFICATIONS=True
BACKUP_EMAIL_RECIPIENTS=admin@empresa.com,tecnico@empresa.com
```

**Nota:** Para OneDrive o Google Drive, usar `local_copy` si el servidor tiene acceso a carpetas sincronizadas.

#### Paso 3: Probar Backup Manual

```bash
# Activar entorno virtual
workon contratos_env

# Ejecutar backup de prueba
cd ~/Proyecto_Contratos
python manage.py backup_database --keep-days 30 --format both --remote

# Verificar que se crearon los archivos
ls -lh backups/
```

### 2. Automatización de Backups Diarios

#### Opción A: Scheduled Tasks de PythonAnywhere (Recomendado)

1. **Ir al Dashboard de PythonAnywhere**
   - Navegar a la pestaña "Tasks"

2. **Crear nueva tarea programada:**
   - **Hora:** 02:00 (o la hora deseada)
   - **Comando:**
     ```bash
     cd ~/Proyecto_Contratos && workon contratos_env && python manage.py backup_database --keep-days 30 --format both --remote
     ```
   - **Descripción:** "Backup diario de base de datos"

3. **Guardar la tarea**

4. **Verificar logs:**
   - Los logs aparecerán en la sección de logs de la tarea
   - Revisar periódicamente para asegurar que los backups se ejecutan correctamente

#### Opción B: Cron Job (Si tienes acceso SSH completo)

1. **Editar el script de backup:**
   ```bash
   nano ~/Proyecto_Contratos/scripts/backup_daily.sh
   ```

2. **Configurar rutas:**
   ```bash
   PROJECT_DIR="/home/tu-usuario/Proyecto_Contratos"
   VENV_DIR="$PROJECT_DIR/venv"  # O usar workon si está disponible
   BACKUP_DIR="$PROJECT_DIR/backups"
   KEEP_DAYS=30
   ```

3. **Dar permisos de ejecución:**
   ```bash
   chmod +x ~/Proyecto_Contratos/scripts/backup_daily.sh
   ```

4. **Agregar a crontab:**
   ```bash
   crontab -e
   ```

5. **Agregar línea:**
   ```cron
   0 2 * * * /home/tu-usuario/Proyecto_Contratos/scripts/backup_daily.sh >> /home/tu-usuario/Proyecto_Contratos/logs/backup.log 2>&1
   ```

### 3. Estructura de Backups en Producción

```
~/Proyecto_Contratos/
├── backups/
│   ├── backup_20250127_020000.json          # Backup JSON del día
│   ├── backup_db_20250127_020000.sqlite3    # Backup SQLite del día
│   ├── backup_20250126_020000.json          # Backup del día anterior
│   ├── backup_db_20250126_020000.sqlite3    # Backup SQLite del día anterior
│   └── ...                                  # Backups de los últimos 30 días
```

**Características:**
- Nombres con timestamp: `backup_YYYYMMDD_HHMMSS.json`
- Formato JSON: Contiene todos los datos serializados (portable)
- Formato SQLite: Copia exacta de la base de datos (rápida restauración)
- Retención: 30 días por defecto (configurable)

### 4. Envío Remoto de Backups

#### Configuración SFTP (Recomendado para Producción)

**Ventajas:**
- Almacenamiento seguro en servidor dedicado
- Control total sobre los backups
- No depende de servicios de terceros

**Configuración:**
```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=sftp
BACKUP_SFTP_HOST=backup.empresa.com
BACKUP_SFTP_USER=backup_user
BACKUP_SFTP_PASSWORD=password_seguro
BACKUP_SFTP_PATH=/backups/contratos
BACKUP_SFTP_PORT=22
```

**Requisitos:**
- Servidor SFTP configurado
- Credenciales de acceso
- Espacio suficiente en el servidor remoto

#### Configuración AWS S3

**Ventajas:**
- Escalabilidad ilimitada
- Alta disponibilidad
- Versionado de archivos

**Configuración:**
```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=s3
BACKUP_AWS_S3_BUCKET=backups-empresa-contratos
BACKUP_AWS_ACCESS_KEY=tu_access_key
BACKUP_AWS_SECRET_KEY=tu_secret_key
BACKUP_AWS_REGION=us-east-1
```

**Requisitos:**
- Cuenta AWS
- Bucket S3 creado
- AWS CLI instalado (`pip install awscli`)

#### Configuración OneDrive/Google Drive

**Ventajas:**
- Integración con servicios existentes
- Sincronización automática
- Acceso desde cualquier dispositivo

**Configuración (usando local_copy):**
```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=local_copy
BACKUP_LOCAL_COPY_PATH=/home/tu-usuario/OneDrive/Backups/Contratos
```

**Nota:** Requiere que OneDrive/Google Drive esté montado en el servidor.

### 5. Monitoreo y Notificaciones

#### Notificaciones por Email

Configurar en `.env`:
```env
BACKUP_EMAIL_NOTIFICATIONS=True
BACKUP_EMAIL_RECIPIENTS=admin@empresa.com,tecnico@empresa.com
```

**Información incluida en las notificaciones:**
- Estado del backup (éxito/error)
- Archivos procesados
- Destino del backup remoto
- Detalles de errores (si aplica)

**Requisitos:**
- Configuración SMTP en `settings_production.py`
- Variables de entorno de email configuradas

#### Verificación Manual

```bash
# Listar backups locales
ls -lh ~/Proyecto_Contratos/backups/

# Verificar tamaño total
du -sh ~/Proyecto_Contratos/backups/

# Verificar backups remotos (SFTP)
ssh backup_user@backup.empresa.com "ls -lh /backups/contratos/"

# Verificar backups en S3
aws s3 ls s3://backups-empresa-contratos/backups/contratos/
```

### 6. Restauración de Backups

#### Restaurar desde Backup JSON

```bash
# Activar entorno virtual
workon contratos_env

# Detener la aplicación (si está corriendo)
# En PythonAnywhere: Reload web app → Stop

# Restaurar backup
cd ~/Proyecto_Contratos
python manage.py loaddata backups/backup_20250127_020000.json

# Reiniciar aplicación
# En PythonAnywhere: Reload web app → Start
```

#### Restaurar desde Backup SQLite

```bash
# Detener la aplicación
# En PythonAnywhere: Reload web app → Stop

# Hacer backup del archivo actual (por seguridad)
cp ~/Proyecto_Contratos/db.sqlite3 ~/Proyecto_Contratos/db.sqlite3.backup

# Restaurar backup SQLite
cp ~/Proyecto_Contratos/backups/backup_db_20250127_020000.sqlite3 ~/Proyecto_Contratos/db.sqlite3

# Reiniciar aplicación
# En PythonAnywhere: Reload web app → Start
```

#### Restaurar desde Backup Remoto

```bash
# Descargar backup desde SFTP
scp backup_user@backup.empresa.com:/backups/contratos/backup_20250127_020000.json ~/Proyecto_Contratos/backups/

# Descargar desde S3
aws s3 cp s3://backups-empresa-contratos/backups/contratos/backup_20250127_020000.json ~/Proyecto_Contratos/backups/

# Luego restaurar usando los métodos anteriores
```

### 7. Mejores Prácticas

#### Retención de Backups

- **Backups diarios:** Mantener últimos 30 días (configuración por defecto)
- **Backups semanales:** Considerar mantener backups semanales por 3-6 meses
- **Backups mensuales:** Mantener backups mensuales por 1-2 años

**Implementación:**
```bash
# Backup diario (automático)
python manage.py backup_database --keep-days 30

# Backup semanal (manual o script adicional)
python manage.py backup_database --output-dir ~/backups/semanales --keep-days 0
# Luego mover a ubicación de largo plazo
```

#### Seguridad

1. **Encriptación:** Considerar encriptar backups antes de enviarlos remotamente
2. **Permisos:** Asegurar que solo usuarios autorizados tengan acceso a backups
3. **Credenciales:** Nunca almacenar credenciales en el código, usar variables de entorno
4. **Pruebas:** Probar restauración periódicamente (mensualmente recomendado)

#### Espacio en Disco

- **Monitoreo:** Verificar espacio disponible regularmente
- **Limpieza:** El sistema limpia automáticamente backups antiguos
- **Compresión:** Considerar comprimir backups antiguos si el espacio es limitado

```bash
# Comprimir backups antiguos (opcional)
gzip ~/Proyecto_Contratos/backups/backup_*.json
gzip ~/Proyecto_Contratos/backups/backup_db_*.sqlite3
```

### 8. Solución de Problemas Comunes

#### Error: "Backup remoto deshabilitado"

**Solución:**
- Verificar que `BACKUP_REMOTE_ENABLED=True` en `.env`
- Verificar que se está usando el flag `--remote` o que la variable está configurada

#### Error: "Ruta de SFTP no configurada"

**Solución:**
- Verificar todas las variables de entorno de SFTP en `.env`
- Probar conexión manual: `ssh backup_user@backup.empresa.com`

#### Error: "Permiso denegado"

**Solución:**
```bash
# Verificar permisos del directorio de backups
chmod 755 ~/Proyecto_Contratos/backups
chown tu-usuario:tu-usuario ~/Proyecto_Contratos/backups
```

#### Error: "Base de datos bloqueada"

**Solución:**
- Asegurar que la aplicación está detenida durante el backup
- O usar backup JSON que no requiere bloqueo completo

#### Backup muy grande

**Solución:**
```bash
# Usar solo formato JSON (más pequeño)
python manage.py backup_database --format json

# O comprimir backups
gzip ~/Proyecto_Contratos/backups/backup_*.json
```

---

## 📋 Checklist de Configuración Post-Deployment

- [ ] Directorio `backups/` creado con permisos adecuados
- [ ] Variables de entorno configuradas en `.env`
- [ ] Backup manual probado exitosamente
- [ ] Tarea programada configurada en PythonAnywhere
- [ ] Envío remoto configurado y probado
- [ ] Notificaciones por email configuradas (opcional)
- [ ] Proceso de restauración probado
- [ ] Documentación de ubicación de backups actualizada
- [ ] Monitoreo de espacio en disco configurado
- [ ] Plan de retención de backups definido

---

## 📚 Referencias

- **Guía completa de backups:** `docs/guias/GUIA_BACKUPS_AUTOMATICOS.md`
- **Configuración de ejemplo:** `backup_config_example.env`
- **Scripts de automatización:** `scripts/backup_daily.sh` y `scripts/backup_daily.bat`
- **Comando Django:** `gestion/management/commands/backup_database.py`
- **Servicio remoto:** `gestion/services/backup_remote.py`

---

**Última actualización:** Enero 2025  
**Compatible con:** Django 5.0+, Python 3.10+, PythonAnywhere
