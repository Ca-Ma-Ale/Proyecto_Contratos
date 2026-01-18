# 🚀 Guía de Producción - Sistema de Gestión de Contratos

## 📋 Preparación para Producción

### ⚠️ **TAREAS CRÍTICAS ANTES DE PRODUCCIÓN**

#### 1. **Aplicar Decoradores de Seguridad** (15 min)
```python
# En gestion/views.py - Agregar al inicio:
from gestion.decorators import login_required_custom, admin_required

# Aplicar a cada vista:
@login_required_custom
def dashboard(request):
    ...

@admin_required
def configuracion_empresa(request):
    ...
```

**Vistas que necesitan decorador:**
- `dashboard` → @login_required_custom
- `nuevo_contrato` → @login_required_custom
- `editar_contrato` → @login_required_custom
- `lista_contratos` → @login_required_custom
- `detalle_contrato` → @login_required_custom
- `nuevo_arrendatario` → @login_required_custom
- `nuevo_local` → @login_required_custom
- `gestionar_polizas` → @login_required_custom
- `nueva_poliza` → @login_required_custom
- `editar_poliza` → @login_required_custom
- `validar_poliza` → @login_required_custom
- `eliminar_poliza` → @login_required_custom
- `configuracion_empresa` → @admin_required
- `eliminar_contrato` → @admin_required

#### 2. **Limpiar Código de Debug** (10 min)
```python
# En gestion/views.py - Comentar prints:
# print("\n" + "="*80)
# print("INICIANDO GUARDADO DE PÓLIZA")
# ... (comentar todos los prints)
```

#### 3. **Crear Archivo .env** (5 min)
```bash
# Copiar plantilla
copy env_example.txt .env

# Generar SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Editar .env
notepad .env
```

**Contenido del .env:**
```env
SECRET_KEY=tu-clave-secreta-generada
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com
```

#### 4. **Crear Directorios** (1 min)
```bash
mkdir logs
mkdir media
echo. > logs\django_errors.log
```

#### 5. **Testing Local** (5 min)
```bash
# Probar con DEBUG=False
python manage.py runserver
# Verificar que todo funciona
```

## 🌐 Deployment en PythonAnywhere

### **Paso 1: Preparar Repositorio**
```bash
# Subir a Git
git add .
git commit -m "Preparado para producción"
git push
```

