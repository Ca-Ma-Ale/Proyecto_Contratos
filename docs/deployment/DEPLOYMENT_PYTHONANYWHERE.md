# 🚀 Guía de Deployment en PythonAnywhere

Esta guía paso a paso te ayudará a desplegar tu Sistema de Gestión de Contratos en PythonAnywhere.

## 📋 Requisitos Previos

1. Cuenta en [PythonAnywhere](https://www.pythonanywhere.com/) (la cuenta gratuita funciona perfectamente)
2. Tu código del proyecto listo para subir
   - **Opción A:** Código en un repositorio Git (GitHub, GitLab, etc.) - Recomendado
   - **Opción B:** Código local que subirás directamente a PythonAnywhere

## 🔧 Paso 1: Configuración Inicial

### 1.1 Crear cuenta en PythonAnywhere
- Ve a [pythonanywhere.com](https://www.pythonanywhere.com/)
- Crea una cuenta gratuita (Beginner account)
- Inicia sesión

### 1.2 Abrir Bash Console
- En el Dashboard, ve a "Consoles"
- Haz clic en "Bash"

## 📥 Paso 2: Subir el Código

### Opción A: Usando Git (Recomendado)

```bash
# Clonar tu repositorio
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio

# O si usas otro servicio de Git, ajusta la URL
```

### Opción B: Subir Código Directamente

1. **Usando File Manager de PythonAnywhere:**
   - Ve a "Files" en el Dashboard
   - Navega a `/home/tu-usuario/`
   - Haz clic en "Upload a file" o arrastra tu proyecto

2. **Usando Consola Bash:**
   ```bash
   # Crea el directorio del proyecto
   mkdir -p ~/Proyecto_Contratos
   cd ~/Proyecto_Contratos
   
   # Luego sube tus archivos usando el File Manager o scp
   ```

**Nota:** Si subes directamente, asegúrate de incluir todos los archivos excepto:
- `venv/` o `env/` (entorno virtual)
- `__pycache__/`
- `*.pyc`
- `.env` (si tiene datos sensibles)

## 🐍 Paso 3: Crear Entorno Virtual

```bash
# Crear entorno virtual con Python 3.10
mkvirtualenv --python=/usr/bin/python3.10 contratos_env

# Activar el entorno virtual (se activa automáticamente al crearlo)
# Si necesitas activarlo manualmente después:
workon contratos_env

# Instalar dependencias
pip install -r requirements.txt
```

## ⚙️ Paso 4: Configurar Variables de Entorno

```bash
# Crear archivo .env
nano .env
```

Copia y pega lo siguiente (ajusta los valores):

```env
SECRET_KEY=genera-una-clave-secreta-super-segura-aqui-usando-python
DEBUG=False
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
```

Para generar una SECRET_KEY segura:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Guarda el archivo con `Ctrl+O`, Enter, `Ctrl+X`

## 🗄️ Paso 5: Configurar Base de Datos

```bash
# Asegúrate de estar en el directorio del proyecto
cd ~/tu-repositorio

# Activar entorno virtual
workon contratos_env

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
# Ingresa: usuario, email (opcional), contraseña

# Recolectar archivos estáticos
python manage.py collectstatic --noinput
```

## 🌐 Paso 6: Configurar Web App

### 6.1 Crear Web App
1. En el Dashboard de PythonAnywhere, ve a "Web"
2. Haz clic en "Add a new web app"
3. Selecciona "Manual configuration" (NO selecciones Django)
4. Selecciona Python 3.10
5. Haz clic en "Next"

### 6.2 Configurar Virtualenv
1. En la página de configuración de tu web app
2. En la sección "Virtualenv":
   - Ingresa: `/home/tu-usuario/.virtualenvs/contratos_env`
3. Haz clic en el check mark

### 6.3 Configurar WSGI File
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

# Configurar Django
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

### 6.4 Configurar Static Files
1. En la página de configuración de tu web app
2. En la sección "Static files", agrega:
   - URL: `/static/`
   - Directory: `/home/tu-usuario/tu-repositorio/staticfiles`
3. Agrega otra entrada:
   - URL: `/media/`
   - Directory: `/home/tu-usuario/tu-repositorio/media`

## 🔄 Paso 7: Crear directorio de logs

```bash
cd ~/tu-repositorio
mkdir -p logs
touch logs/django_errors.log
```

## ✅ Paso 8: Recargar y Probar

1. En la página "Web" de PythonAnywhere
2. Haz clic en el botón verde "Reload tu-usuario.pythonanywhere.com"
3. Visita tu sitio: `https://tu-usuario.pythonanywhere.com`

## 🔐 Paso 9: Configurar Seguridad Adicional

### 9.1 Cambiar SECRET_KEY
```bash
cd ~/tu-repositorio
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Copia la clave generada

nano .env
# Reemplaza SECRET_KEY con la nueva clave
# Guarda y cierra
```

### 9.2 Verificar configuraciones
```bash
workon contratos_env
python manage.py check --deploy
```

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

## 📊 Monitoreo y Logs

### Ver logs de errores
1. En PythonAnywhere, ve a la pestaña "Web"
2. Mira la sección "Log files"
3. Haz clic en "error.log" para ver errores del servidor
4. También puedes ver tus logs personalizados en `~/tu-repositorio/logs/django_errors.log`

### Ver logs desde consola
```bash
tail -f ~/tu-repositorio/logs/django_errors.log
```

## ⚠️ Problemas Comunes

### Error 502: Bad Gateway
- Verifica que el virtualenv esté correctamente configurado
- Revisa el archivo WSGI
- Verifica los logs de error

### ImportError
- Asegúrate de que todas las dependencias estén instaladas
- Verifica que el path en WSGI sea correcto

### Static files no se cargan
- Ejecuta `python manage.py collectstatic`
- Verifica la configuración de Static files en el dashboard

### CSRF verification failed
- Verifica que `CSRF_TRUSTED_ORIGINS` incluya tu dominio de PythonAnywhere
- Asegúrate de que comience con `https://`

## 📝 Checklist de Deployment

- [ ] Código subido a Git
- [ ] Entorno virtual creado
- [ ] Dependencias instaladas
- [ ] Archivo .env configurado con SECRET_KEY segura
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] collectstatic ejecutado
- [ ] Web app creada en PythonAnywhere
- [ ] Virtualenv configurado en web app
- [ ] WSGI file configurado correctamente
- [ ] Static files configurados
- [ ] Media files configurados
- [ ] Directorio de logs creado
- [ ] Web app recargada
- [ ] Sitio probado y funcionando
- [ ] Login funciona correctamente

## 🎉 ¡Listo!

Tu sistema de gestión de contratos debería estar funcionando en:
`https://tu-usuario.pythonanywhere.com`

Para acceder:
1. Ve a `/login/`
2. Usa las credenciales del superusuario que creaste
3. ¡Disfruta tu sistema en producción!

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs de error en PythonAnywhere
2. Consulta la documentación de Django
3. Revisa los foros de PythonAnywhere
4. Verifica que todas las configuraciones de seguridad estén correctas

---

**Última actualización:** Octubre 2025
**Compatible con:** Django 5.0+, Python 3.10+, PythonAnywhere

