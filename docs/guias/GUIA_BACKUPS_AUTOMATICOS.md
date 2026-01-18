# 💾 Guía de Backups Automáticos

## Descripción

Sistema automatizado para realizar backups diarios de la base de datos del sistema de gestión de contratos.

---

## 🚀 Uso Rápido

### Backup Manual

```bash
# Activar entorno virtual
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Ejecutar backup
python manage.py backup_database
```

### Opciones del Comando

```bash
# Backup solo en formato JSON
python manage.py backup_database --format json

# Backup solo en formato SQLite
python manage.py backup_database --format sqlite

# Backup en ambos formatos (por defecto)
python manage.py backup_database --format both

# Especificar directorio de salida
python manage.py backup_database --output-dir /ruta/backups

# Mantener backups por 60 días (por defecto: 30)
python manage.py backup_database --keep-days 60
```

---

## 📁 Ubicación de Backups

Por defecto, los backups se guardan en:
```
Proyecto_Contratos/
  └── backups/
      ├── backup_20241215_143022.json
      ├── backup_db_20241215_143022.sqlite3
      └── ...
```

---

## ⚙️ Configuración Automática

### Linux/Unix (Cron Job)

1. **Editar el script de backup:**
   ```bash
   nano scripts/backup_daily.sh
   ```
   
2. **Configurar las rutas:**
   ```bash
   PROJECT_DIR="/ruta/completa/al/Proyecto_Contratos"
   VENV_DIR="$PROJECT_DIR/venv"
   ```

3. **Dar permisos de ejecución:**
   ```bash
   chmod +x scripts/backup_daily.sh
   ```

4. **Agregar a crontab:**
   ```bash
   crontab -e
   ```
   
5. **Agregar línea para backup diario a las 2:00 AM:**
   ```cron
   0 2 * * * /ruta/completa/al/Proyecto_Contratos/scripts/backup_daily.sh >> /ruta/completa/al/Proyecto_Contratos/logs/backup.log 2>&1
   ```

6. **Verificar que cron está funcionando:**
   ```bash
   crontab -l
   ```

**Ejemplos de horarios:**
- `0 2 * * *` - Diario a las 2:00 AM
- `0 */6 * * *` - Cada 6 horas
- `0 2 * * 0` - Semanal (domingos a las 2:00 AM)

---

### Windows (Tareas Programadas)

1. **Abrir el Programador de Tareas:**
   - Presionar `Win + R`
   - Escribir `taskschd.msc` y presionar Enter

2. **Crear Tarea Básica:**
   - Clic derecho en "Tareas Programadas" → "Crear Tarea Básica"
   - Nombre: "Backup Diario Contratos"
   - Descripción: "Backup automático diario de la base de datos"

3. **Configurar Disparador:**
   - Frecuencia: Diariamente
   - Hora: 2:00 AM (o la hora deseada)
   - Repetir: Según necesidad

4. **Configurar Acción:**
   - Acción: "Iniciar un programa"
   - Programa/script: `C:\ruta\al\proyecto\scripts\backup_daily.bat`
   - Iniciar en: `C:\ruta\al\proyecto`

5. **Editar el script .bat:**
   - Abrir `scripts/backup_daily.bat` con un editor de texto
   - Configurar las rutas:
     ```batch
     set PROJECT_DIR=C:\Users\DELL\OneDrive - GLOBAL ANALITICS SAS\Proyecto_Contratos
     set VENV_DIR=%PROJECT_DIR%\venv
     ```

6. **Configurar Condiciones (Opcional):**
   - En la pestaña "Condiciones":
     - ✅ Activar la tarea solo si el equipo está conectado a la alimentación de CA
     - ✅ Activar la tarea solo si hay una conexión de red disponible

7. **Guardar y Probar:**
   - Guardar la tarea
   - Clic derecho → "Ejecutar" para probar

---

### PythonAnywhere (Scheduled Tasks)

1. **Ir a la pestaña "Tasks" en el dashboard**

2. **Crear nueva tarea:**
   - Hora: 02:00 (o la deseada)
   - Comando:
     ```bash
     cd /home/tu-usuario/tu-repositorio && workon contratos_env && python manage.py backup_database --keep-days 30
     ```

