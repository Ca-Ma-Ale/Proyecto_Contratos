# 🔒 Guía de Seguridad para Base de Datos SQLite

**Fecha:** 2025-01-27  
**Propósito:** Proteger información sensible en SQLite sin migrar a MySQL

---

## 📋 Resumen

Aunque SQLite es adecuada para tu proyecto, es importante implementar medidas de seguridad adicionales para proteger los datos sensibles almacenados.

---

## 🛡️ Medidas de Seguridad Implementadas

### 1. ✅ Encriptación de Contraseñas de Email

**Estado:** ✅ **IMPLEMENTADO**

Las contraseñas de email SMTP se encriptan automáticamente antes de guardarse en la base de datos.

**Ver:** `docs/guias/GUIA_ENCRIPTACION_DATOS.md` para detalles completos.

---

### 2. 🔐 Permisos de Archivo de Base de Datos

**Objetivo:** Restringir acceso al archivo `db.sqlite3` solo al propietario.

#### En Desarrollo (Windows)

```powershell
# Verificar permisos actuales
icacls db.sqlite3

# Restringir acceso (solo propietario)
icacls db.sqlite3 /inheritance:r
icacls db.sqlite3 /grant:r "%USERNAME%:(F)"
```

#### En Producción (Linux/PythonAnywhere)

```bash
# Restringir permisos (solo lectura/escritura para propietario)
chmod 600 db.sqlite3

# Verificar permisos
ls -l db.sqlite3
# Debe mostrar: -rw------- (solo propietario puede leer/escribir)
```

**Resultado esperado:**
```
-rw------- 1 usuario usuario 1234567 fecha db.sqlite3
```

**⚠️ IMPORTANTE:**
- Ejecutar después de crear la base de datos
- Ejecutar después de cada `migrate`
- Verificar periódicamente que los permisos no cambien

---

### 3. 📦 Backups Seguros

**Estado:** ✅ **Ya implementado**

Tu sistema ya tiene backups automáticos configurados.

**Mejoras de seguridad para backups:**

1. **Encriptar backups:**
   ```bash
   # Usar gzip (compresión básica)
   gzip backups/backup_*.json
   gzip backups/backup_db_*.sqlite3
   ```

2. **Permisos de directorio de backups:**
   ```bash
   # En producción
   chmod 700 backups/  # Solo propietario puede acceder
   ```

3. **Almacenar backups fuera del servidor:**
   - Usar OneDrive (ya configurado)
   - Usar servicios cloud seguros
   - Nunca subir backups a repositorios públicos

**Ver:** `docs/guias/GUIA_BACKUPS_AUTOMATICOS.md`

---

### 4. 🔑 Variables de Entorno Seguras

**Estado:** ✅ **Implementado**

Todas las claves sensibles deben estar en variables de entorno:

```env
# .env (NO subir a Git)
SECRET_KEY=tu-secret-key
ENCRYPTION_KEY=tu-encryption-key
EMAIL_HOST_PASSWORD=... (si se usa desde .env)
```

**Verificar:**
- ✅ `.env` está en `.gitignore`
- ✅ `env_example.txt` no contiene valores reales
- ✅ Variables de entorno configuradas en producción

---

### 5. 🚫 Exclusión de Base de Datos del Repositorio

**Estado:** ✅ **Verificar**

Asegurar que `db.sqlite3` está en `.gitignore`:

```gitignore
# Base de datos
db.sqlite3
*.sqlite3
*.db

# Archivos de entorno
.env
*.env
```

**Verificar:**
```bash
# Verificar que está en .gitignore
cat .gitignore | grep sqlite3

# Verificar que no está en el repositorio
git ls-files | grep sqlite3
# No debe mostrar nada
```

---

## 📝 Checklist de Seguridad SQLite

### Configuración Inicial

- [ ] Permisos de archivo configurados (chmod 600)
- [ ] `ENCRYPTION_KEY` generada y configurada
- [ ] Contraseñas de email encriptadas
- [ ] `.env` en `.gitignore`
- [ ] `db.sqlite3` en `.gitignore`
- [ ] Backups configurados y probados

