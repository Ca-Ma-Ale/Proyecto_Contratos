# 🚀 Guía Rápida: Despliegue desde GitHub a PythonAnywhere

Esta guía te ayudará a desplegar tu proyecto desde GitHub a PythonAnywhere de forma rápida.

## 📋 Requisitos Previos

- ✅ Repositorio en GitHub con el código actualizado
- ✅ Cuenta en PythonAnywhere (gratuita funciona perfectamente)
- ✅ Acceso SSH a PythonAnywhere (incluido en todas las cuentas)

---

## 🔧 Paso 1: Preparar el Código en GitHub

### 1.1 Verificar que el código esté listo

Antes de hacer push, asegúrate de:

```bash
# Verificar que no haya archivos sensibles
git status

# Verificar que .env NO esté en el repositorio
git ls-files | grep .env

# Si aparece .env, eliminarlo del tracking:
# git rm --cached .env
```

### 1.2 Hacer commit y push

```bash
# Agregar cambios
git add .

# Commit con mensaje descriptivo
git commit -m "Preparación para deployment en PythonAnywhere"

# Push a GitHub
git push origin main
# (o git push origin master según tu rama principal)
```

---

## 🌐 Paso 2: Configurar PythonAnywhere

### 2.1 Crear cuenta y abrir Bash Console

