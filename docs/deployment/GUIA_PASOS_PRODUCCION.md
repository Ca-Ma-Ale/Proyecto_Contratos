# Guía Detallada: Próximos Pasos para Producción

## 📋 Resumen Ejecutivo

Tu proyecto Django está **listo para producción**. Solo necesitas configurar las variables de entorno en el servidor y ejecutar algunos comandos finales.

---

## 🔐 Paso 1: Configurar Variables de Entorno

Las variables de entorno son configuración sensible que **NO debe estar en el código**. Se configuran directamente en el servidor.

### 1.1 Generar SECRET_KEY

La `SECRET_KEY` es una cadena aleatoria segura que Django usa para:
- Firmar cookies y sesiones
- Generar tokens CSRF
- Encriptar datos sensibles

**Generar una SECRET_KEY segura:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Ejemplo de salida:**
```
django-insecure-abc123xyz789... (50+ caracteres)
```

⚠️ **IMPORTANTE:** Guarda esta clave en un lugar seguro. Si la pierdes, los usuarios tendrán que iniciar sesión nuevamente.

### 1.2 Configurar Variables en PythonAnywhere

**PythonAnywhere es la plataforma recomendada para este proyecto.**

#### Método Recomendado: Panel Web

1. Ve al Dashboard de PythonAnywhere → **Web**
2. Desplázate hasta la sección **"Environment variables"**
3. Haz clic en **"Add a new environment variable"**
4. Agrega cada variable una por una:

```
Variable: SECRET_KEY
Value: django-insecure-tu-clave-generada-aqui-50-caracteres-minimo
```

```
Variable: DEBUG
Value: False
```

```
Variable: ALLOWED_HOSTS
Value: tu-usuario.pythonanywhere.com
```
*(Reemplaza "tu-usuario" con tu nombre de usuario de PythonAnywhere)*

