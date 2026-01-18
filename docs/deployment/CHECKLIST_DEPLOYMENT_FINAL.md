# Checklist Final de Deployment - PythonAnywhere

**Fecha de verificación:** 2025-01-27  
**Estado:** ✅ Listo para despliegue

---

## ✅ Verificaciones Completadas

### 1. Archivos Requeridos
- ✅ `manage.py` - Presente
- ✅ `requirements.txt` - Presente y actualizado
- ✅ `contratos/settings.py` - Configurado para desarrollo
- ✅ `contratos/settings_production.py` - Configurado para producción
- ✅ `contratos/wsgi.py` - Configurado correctamente
- ✅ `contratos/urls.py` - Configurado
- ✅ `env_example.txt` - Plantilla completa
- ✅ `.gitignore` - Configurado correctamente

### 2. Directorios
- ✅ `logs/` - Creado
- ✅ `static/` - Presente
- ✅ `templates/` - Presente
- ✅ `gestion/` - Presente

### 3. Configuración de Producción (`settings_production.py`)
- ✅ `django.contrib.humanize` agregado a INSTALLED_APPS
- ✅ Configuración de email agregada
- ✅ Configuración de seguridad HTTPS habilitada
- ✅ Logging configurado
- ✅ Variables de entorno configuradas

### 4. Dependencias (`requirements.txt`)
- ✅ Django>=5.0.0,<5.1.0
- ✅ gunicorn>=21.2.0
- ✅ python-decouple>=3.8
- ✅ django-axes>=6.0.0
- ✅ cryptography>=41.0.0
- ✅ Todas las dependencias necesarias presentes

### 5. Seguridad
- ✅ `.gitignore` excluye archivos sensibles (.env, db.sqlite3, etc.)
- ✅ `settings_production.py` requiere SECRET_KEY de variable de entorno
- ✅ Configuración de seguridad HTTPS lista
- ✅ Protección CSRF configurada
- ✅ Protección contra fuerza bruta (django-axes) configurada

### 6. Scripts de Verificación
- ✅ `scripts/verificar_deployment.py` - Creado y funcionando

---

## 📋 Pasos para Desplegar en PythonAnywhere

### Paso 1: Preparar el Código Localmente

```bash
# 1. Asegúrate de estar en la rama correcta
git status

# 2. Ejecutar script de verificación
python scripts/verificar_deployment.py

# 3. Recolectar archivos estáticos (si no lo has hecho)
python manage.py collectstatic --noinput

# 4. Verificar que no haya migraciones pendientes
python manage.py makemigrations
python manage.py migrate

# 5. Hacer commit y push de los cambios
git add .
git commit -m "Preparación para deployment en PythonAnywhere"
git push
```

### Paso 2: Configurar PythonAnywhere