1. Ve a [pythonanywhere.com](https://www.pythonanywhere.com/)
2. Crea una cuenta gratuita o inicia sesión
3. Ve a "Consoles" → "Bash"

### 2.2 Clonar el Repositorio desde GitHub

```bash
# Clonar tu repositorio desde GitHub
git clone https://github.com/Ca-Ma-Ale/Proyecto_Contratos.git

# Entrar al directorio del proyecto
cd Proyecto_Contratos

# Verificar que se clonó correctamente
ls -la
```

**Nota:** Si el repositorio es privado, necesitarás configurar autenticación:
- Usar SSH: `git clone git@github.com:Ca-Ma-Ale/Proyecto_Contratos.git`
- O usar token de acceso personal en la URL

---

## 🐍 Paso 3: Configurar Entorno Virtual

```bash
# Crear entorno virtual con Python 3.10
mkvirtualenv --python=/usr/bin/python3.10 contratos_env

# El entorno se activa automáticamente
# Si necesitas activarlo después:
workon contratos_env

# Instalar dependencias
pip install -r requirements.txt
```

---

## ⚙️ Paso 4: Configurar Variables de Entorno

```bash
# Crear archivo .env desde la plantilla
cp env_example.txt .env

# Editar el archivo .env
nano .env
```

**Contenido mínimo del archivo `.env`:**

```env
SECRET_KEY=genera-una-clave-secreta-super-segura-aqui
DEBUG=False
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
```

**Generar SECRET_KEY:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Guarda el archivo con `Ctrl+O`, Enter, `Ctrl+X`

---

## 🗄️ Paso 5: Configurar Base de Datos

```bash
# Asegúrate de estar en el directorio del proyecto
cd ~/Proyecto_Contratos

# Activar entorno virtual
workon contratos_env

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
# Ingresa: usuario, email (opcional), contraseña

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Crear directorio de logs
mkdir -p logs
touch logs/django_errors.log
chmod 755 logs
```

---

## 🌐 Paso 6: Configurar Web App en PythonAnywhere

### 6.1 Crear Web App

1. En el Dashboard, ve a "Web"
2. Haz clic en "Add a new web app"
3. Selecciona **"Manual configuration"** (NO selecciones Django)
4. Selecciona **Python 3.10**
5. Haz clic en "Next"

### 6.2 Configurar Virtualenv

1. En la página de configuración de tu web app
2. En la sección "Virtualenv":
   - Ingresa: `/home/tu-usuario/.virtualenvs/contratos_env`
3. Haz clic en el check mark

### 6.3 Configurar WSGI File

1. En la sección "Code", haz clic en el link de **"WSGI configuration file"**
2. Borra todo el contenido
3. Pega el siguiente código (ajusta `tu-usuario` y la ruta del repositorio):

```python
import os
import sys

# Agregar el directorio del proyecto al path
path = '/home/tu-usuario/Proyecto_Contratos'
if path not in sys.path:
    sys.path.append(path)

# Configurar Django para producción
os.environ['DJANGO_SETTINGS_MODULE'] = 'contratos.settings_production'

# Cargar variables de entorno desde .env
from pathlib import Path
env_file = Path('/home/tu-usuario/Proyecto_Contratos/.env')
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

4. Guarda el archivo con el botón **"Save"**

### 6.4 Configurar Static Files

1. En la página de configuración de tu web app
2. En la sección **"Static files"**, agrega:
   - **URL:** `/static/`
   - **Directory:** `/home/tu-usuario/Proyecto_Contratos/staticfiles`
3. Agrega otra entrada:
   - **URL:** `/media/`
   - **Directory:** `/home/tu-usuario/Proyecto_Contratos/media`

---

## ✅ Paso 7: Recargar y Probar

1. En la página "Web" de PythonAnywhere
2. Haz clic en el botón verde **"Reload tu-usuario.pythonanywhere.com"**
3. Espera unos segundos
4. Visita tu sitio: `https://tu-usuario.pythonanywhere.com`
5. Prueba el login con las credenciales del superusuario

---

## 🔄 Actualizar el Proyecto (Cuando hagas cambios)

Cuando actualices el código en GitHub:

```bash
# En PythonAnywhere bash console
cd ~/Proyecto_Contratos
workon contratos_env

# Actualizar código desde GitHub
git pull

# Si hay cambios en modelos
python manage.py migrate

# Si hay cambios en archivos estáticos
python manage.py collectstatic --noinput

# Recargar la web app
# Opción 1: Usar el botón "Reload" en el dashboard Web
# Opción 2: Tocar el archivo WSGI
touch /var/www/tu-usuario_pythonanywhere_com_wsgi.py
```

---

## 🔒 Configuraciones de Seguridad

### Permisos de Base de Datos

```bash
# En PythonAnywhere bash console
chmod 600 /home/tu-usuario/Proyecto_Contratos/db.sqlite3
```

### Verificar Configuración de Seguridad

```bash
workon contratos_env
python manage.py check --deploy
```

---

## 📊 Monitoreo

### Ver Logs de Errores

1. En PythonAnywhere, ve a la pestaña "Web"
2. Mira la sección "Log files"
3. Haz clic en "error.log" para ver errores del servidor
4. También puedes ver tus logs personalizados:

```bash
tail -f ~/Proyecto_Contratos/logs/django_errors.log
```

---

## ⚠️ Problemas Comunes

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

---

## ✅ Checklist Rápido

### Antes de hacer push a GitHub
- [ ] Código probado localmente
- [ ] No hay archivos `.env` en el repositorio
- [ ] `requirements.txt` actualizado
- [ ] Cambios commiteados
- [ ] Push realizado a GitHub

### En PythonAnywhere
- [ ] Repositorio clonado desde GitHub
- [ ] Entorno virtual creado
- [ ] Dependencias instaladas
- [ ] Archivo `.env` creado con SECRET_KEY segura
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] `collectstatic` ejecutado
- [ ] Web app creada
- [ ] Virtualenv configurado
- [ ] WSGI file configurado
- [ ] Static files configurados
- [ ] Web app recargada
- [ ] Sitio probado y funcionando

---

## 🎉 ¡Listo!

Tu sistema debería estar funcionando en:
`https://tu-usuario.pythonanywhere.com`

Para acceder:
1. Ve a `/login/`
2. Usa las credenciales del superusuario que creaste
3. ¡Disfruta tu sistema en producción!

---

**Última actualización:** 2025-01-27  
**Versión:** 1.0