### **Paso 2: Crear Cuenta en PythonAnywhere**
1. Ve a [pythonanywhere.com](https://www.pythonanywhere.com/)
2. Crea cuenta gratuita
3. Inicia sesión

### **Paso 3: Clonar Proyecto**
```bash
# En consola de PythonAnywhere
git clone https://github.com/tu-usuario/tu-repo.git
cd tu-repo
```

### **Paso 4: Configurar Entorno Virtual**
```bash
# Crear virtualenv
mkvirtualenv --python=/usr/bin/python3.10 contratos_env

# Instalar dependencias
pip install -r requirements.txt
```

### **Paso 5: Configurar Variables de Entorno**
```bash
# Crear .env en servidor
nano .env
```

**Contenido para producción:**
```env
SECRET_KEY=clave-super-secreta-para-produccion
DEBUG=False
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
```

### **Paso 6: Configurar Base de Datos**
```bash
# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar archivos estáticos
python manage.py collectstatic --noinput
```

### **Paso 7: Configurar Web App**
1. **Crear Web App:**
   - Ve a "Web" en PythonAnywhere
   - "Add a new web app"
   - Selecciona "Manual configuration"
   - Python 3.10

2. **Configurar Virtualenv:**
   - Virtualenv: `/home/tu-usuario/.virtualenvs/contratos_env`

3. **Configurar WSGI:**
```python
import os
import sys

path = '/home/tu-usuario/tu-repo'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'contratos.settings_production'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

4. **Configurar Static Files:**
   - URL: `/static/`
   - Directory: `/home/tu-usuario/tu-repo/staticfiles`
   - URL: `/media/`
   - Directory: `/home/tu-usuario/tu-repo/media`

### **Paso 8: Recargar y Probar**
1. Haz clic en "Reload" en PythonAnywhere
2. Visita tu sitio: `https://tu-usuario.pythonanywhere.com`
3. Prueba el login y funcionalidades

## 🔒 Configuración de Seguridad

### **Variables de Entorno Críticas**
```env
# OBLIGATORIAS
SECRET_KEY=clave-super-secreta
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com

# OPCIONALES
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### **Verificación de Seguridad**
```bash
# Verificar configuración
python manage.py check --deploy
```

## 📊 Monitoreo y Logs

### **Ver Logs de Errores**
```bash
# En PythonAnywhere
tail -f ~/tu-repo/logs/django_errors.log
```

### **Logs de PythonAnywhere**
1. Ve a "Web" → "Log files"
2. Revisa "error.log" para errores del servidor

## 🔄 Actualizaciones Futuras

### **Proceso de Actualización**
```bash
# En PythonAnywhere
cd ~/tu-repo
workon contratos_env

# Actualizar código
git pull

# Si hay cambios en modelos
python manage.py migrate

# Si hay cambios en archivos estáticos
python manage.py collectstatic --noinput

# Recargar
touch /var/www/tu-usuario_pythonanywhere_com_wsgi.py
```

## ⚠️ Problemas Comunes

### **Error 502: Bad Gateway**
- Verificar virtualenv configurado
- Revisar archivo WSGI
- Verificar logs de error

### **Static Files no cargan**
```bash
python manage.py collectstatic --noinput
# Verificar mapeo en PythonAnywhere
```

### **CSRF Error**
- Verificar `CSRF_TRUSTED_ORIGINS`
- Debe incluir `https://`
- Verificar `{% csrf_token %}` en formularios

### **ImportError**
```bash
# Verificar dependencias
pip install -r requirements.txt
# Verificar virtualenv activado
```

## ✅ Checklist de Producción

### **Antes de Lanzar:**
- [ ] Decoradores aplicados a todas las vistas
- [ ] Código de debug limpiado
- [ ] Archivo .env configurado con valores seguros
- [ ] SECRET_KEY única generada
- [ ] DEBUG=False configurado
- [ ] Directorios logs/ y media/ creados
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] collectstatic ejecutado
- [ ] Testing local completo
- [ ] Código subido a Git

### **Durante Deployment:**
- [ ] Cuenta PythonAnywhere creada
- [ ] Proyecto clonado
- [ ] Virtualenv configurado
- [ ] Dependencias instaladas
- [ ] .env configurado en servidor
- [ ] Web app creada
- [ ] WSGI configurado
- [ ] Static files configurados
- [ ] Media files configurados
- [ ] Web app recargada

### **Después de Lanzar:**
- [ ] Login funciona
- [ ] Dashboard carga
- [ ] Crear contrato funciona
- [ ] Formateo funciona
- [ ] Logs funcionando
- [ ] HTTPS funcionando
- [ ] Usuarios pueden acceder

## 📞 Soporte

### **Recursos de Ayuda:**
- [Documentación Django](https://docs.djangoproject.com/)
- [PythonAnywhere Help](https://help.pythonanywhere.com/)
- [Foros PythonAnywhere](https://www.pythonanywhere.com/forums/)

### **Contactos de Emergencia:**
- **Desarrollador:** [Tu información]
- **Administrador:** [Información del admin]
- **Soporte PythonAnywhere:** Foros oficiales

## 🎉 ¡Listo para Producción!

Una vez completadas todas las tareas:

1. **Tu sistema estará funcionando en:** `https://tu-usuario.pythonanywhere.com`
2. **Acceso:** `/login/` con las credenciales del superusuario
3. **Monitoreo:** Revisa logs regularmente
4. **Mantenimiento:** Actualiza según sea necesario

---

**Última actualización:** Octubre 2025  
**Versión:** 2.0 - Producción Ready  
**Tiempo estimado:** ~1 hora para deployment completo
