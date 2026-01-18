# 🗄️ Bases de Datos en PythonAnywhere - Guía Completa

**Fecha:** 2025-01-27  
**Actualización:** Análisis de opciones para plan gratuito

---

## 📊 Resumen Ejecutivo

### ✅ **BUENA NOTICIA: No necesitas migrar la base de datos ahora**

Para tu proyecto con **máximo 15 usuarios y 10 simultáneos**, **SQLite es perfectamente adecuada** y está disponible **completamente gratis** en PythonAnywhere.

---

## 🎯 Situación Actual del Proyecto

### Características del Proyecto
- **Tipo:** Sistema de gestión de contratos interno
- **Usuarios esperados:** 15 máximo, 10 simultáneos
- **Volumen de datos:** Bajo-medio (contratos, pólizas, reportes)
- **Base de datos actual:** SQLite
- **Uso:** Organización pequeña-mediana

### Conclusión
✅ **SQLite es la opción correcta** para este proyecto en este momento.

---

## 📋 Opciones de Base de Datos en PythonAnywhere

### 1. **SQLite** ✅ **INCLUIDO GRATIS - RECOMENDADO PARA TI**

#### Disponibilidad
- ✅ **Plan Gratuito:** Incluido sin restricciones
- ✅ **Todos los planes:** Disponible siempre
- ✅ **Sin límite de tamaño** para proyectos pequeños-medianos
- ✅ **Sin configuración adicional** requerida

#### Características
- **Archivo único:** `db.sqlite3` en el directorio del proyecto
- **Backup simple:** Copiar el archivo es suficiente
- **Rendimiento:** Excelente para < 100 usuarios concurrentes
- **Configuración:** Ya está configurado en tu proyecto

#### Límites Prácticos
- ✅ **Tu proyecto:** 10 usuarios simultáneos → **Perfecto**
- ⚠️ **Límite recomendado:** ~50 usuarios simultáneos
- ⚠️ **Límite máximo:** ~100 usuarios simultáneos (con optimizaciones)

#### Configuración Actual (Ya Implementada)
```python
# contratos/settings_production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

**✅ Esto funciona perfectamente en PythonAnywhere gratis**

---

### 2. **MySQL** ❌ **NO DISPONIBLE EN PLAN GRATUITO**

#### Disponibilidad
- ❌ **Plan Gratuito:** NO disponible
- ✅ **Plan Hacker ($5/mes):** 1 base de datos MySQL
- ✅ **Plan Web Developer ($12/mes):** 1 base de datos MySQL
- ✅ **Plan de pago superior:** Múltiples bases de datos

#### Características
- **Base de datos separada:** Servidor MySQL dedicado
- **Rendimiento:** Mejor para > 50 usuarios concurrentes
- **Backup:** Requiere herramientas específicas (mysqldump)
- **Configuración:** Requiere cambios en `settings.py`

#### ¿Cuándo necesitarías MySQL?
- ⚠️ Si superas **50 usuarios simultáneos**
- ⚠️ Si el archivo SQLite supera **100 MB**
- ⚠️ Si tienes problemas de bloqueo de base de datos
- ⚠️ Si necesitas replicación o alta disponibilidad

**Para tu proyecto actual:** ❌ No es necesario

---

### 3. **PostgreSQL** ❌ **NO DISPONIBLE EN PYTHONANYWHERE**

PythonAnywhere **NO ofrece PostgreSQL** en ningún plan.

Si necesitas PostgreSQL, considera:
- Railway (incluye PostgreSQL gratis)
- Render (incluye PostgreSQL en plan gratuito)
- VPS (configuración manual)

---

## ✅ Recomendación: Mantener SQLite

### Por qué SQLite es perfecto para tu proyecto

1. **✅ Gratis en PythonAnywhere**
   - Sin costo adicional
   - Sin límites para tu tamaño de proyecto

2. **✅ Rendimiento adecuado**
   - Tu proyecto: 10 usuarios simultáneos
   - SQLite maneja hasta 50-100 sin problemas
   - Rendimiento excelente para este volumen

3. **✅ Simplicidad**
   - Sin configuración adicional
   - Backups simples (copiar archivo)
   - Sin administración de servidor

4. **✅ Ya está configurado**
   - Tu código ya funciona con SQLite
   - No necesitas cambios
   - Sin riesgo de migración

5. **✅ Seguridad suficiente** (con medidas adicionales)
   - Permisos de archivo (chmod 600)
   - Encriptación de campos sensibles (implementar)
   - Backups regulares

---

## 🔄 Cuándo considerar migración a MySQL

### Señales de que necesitas MySQL

1. **Rendimiento**
   - ⚠️ El sitio se vuelve lento con usuarios simultáneos
   - ⚠️ Errores "Database is locked" frecuentes
   - ⚠️ Consultas que toman > 1 segundo

2. **Tamaño**
   - ⚠️ Archivo SQLite > 100 MB
   - ⚠️ Crecimiento rápido de datos

3. **Usuarios**
   - ⚠️ Más de 50 usuarios simultáneos
   - ⚠️ Crecimiento planificado a 100+ usuarios

4. **Funcionalidades avanzadas**
   - ⚠️ Necesitas replicación
   - ⚠️ Necesitas alta disponibilidad
   - ⚠️ Necesitas particionamiento

**Para tu proyecto:** Ninguna de estas señales se aplica actualmente.

---

## 🛠️ Cómo Migrar de SQLite a MySQL (Cuando sea Necesario)

### Paso 1: Obtener Acceso a MySQL

1. **Actualizar plan en PythonAnywhere:**
   - Ir a "Account" → "Upgrade"
   - Seleccionar plan Hacker ($5/mes) o superior
   - Esperar activación (inmediato)

2. **Crear base de datos MySQL:**
   - Ir a "Databases" en el dashboard
   - Hacer clic en "Create a new MySQL database"
   - Anotar credenciales (usuario, contraseña, host)

---

### Paso 2: Configurar Django para MySQL

#### Instalar driver MySQL
```bash
# En PythonAnywhere bash console
workon contratos_env
pip install mysqlclient
```

#### Actualizar settings_production.py
```python
# contratos/settings_production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'tu_usuario$nombre_db',  # Formato en PythonAnywhere
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_password_mysql',
        'HOST': 'tu_usuario.mysql.pythonanywhere-services.com',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}