```
Variable: CSRF_TRUSTED_ORIGINS
Value: https://tu-usuario.pythonanywhere.com
```
*(Con https:// y tu nombre de usuario)*

5. Haz clic en el botón verde **"Reload"** después de agregar todas las variables

#### Método Alternativo: Archivo .env

Si prefieres usar un archivo `.env`:

1. En una consola Bash de PythonAnywhere:
```bash
cd ~/tu-proyecto
nano .env
```

2. Agrega:
```bash
SECRET_KEY=django-insecure-tu-clave-generada-aqui-50-caracteres-minimo
DEBUG=False
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
```

3. Guarda con `Ctrl+O`, `Enter`, `Ctrl+X`

4. Modifica el archivo WSGI para cargar el .env (ver Paso 7)

### 1.3 Explicación de Cada Variable

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SECRET_KEY` | Clave secreta de Django (obligatoria) | `django-insecure-abc123...` |
| `DEBUG` | Modo depuración (debe ser `False`) | `False` |
| `ALLOWED_HOSTS` | Dominios permitidos (sin `http://`) | `miempresa.com,www.miempresa.com` |
| `CSRF_TRUSTED_ORIGINS` | Orígenes confiables para CSRF (con `https://`) | `https://miempresa.com,https://www.miempresa.com` |

---

## 🗄️ Paso 2: Configurar Base de Datos

### 2.1 Ejecutar Migraciones

Las migraciones crean/actualizan las tablas en la base de datos:

```bash
python manage.py migrate --settings=contratos.settings_production
```

**Qué hace este comando:**
- Crea todas las tablas necesarias (Contratos, Polizas, IPC, etc.)
- Aplica cambios de estructura de base de datos
- Crea índices y relaciones

**Salida esperada:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, gestion, sessions
Running migrations:
  Applying gestion.0001_initial... OK
  Applying gestion.0002_... OK
  ...
```

### 2.2 Verificar Base de Datos

Verifica que las tablas se crearon correctamente:

```bash
python manage.py showmigrations --settings=contratos.settings_production
```

Todas las migraciones deben mostrar `[X]` (aplicadas).

---

## 📦 Paso 3: Recolectar Archivos Estáticos

Los archivos estáticos (CSS, JavaScript, imágenes) deben estar en un directorio centralizado para que el servidor web los sirva eficientemente.

### 3.1 Ejecutar collectstatic

```bash
python manage.py collectstatic --noinput --settings=contratos.settings_production
```

**Qué hace este comando:**
- Copia todos los archivos estáticos a `staticfiles/`
- Incluye archivos de Django admin y tus archivos personalizados
- El flag `--noinput` evita preguntas interactivas (útil para scripts)

**Salida esperada:**
```
Copying '/path/to/static/css/style.css'
Copying '/path/to/static/js/app.js'
...
X static files copied to '/path/to/staticfiles'
```

### 3.2 Configurar Archivos Estáticos en PythonAnywhere

En PythonAnywhere:

1. Ve a **Web** → Tu aplicación web
2. Desplázate hasta **"Static files"**
3. Agrega la siguiente entrada:
   - **URL:** `/static/`
   - **Directory:** `/home/tu-usuario/tu-proyecto/staticfiles`
4. Haz clic en el check ✓ para guardar
5. Haz clic en **"Reload"** para aplicar los cambios

---

## 👤 Paso 4: Crear Usuario Administrador

Necesitas un usuario con permisos de administrador para acceder al panel de Django.

### 4.1 Crear Superusuario

```bash
python manage.py createsuperuser --settings=contratos.settings_production
```

**El comando te pedirá:**
- Username (nombre de usuario)
- Email (opcional pero recomendado)
- Password (contraseña segura)
- Password confirmation (confirmar contraseña)

**Ejemplo de ejecución:**
```
Username: admin
Email address: admin@miempresa.com
Password: ********
Password (again): ********
Superuser created successfully.
```

### 4.2 Acceder al Admin

Una vez creado, puedes acceder a:
- **Panel Admin:** `https://tu-usuario.pythonanywhere.com/admin/`
- **Login:** Usa las credenciales que acabas de crear

---

## 🔒 Paso 5: Configurar Permisos de Archivos

El servidor necesita permisos de escritura en ciertos directorios.

### 5.1 Crear Directorios en PythonAnywhere

En una consola Bash de PythonAnywhere:

```bash
cd ~/tu-proyecto
mkdir -p logs
mkdir -p media
```

**Nota:** En PythonAnywhere, los permisos generalmente están configurados correctamente por defecto. Si tienes problemas de escritura, contacta al soporte de PythonAnywhere.

---

## ✅ Paso 6: Verificaciones Finales

### 6.1 Ejecutar Test Pre-Deploy

```bash
python scripts/test_pre_deploy.py
```

**Debe mostrar:**
```
[OK] EL PROYECTO ESTÁ LISTO PARA DESPLIEGUE
```

### 6.2 Verificar Configuración Django

```bash
python manage.py check --settings=contratos.settings_production --deploy
```

**Debe mostrar:**
```
System check identified no issues (0 silenced).
```

### 6.3 Probar la Aplicación

1. Accede a `https://tu-usuario.pythonanywhere.com/`
2. Verifica que la página carga correctamente
3. Intenta iniciar sesión con el usuario admin creado
4. Verifica que no hay errores en la consola del navegador

---

## 🚀 Paso 7: Configurar WSGI en PythonAnywhere

### 7.1 Editar Archivo WSGI

1. Ve a **Web** → Tu aplicación web
2. Haz clic en el enlace **"WSGI configuration file"**
3. Reemplaza todo el contenido con:

```python
import os
import sys

# Agregar el directorio del proyecto al path
path = '/home/tu-usuario/tu-proyecto'
if path not in sys.path:
    sys.path.append(path)

# Configurar Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'contratos.settings_production'

# Si usas archivo .env, carga las variables aquí:
from pathlib import Path
env_file = Path('/home/tu-usuario/tu-proyecto/.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ.setdefault(key, value)

# Importar la aplicación WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

4. **Reemplaza `tu-usuario` y `tu-proyecto`** con tus valores reales
5. Haz clic en **"Save"**

### 7.2 Configurar Archivos Estáticos y Media

En la misma página de configuración:

1. **Static files:**
   - URL: `/static/`
   - Directory: `/home/tu-usuario/tu-proyecto/staticfiles`

2. **Media files (si aplica):**
   - URL: `/media/`
   - Directory: `/home/tu-usuario/tu-proyecto/media`

3. Haz clic en los checks ✓ para guardar cada entrada

### 7.3 Reiniciar Aplicación

Haz clic en el botón verde **"Reload tu-usuario.pythonanywhere.com"** en la parte superior de la página.

---

## 📧 Paso 8: Configurar Email (Opcional)

Si necesitas que la aplicación envíe emails (alertas, notificaciones):

### 8.1 Variables de Entorno para Email

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-password-de-aplicacion-gmail
DEFAULT_FROM_EMAIL=noreply@tu-dominio.com
```

### 8.2 Gmail - Contraseña de Aplicación

Si usas Gmail, necesitas crear una "Contraseña de aplicación":
1. Ve a tu cuenta de Google → Seguridad
2. Activa la verificación en 2 pasos
3. Genera una "Contraseña de aplicación"
4. Usa esa contraseña en `EMAIL_HOST_PASSWORD`

---

## 🔄 Paso 9: Configurar Backups (Recomendado)

### 9.1 Backup Automático de Base de Datos

El proyecto incluye scripts de backup. Configúralos:

```bash
# Ejecutar backup manualmente
python manage.py backup_database --settings=contratos.settings_production

# O configurar tarea programada (cron)
# Ejecutar diariamente a las 2 AM
0 2 * * * cd /ruta/proyecto && python manage.py backup_database --settings=contratos.settings_production
```

---

## 📝 Checklist Final Pre-Despliegue

Antes de poner en producción, verifica:

- [ ] `SECRET_KEY` configurada y segura (50+ caracteres)
- [ ] `DEBUG=False` en producción
- [ ] `ALLOWED_HOSTS` incluye tu dominio
- [ ] `CSRF_TRUSTED_ORIGINS` incluye tu URL con `https://`
- [ ] Migraciones ejecutadas sin errores
- [ ] `collectstatic` ejecutado exitosamente
- [ ] Usuario admin creado
- [ ] Permisos de archivos configurados
- [ ] Test pre-deploy pasa sin errores
- [ ] `python manage.py check --deploy` sin errores
- [ ] Aplicación accesible desde el navegador
- [ ] Login funciona correctamente
- [ ] Logs funcionando (`logs/django_errors.log`)

---

## 🆘 Solución de Problemas Comunes

### Error: "SECRET_KEY no está configurada"
**Solución:** Configura la variable de entorno `SECRET_KEY` en el servidor.

### Error: "DisallowedHost"
**Solución:** Agrega tu dominio a `ALLOWED_HOSTS`.

### Error: "CSRF verification failed"
**Solución:** Agrega tu URL a `CSRF_TRUSTED_ORIGINS` con `https://`.

### Archivos estáticos no se cargan
**Solución:** 
1. Ejecuta `collectstatic` nuevamente
2. Verifica la configuración de archivos estáticos en el servidor web

### Error 500 en producción
**Solución:**
1. Revisa `logs/django_errors.log`
2. Verifica que `DEBUG=False` (no mostrará detalles del error)
3. Temporalmente pon `DEBUG=True` para ver el error completo (solo para debugging)

---

## 📚 Recursos Adicionales

- **Documentación Django Deployment:** https://docs.djangoproject.com/en/5.0/howto/deployment/
- **PythonAnywhere Docs:** https://help.pythonanywhere.com/pages/
- **Guía de Seguridad Django:** https://docs.djangoproject.com/en/5.0/topics/security/

---

## ✅ Estado Actual

Tu proyecto está **100% listo** para producción. Solo necesitas:

1. ✅ Configurar variables de entorno en el servidor
2. ✅ Ejecutar migraciones
3. ✅ Ejecutar collectstatic
4. ✅ Crear usuario admin
5. ✅ Configurar permisos

**¡Todo el código está preparado y probado!** 🎉