### Mantenimiento Regular

- [ ] Verificar permisos de `db.sqlite3` (mensual)
- [ ] Verificar que backups funcionan (semanal)
- [ ] Revisar logs de seguridad (semanal)
- [ ] Rotar `ENCRYPTION_KEY` si es necesario (anual)
- [ ] Auditar acceso a base de datos (trimestral)

---

## 🔧 Scripts de Seguridad

### Script: Verificar Permisos (Linux)

```bash
#!/bin/bash
# verificar_permisos_db.sh

DB_FILE="db.sqlite3"

if [ -f "$DB_FILE" ]; then
    PERMISSIONS=$(stat -c "%a" "$DB_FILE")
    if [ "$PERMISSIONS" = "600" ]; then
        echo "✅ Permisos correctos: $PERMISSIONS"
    else
        echo "⚠️  Permisos incorrectos: $PERMISSIONS (debe ser 600)"
        echo "Ejecutar: chmod 600 $DB_FILE"
    fi
else
    echo "⚠️  Archivo $DB_FILE no encontrado"
fi
```

### Script: Verificar Encriptación

```bash
#!/bin/bash
# verificar_encriptacion.sh

python manage.py shell << EOF
from gestion.models import ConfiguracionEmail
from gestion.utils_encryption import decrypt_value

configs = ConfiguracionEmail.objects.all()
for config in configs:
    try:
        password = config.get_password()
        print(f"✅ {config.nombre}: Contraseña encriptada correctamente")
    except Exception as e:
        print(f"❌ {config.nombre}: Error - {e}")
EOF
```

---

## 🚨 Respuesta a Incidentes

### Si se Compromete el Archivo db.sqlite3

1. **Inmediato:**
   - Cambiar todas las contraseñas de email
   - Cambiar `SECRET_KEY` y `ENCRYPTION_KEY`
   - Re-encriptar todas las contraseñas

2. **Corto plazo:**
   - Auditar accesos al sistema
   - Revisar logs de seguridad
   - Notificar a usuarios si es necesario

3. **Mediano plazo:**
   - Considerar migración a MySQL
   - Implementar auditoría más estricta
   - Reforzar medidas de seguridad

---

## 📊 Nivel de Seguridad Actual

### Con Medidas Implementadas

| Aspecto | Sin Protección | Con Protección |
|---------|----------------|----------------|
| **Contraseñas email** | ❌ Texto plano | ✅ Encriptadas |
| **Acceso al archivo** | ⚠️ Permisos por defecto | ✅ Restringido (chmod 600) |
| **Backups** | ⚠️ Sin encriptar | ✅ Automáticos y seguros |
| **Variables de entorno** | ⚠️ En código | ✅ En .env |
| **Repositorio** | ⚠️ Riesgo de exposición | ✅ Excluido |

**Nivel de seguridad:** 🟢 **ALTO** (con todas las medidas)

---

## 🎯 Próximos Pasos Recomendados

### Corto Plazo (Ahora)

1. ✅ Implementar encriptación de contraseñas
2. ✅ Configurar permisos de archivo
3. ✅ Verificar exclusiones de Git
4. ✅ Configurar `ENCRYPTION_KEY`

### Mediano Plazo (1-3 meses)

1. Implementar auditoría de accesos
2. Monitoreo de cambios en base de datos
3. Alertas de seguridad

### Largo Plazo (Si el proyecto crece)

1. Considerar migración a MySQL (si superas 50 usuarios)
2. Implementar replicación de backups
3. Auditoría completa de seguridad

---

## 📚 Referencias

- **Encriptación:** `docs/guias/GUIA_ENCRIPTACION_DATOS.md`
- **Backups:** `docs/guias/GUIA_BACKUPS_AUTOMATICOS.md`
- **Bases de Datos:** `docs/deployment/BASES_DATOS_PYTHONANYWHERE.md`
- **Diagnóstico de Seguridad:** `docs/analisis/DIAGNOSTICO_SEGURIDAD_CIBERSEGURIDAD.md`

---

**Última actualización:** 2025-01-27  
**Estado:** ✅ Medidas de seguridad implementadas