```

#### Variables de entorno (Recomendado)
```bash
# En .env
DATABASE_NAME=tu_usuario$nombre_db
DATABASE_USER=tu_usuario
DATABASE_PASSWORD=tu_password_mysql
DATABASE_HOST=tu_usuario.mysql.pythonanywhere-services.com
DATABASE_PORT=3306
```

```python
# settings_production.py con variables de entorno
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DATABASE_NAME'),
        'USER': os.environ.get('DATABASE_USER'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD'),
        'HOST': os.environ.get('DATABASE_HOST'),
        'PORT': os.environ.get('DATABASE_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
    }
}
```

---

### Paso 3: Migrar Datos

#### Método 1: Usando dumpdata/loaddata (Recomendado)

```bash
# 1. Exportar datos desde SQLite
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > backup.json

# 2. Cambiar configuración a MySQL (paso anterior)
# 3. Crear tablas en MySQL
python manage.py migrate

# 4. Cargar datos
python manage.py loaddata backup.json

# 5. Crear superusuario (si es necesario)
python manage.py createsuperuser
```

#### Método 2: Usando herramienta de migración

```bash
# Instalar django-extensions (opcional, facilita migración)
pip install django-extensions

# Exportar y migrar
python manage.py dumpdata --natural-primary --natural-foreign > backup.json
# (cambiar configuración)
python manage.py migrate
python manage.py loaddata backup.json
```

---

## 🔒 Mejoras de Seguridad para SQLite (Implementar Ahora)

Aunque SQLite es adecuada, puedes mejorar la seguridad:

### 1. **Permisos de Archivo**

```bash
# En PythonAnywhere bash console
chmod 600 /home/tu_usuario/tu_proyecto/db.sqlite3
```

Esto restringe el acceso al archivo solo al propietario.

### 2. **Encriptación de Campos Sensibles**

Implementar encriptación para campos críticos (ver diagnóstico de seguridad).

### 3. **Backups Regulares**

Tu proyecto ya tiene sistema de backups implementado:

```bash
python manage.py backup_database
```

**Configurar backup automático diario** (ver `docs/guias/GUIA_BACKUPS_AUTOMATICOS.md`).

---

## 📊 Comparativa: SQLite vs MySQL en PythonAnywhere

| Característica | SQLite (Gratis) | MySQL ($5/mes) |
|----------------|-----------------|----------------|
| **Costo** | ✅ Gratis | ❌ $5/mes mínimo |
| **Usuarios simultáneos** | ✅ 50-100 | ✅ 1000+ |
| **Tamaño de datos** | ✅ Hasta 100 MB | ✅ Ilimitado |
| **Configuración** | ✅ Cero | ⚠️ Requiere setup |
| **Backup** | ✅ Copiar archivo | ⚠️ mysqldump |
| **Rendimiento (tu caso)** | ✅ Excelente | ✅ Excelente |
| **Necesario para ti** | ✅ **SÍ** | ❌ No (aún) |

---

## 🎯 Plan de Acción Recomendado

### Fase 1: Ahora (Gratis) ✅

1. **Desplegar con SQLite**
   - ✅ Ya está configurado
   - ✅ Funciona en plan gratuito
   - ✅ Sin cambios necesarios

2. **Implementar seguridad**
   - ✅ Permisos de archivo (chmod 600)
   - ✅ Backups automáticos
   - ✅ Encriptación de campos sensibles

3. **Monitorear rendimiento**
   - Medir tiempo de respuesta
   - Verificar errores de base de datos
   - Revisar tamaño del archivo

**Costo:** $0/mes

---

### Fase 2: Si el Proyecto Crece (Futuro)

#### Señales para migrar:
- ✅ Más de 50 usuarios simultáneos
- ✅ Archivo SQLite > 100 MB
- ✅ Problemas de rendimiento

#### Proceso:
1. Actualizar a plan Hacker ($5/mes)
2. Crear base de datos MySQL
3. Migrar datos (proceso documentado arriba)
4. Actualizar configuración

**Costo:** $5/mes adicional

---

### Fase 3: Escalamiento (Muy Futuro)

Si el proyecto crece mucho:
- Considerar VPS dedicado
- Considerar bases de datos cloud (AWS RDS, etc.)
- Implementar alta disponibilidad

**Costo:** Variable ($10-50+/mes)

---

## ❓ Preguntas Frecuentes

### ¿SQLite es seguro para producción?

**Sí, con medidas de seguridad:**
- ✅ Permisos de archivo restringidos
- ✅ Encriptación de campos sensibles
- ✅ Backups regulares
- ✅ HTTPS (ya configurado)

**SQLite es usado en producción por:**
- Aplicaciones móviles (WhatsApp, Firefox, etc.)
- Sistemas embebidos
- Proyectos pequeños-medianos

---

### ¿Puedo usar SQLite en PythonAnywhere gratis?

**✅ SÍ, completamente gratis**
- Sin límites para proyectos pequeños-medianos
- Sin configuración adicional
- Sin restricciones en el plan gratuito

---

### ¿Cuándo debo migrar a MySQL?

**Solo si:**
- Tienes más de 50 usuarios simultáneos
- El archivo SQLite supera 100 MB
- Experimentas problemas de rendimiento
- Necesitas funcionalidades avanzadas

**Para tu proyecto actual:** No es necesario.

---

### ¿Qué pasa si supero los límites de SQLite?

**Opciones:**
1. **Optimizar SQLite** (índices, consultas, etc.)
2. **Migrar a MySQL** (proceso documentado arriba)
3. **Escalar a VPS** (si el proyecto crece mucho)

---

### ¿Puedo probar MySQL antes de pagar?

**No directamente, pero puedes:**
- Probar localmente con MySQL
- Evaluar si necesitas las características adicionales
- Migrar cuando realmente lo necesites

---

## ✅ Conclusión

### Para tu Proyecto

1. **✅ SQLite es la opción correcta ahora**
   - Gratis en PythonAnywhere
   - Rendimiento excelente para tu tamaño
   - Ya está configurado

2. **✅ No necesitas migrar ahora**
   - Tu proyecto está dentro de los límites de SQLite
   - No justifica el costo adicional ($5/mes)
   - Sin problemas de rendimiento esperados

3. **✅ Plan de migración disponible**
   - Documentación completa arriba
   - Proceso simple cuando sea necesario
   - Sin presión de tiempo

4. **✅ Mejoras de seguridad recomendadas**
   - Permisos de archivo
   - Encriptación de campos sensibles
   - Backups automáticos

---

## 📝 Checklist Pre-Despliegue

### Base de Datos SQLite

- [x] Configuración en `settings_production.py` verificada
- [ ] Permisos de archivo configurados (chmod 600)
- [ ] Sistema de backups configurado
- [ ] Encriptación de campos sensibles implementada
- [ ] Pruebas de rendimiento realizadas

### Plan de Migración (Para Futuro)

- [ ] Documentación de migración revisada
- [ ] Proceso de backup verificado
- [ ] Conocimiento de cuando migrar documentado

---

## 🔗 Referencias

- [Documentación SQLite](https://www.sqlite.org/)
- [PythonAnywhere Databases](https://help.pythonanywhere.com/pages/UsingMySQL/)
- [Django Database Settings](https://docs.djangoproject.com/en/5.0/ref/settings/#databases)
- [Guía de Backups](docs/guias/GUIA_BACKUPS_AUTOMATICOS.md)

---

**Última actualización:** 2025-01-27  
**Estado:** ✅ SQLite recomendado y listo para producción  
**Próxima revisión:** Cuando el proyecto supere 50 usuarios simultáneos