#### 2.1 Crear cuenta y abrir Bash Console
1. Ve a [pythonanywhere.com](https://www.pythonanywhere.com/)
2. Crea una cuenta gratuita o inicia sesión
3. Ve a "Consoles" → "Bash"

#### 2.2 Clonar el Repositorio
```bash
# Clonar tu repositorio (reemplaza con tu URL)
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
```

#### 2.3 Crear Entorno Virtual
```bash
# Crear entorno virtual con Python 3.10
mkvirtualenv --python=/usr/bin/python3.10 contratos_env

# El entorno se activa automáticamente
# Si necesitas activarlo después:
workon contratos_env

# Instalar dependencias
pip install -r requirements.txt
```

#### 2.4 Configurar Variables de Entorno
```bash
# Crear archivo .env
nano .env
```

Contenido del archivo `.env`:
```env
SECRET_KEY=genera-una-clave-secreta-super-segura-aqui
DEBUG=False
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
```

Para generar SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### 2.5 Configurar Base de Datos
```bash
# Asegúrate de estar en el directorio del proyecto
cd ~/tu-repositorio

# Activar entorno virtual
workon contratos_env

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar archivos estáticos
python manage.py collectstatic --noinput
```

#### 2.6 Crear Directorio de Logs
```bash
mkdir -p logs
touch logs/django_errors.log
chmod 755 logs
```

### Paso 3: Configurar Web App en PythonAnywhere

#### 3.1 Crear Web App
1. En el Dashboard, ve a "Web"
2. Haz clic en "Add a new web app"
3. Selecciona "Manual configuration" (NO selecciones Django)
4. Selecciona Python 3.10
5. Haz clic en "Next"

#### 3.2 Configurar Virtualenv
1. En la página de configuración de tu web app
2. En la sección "Virtualenv":
   - Ingresa: `/home/tu-usuario/.virtualenvs/contratos_env`
3. Haz clic en el check mark

#### 3.3 Configurar WSGI File
1. En la sección "Code", haz clic en el link de "WSGI configuration file"
2. Borra todo el contenido
3. Pega el siguiente código (ajusta `tu-usuario` y la ruta):

```python
import os
import sys

# Agregar el directorio del proyecto al path
path = '/home/tu-usuario/tu-repositorio'
if path not in sys.path:
    sys.path.append(path)

# Configurar Django para producción
os.environ['DJANGO_SETTINGS_MODULE'] = 'contratos.settings_production'

# Cargar variables de entorno desde .env
from pathlib import Path
env_file = Path('/home/tu-usuario/tu-repositorio/.env')
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

4. Guarda el archivo con el botón "Save"

#### 3.4 Configurar Static Files
1. En la página de configuración de tu web app
2. En la sección "Static files", agrega:
   - URL: `/static/`
   - Directory: `/home/tu-usuario/tu-repositorio/staticfiles`
3. Agrega otra entrada:
   - URL: `/media/`
   - Directory: `/home/tu-usuario/tu-repositorio/media`

### Paso 4: Recargar y Probar

1. En la página "Web" de PythonAnywhere
2. Haz clic en el botón verde "Reload tu-usuario.pythonanywhere.com"
3. Visita tu sitio: `https://tu-usuario.pythonanywhere.com`
4. Prueba el login con las credenciales del superusuario

---

## 🔒 Configuraciones de Seguridad Adicionales

### Permisos de Base de Datos
```bash
# En PythonAnywhere bash console
chmod 600 /home/tu-usuario/tu-repositorio/db.sqlite3
```

### Verificar Configuración de Seguridad
```bash
workon contratos_env
python manage.py check --deploy
```

---

## 📊 Monitoreo Post-Deployment

### Ver Logs de Errores
1. En PythonAnywhere, ve a la pestaña "Web"
2. Mira la sección "Log files"
3. Haz clic en "error.log" para ver errores del servidor
4. También puedes ver tus logs personalizados:
```bash
tail -f ~/tu-repositorio/logs/django_errors.log
```

### Verificar Funcionalidades
- [ ] Login funciona correctamente
- [ ] Dashboard carga sin errores
- [ ] Archivos estáticos se cargan correctamente
- [ ] Formularios funcionan
- [ ] Base de datos funciona correctamente
- [ ] No hay errores en los logs

---

## 🔄 Actualizaciones Futuras

Cuando hagas cambios en tu código:

```bash
cd ~/tu-repositorio
workon contratos_env

# Actualizar código desde Git
git pull

# Si hay cambios en modelos
python manage.py migrate

# Si hay cambios en archivos estáticos
python manage.py collectstatic --noinput

# Recargar la web app (o usa el botón en el dashboard)
touch /var/www/tu-usuario_pythonanywhere_com_wsgi.py
```

O simplemente haz clic en "Reload" en el dashboard de Web.

---

## ⚠️ Problemas Comunes y Soluciones

### Error 502: Bad Gateway
- Verifica que el virtualenv esté correctamente configurado
- Revisa el archivo WSGI
- Verifica los logs de error
- Asegúrate de que todas las dependencias estén instaladas

### Static files no se cargan
- Ejecuta `python manage.py collectstatic --noinput`
- Verifica la configuración de Static files en el dashboard
- Asegúrate de que `STATIC_ROOT` esté configurado correctamente

### CSRF verification failed
- Verifica que `CSRF_TRUSTED_ORIGINS` incluya tu dominio de PythonAnywhere
- Asegúrate de que comience con `https://`
- Verifica que el archivo `.env` tenga la configuración correcta

### ImportError
- Asegúrate de que todas las dependencias estén instaladas: `pip install -r requirements.txt`
- Verifica que el virtualenv esté activado
- Verifica que el path en WSGI sea correcto

### Database is locked (SQLite)
- Normal en desarrollo con múltiples procesos
- En producción, si ocurre frecuentemente, considera migrar a MySQL
- Verifica que no haya procesos bloqueando la base de datos

---

## ✅ Checklist Final Pre-Deployment

### Antes de Desplegar
- [ ] Código subido a Git
- [ ] Script de verificación ejecutado sin errores críticos
- [ ] `collectstatic` ejecutado localmente
- [ ] Migraciones aplicadas localmente
- [ ] Superusuario creado localmente (para pruebas)
- [ ] Archivo `.env` preparado con valores correctos
- [ ] Documentación revisada

### En PythonAnywhere
- [ ] Repositorio clonado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas
- [ ] Archivo `.env` creado con SECRET_KEY segura
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] `collectstatic` ejecutado
- [ ] Web app creada
- [ ] Virtualenv configurado en web app
- [ ] WSGI file configurado correctamente
- [ ] Static files configurados
- [ ] Media files configurados
- [ ] Directorio de logs creado
- [ ] Permisos de base de datos configurados
- [ ] Web app recargada
- [ ] Sitio probado y funcionando

### Post-Deployment
- [ ] Login funciona correctamente
- [ ] Dashboard carga sin errores
- [ ] Archivos estáticos se cargan
- [ ] Formularios funcionan
- [ ] No hay errores en logs
- [ ] Configuración de seguridad verificada

---

## 📝 Notas Importantes

1. **SECRET_KEY**: Nunca compartas tu SECRET_KEY. Genera una nueva para producción.

2. **DEBUG**: Siempre debe estar en `False` en producción.

3. **ALLOWED_HOSTS**: Debe incluir tu dominio de PythonAnywhere.

4. **Base de Datos**: SQLite es adecuada para tu proyecto actual. Si creces, considera MySQL.

5. **Backups**: Configura backups regulares de la base de datos.

6. **Logs**: Revisa los logs regularmente para detectar problemas.

---

## 🎉 ¡Listo!

Tu sistema de gestión de contratos debería estar funcionando en:
`https://tu-usuario.pythonanywhere.com`

Para acceder:
1. Ve a `/login/`
2. Usa las credenciales del superusuario que creaste
3. ¡Disfruta tu sistema en producción!

---

**Última actualización:** 2025-01-27  
**Versión:** 1.0  
**Proyecto:** Sistema de Gestión de Contratos - Centro Comercial Avenida de Chile