3. **Guardar la tarea**

4. **Verificar logs:**
   - Los logs aparecerán en la sección de logs de la tarea

---

## 🔄 Restaurar un Backup

### Restaurar desde JSON

```bash
# Activar entorno virtual
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Restaurar backup JSON
python manage.py loaddata backups/backup_20241215_143022.json
```

### Restaurar desde SQLite

```bash
# Detener el servidor si está corriendo
# Ctrl+C en la terminal del servidor

# Hacer backup del archivo actual (por si acaso)
cp db.sqlite3 db.sqlite3.backup

# Restaurar backup SQLite
cp backups/backup_db_20241215_143022.sqlite3 db.sqlite3

# Reiniciar servidor
python manage.py runserver
```

---

## 📊 Limpieza Automática

El comando de backup elimina automáticamente los backups más antiguos que el número de días especificado:

```bash
# Mantener backups por 30 días (por defecto)
python manage.py backup_database --keep-days 30

# Mantener backups por 60 días
python manage.py backup_database --keep-days 60

# No eliminar backups antiguos
python manage.py backup_database --keep-days 0
```

---

## 🔐 Backup Remoto Automático

El sistema incluye un módulo integrado para enviar backups automáticamente a ubicaciones remotas. **No requiere configuración manual en los scripts.**

### Configuración Rápida

1. **Copiar configuración de ejemplo:**
   ```bash
   # Copiar el archivo de ejemplo
   cp backup_config_example.env .env
   ```

2. **Editar `.env` y configurar:**
   ```env
   # Habilitar backup remoto
   BACKUP_REMOTE_ENABLED=True
   
   # Elegir destino
   BACKUP_REMOTE_DESTINATION=onedrive
   
   # Configurar ruta (ejemplo para OneDrive en Windows)
   BACKUP_ONEDRIVE_PATH=C:\Users\Usuario\OneDrive
   ```

3. **Ejecutar backup con envío remoto:**
   ```bash
   python manage.py backup_database --remote
   ```

### Destinos Soportados

#### 1. OneDrive (Windows/Linux)

```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=onedrive
BACKUP_ONEDRIVE_PATH=C:\Users\Usuario\OneDrive
```

**Ventajas:**
- Sincronización automática con la nube
- Acceso desde cualquier dispositivo
- Integración nativa en Windows

#### 2. Google Drive

```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=google_drive
BACKUP_GOOGLE_DRIVE_PATH=C:\Users\Usuario\Google Drive
```

#### 3. Servidor Remoto (SFTP/SCP)

```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=sftp
BACKUP_SFTP_HOST=servidor.example.com
BACKUP_SFTP_USER=usuario
BACKUP_SFTP_PASSWORD=password_seguro
BACKUP_SFTP_PATH=/backups/contratos
BACKUP_SFTP_PORT=22
```

**Nota:** Para usar autenticación por clave SSH, dejar `BACKUP_SFTP_PASSWORD` vacío y configurar SSH keys.

#### 4. AWS S3

```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=s3
BACKUP_AWS_S3_BUCKET=mi-bucket-backups
BACKUP_AWS_ACCESS_KEY=tu_access_key
BACKUP_AWS_SECRET_KEY=tu_secret_key
BACKUP_AWS_REGION=us-east-1
```

**Requisitos:** Instalar AWS CLI (`pip install awscli`)

#### 5. Copia Local (Sincronización Automática)

```env
BACKUP_REMOTE_ENABLED=True
BACKUP_REMOTE_DESTINATION=local_copy
BACKUP_LOCAL_COPY_PATH=C:\Users\Usuario\OneDrive\Backups\Contratos
```

Útil cuando OneDrive/Google Drive se sincronizan automáticamente desde una carpeta local.

### Notificaciones por Email

Para recibir notificaciones sobre el resultado de los backups:

```env
BACKUP_EMAIL_NOTIFICATIONS=True
BACKUP_EMAIL_RECIPIENTS=admin@empresa.com,tecnico@empresa.com
```

**Requisitos:** Configurar SMTP en `settings.py` o `settings_production.py`

### Uso en Scripts Automatizados

