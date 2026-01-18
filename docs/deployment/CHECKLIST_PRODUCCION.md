# Checklist Pre-Deployment - Producción

## Fecha: $(Get-Date -Format "yyyy-MM-dd")

## Verificaciones Completadas

### ✅ Configuración
- [x] `wsgi.py` configurado para usar `settings_production.py`
- [x] `settings_production.py` requiere SECRET_KEY de variable de entorno
- [x] DEBUG configurado para False en producción
- [x] Directorio `logs/` creado
- [x] Configuración de seguridad HTTPS habilitada

### ✅ Código Limpio
- [x] `console.log` eliminados de templates críticos:
  - `templates/gestion/clausulas/auditoria.html`
  - `templates/gestion/contratos/form.html`
  - `templates/gestion/polizas/form.html`
  - `templates/gestion/otrosi/form.html`
- [x] No hay datos sensibles hardcodeados en código de producción
- [x] Archivos de depuración eliminados

### ✅ Archivos y Directorios
- [x] Todos los archivos requeridos presentes
- [x] Directorios necesarios creados
- [x] Migraciones presentes (65 archivos)

### ✅ Dependencias
- [x] `requirements.txt` completo con todas las dependencias necesarias
- [x] `env_example.txt` con todas las variables requeridas

### ✅ Seguridad
- [x] `.gitignore` configurado correctamente
- [x] SECRET_KEY requerida desde variable de entorno
- [x] Configuración de seguridad HTTPS habilitada
- [x] Protección CSRF configurada
- [x] Protección contra fuerza bruta (django-axes) configurada

## Pendientes para Producción

### ⚠️ Configuración Requerida en Servidor

1. **Variables de Entorno** - Configurar en PythonAnywhere (Panel Web → Environment variables):
   ```
   SECRET_KEY=tu-clave-secreta-super-segura-generada
   DEBUG=False
   ALLOWED_HOSTS=tu-usuario.pythonanywhere.com
   CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
   ```
   Ver guía: `CONFIGURAR_VARIABLES_PYTHONANYWHERE.md`

2. **Base de Datos** - Ejecutar migraciones:
   ```bash
   python manage.py migrate --settings=contratos.settings_production
   ```

3. **Archivos Estáticos** - Recolectar archivos estáticos:
   ```bash
   python manage.py collectstatic --noinput --settings=contratos.settings_production
   ```

4. **Directorios** - Crear en PythonAnywhere:
   ```bash
   cd ~/tu-proyecto
   mkdir -p logs
   mkdir -p media
   ```
   *(Los permisos en PythonAnywhere generalmente están correctos por defecto)*

5. **Usuario Admin** - Crear usuario administrador:
   ```bash
   python manage.py createsuperuser --settings=contratos.settings_production
   ```

## Scripts de Verificación

### Test Pre-Deploy
```bash
python scripts/test_pre_deploy.py
```

### Verificación de Deployment
```bash
python scripts/verificar_deployment.py
```

## Notas Importantes

1. **SECRET_KEY**: Debe ser una cadena aleatoria segura de al menos 50 caracteres
2. **ALLOWED_HOSTS**: Debe incluir el dominio de producción
3. **CSRF_TRUSTED_ORIGINS**: Debe incluir la URL completa con protocolo HTTPS
4. **Logs**: Revisar periódicamente `logs/django_errors.log` para errores
5. **Backups**: Configurar backups automáticos de la base de datos

## Cambios Realizados en Esta Sesión

1. ✅ Corregido `wsgi.py` para usar `settings_production.py` por defecto
2. ✅ Eliminados `console.log` de templates críticos
3. ✅ Creado script completo de test pre-deploy (`scripts/test_pre_deploy.py`)
4. ✅ Verificado directorio `logs/` existe
5. ✅ Corregido manejo de `CSRF_TRUSTED_ORIGINS` para filtrar valores vacíos y validar esquema
6. ✅ Ejecutado test pre-deploy exitosamente
7. ✅ Verificado con `python manage.py check --settings=contratos.settings_production` - Sin errores

## Estado Final

✅ **PROYECTO LISTO PARA DESPLIEGUE**

Solo requiere configuración de variables de entorno en el servidor de producción.