Los scripts `backup_daily.sh` y `backup_daily.bat` ya incluyen el flag `--remote` automáticamente. El envío remoto se controla mediante variables de entorno en `.env`.

**Ejemplo de uso manual:**
```bash
# Con envío remoto (usa configuración de .env)
python manage.py backup_database --remote

# Sin envío remoto (sobrescribe configuración)
python manage.py backup_database --no-remote
```

### Verificación

Después de ejecutar un backup, verás mensajes como:

```
[OK] Backup completado exitosamente
Enviando backup a ubicación remota...
[OK] Backups copiados a OneDrive: 2 archivos
Destino: C:\Users\Usuario\OneDrive\backups\contratos
```

### Solución de Problemas

**Error: "Backup remoto deshabilitado"**
- Verificar que `BACKUP_REMOTE_ENABLED=True` en `.env`

**Error: "Ruta de OneDrive no configurada"**
- Verificar que `BACKUP_ONEDRIVE_PATH` esté configurado correctamente
- Verificar que la ruta existe y es accesible

**Error: "sshpass no está instalado" (SFTP)**
- Instalar: `sudo apt install sshpass` (Linux)
- O configurar autenticación por clave SSH

**Error: "AWS CLI no está instalado"**
- Instalar: `pip install awscli`

---

## 📝 Verificación de Backups

### Verificar que los backups se están creando

```bash
# Listar backups
ls -lh backups/

# Ver tamaño de backups
du -sh backups/

# Verificar contenido de backup JSON
python manage.py loaddata backups/backup_20241215_143022.json --dry-run
```

### Monitoreo

El sistema incluye notificaciones automáticas por email cuando está configurado:

```env
# En .env
BACKUP_EMAIL_NOTIFICATIONS=True
BACKUP_EMAIL_RECIPIENTS=admin@empresa.com
```

Las notificaciones se envían automáticamente después de cada backup con:
- Estado del backup (éxito/error)
- Archivos procesados
- Destino del backup remoto
- Detalles de errores (si aplica)

---

## ⚠️ Consideraciones Importantes

1. **Espacio en disco:**
   - Monitorear el espacio disponible
   - Los backups pueden ocupar varios MB/GB según el tamaño de la BD
   - Configurar `--keep-days` apropiadamente

2. **Permisos:**
   - Asegurar que el usuario que ejecuta el backup tenga permisos de escritura
   - Verificar permisos del directorio `backups/`

3. **Seguridad:**
   - Los backups contienen datos sensibles
   - Encriptar backups si se almacenan en ubicaciones remotas
   - No subir backups a repositorios Git (ya está en .gitignore)

4. **Pruebas:**
   - Probar la restauración periódicamente
   - Verificar que los backups no estén corruptos

5. **Documentación:**
   - Mantener registro de dónde se almacenan los backups
   - Documentar procedimientos de restauración

---

## 🆘 Solución de Problemas

### Error: "No se puede crear directorio backups"

```bash
# Crear directorio manualmente
mkdir backups
chmod 755 backups  # Linux
```

### Error: "Permiso denegado"

```bash
# Verificar permisos
ls -la backups/

# Cambiar propietario (Linux)
sudo chown -R usuario:usuario backups/
```

### Error: "Base de datos bloqueada"

- Asegurar que no hay procesos usando la base de datos
- En producción, detener la aplicación brevemente durante el backup

### Backup muy grande

```bash
# Comprimir backups antiguos
gzip backups/backup_*.json
gzip backups/backup_db_*.sqlite3

# O usar solo formato JSON (más pequeño)
python manage.py backup_database --format json
```

---

## 📚 Referencias

- [Documentación Django dumpdata](https://docs.djangoproject.com/en/stable/ref/django-admin/#dumpdata)
- [Documentación Django loaddata](https://docs.djangoproject.com/en/stable/ref/django-admin/#loaddata)
- [Cron Tutorial](https://crontab.guru/)
- [Windows Task Scheduler](https://docs.microsoft.com/en-us/windows/desktop/taskschd/task-scheduler-start-page)

---

**Última actualización:** Diciembre 2024  
**Compatible con:** Django 5.0+, Python 3.10+

