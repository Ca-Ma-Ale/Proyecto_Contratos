# ✅ Verificación Pre-Push a GitHub

Antes de hacer push a GitHub, verifica lo siguiente:

## 🔍 Verificaciones Críticas

### 1. Archivos Sensibles NO deben estar en Git

```bash
# Verificar que .env NO esté siendo rastreado
git ls-files | grep .env

# Si aparece .env, eliminarlo del tracking:
git rm --cached .env
git commit -m "Eliminar .env del tracking de git"
```

**Archivos que NO deben estar en Git:**
- `.env`
- `.env.local`
- `.env.production`
- `db.sqlite3`
- `*.log`
- `venv/` o `env/`
- `__pycache__/`
- `backups/`
- `media/`
- `staticfiles/`

### 2. Archivos que SÍ deben estar en Git

- ✅ `env_example.txt` (plantilla de variables de entorno)
- ✅ `requirements.txt`
- ✅ `manage.py`
- ✅ `contratos/settings.py`
- ✅ `contratos/settings_production.py`
- ✅ `contratos/wsgi.py`
- ✅ `.gitignore`
- ✅ `README.md`
- ✅ `docs/` (documentación)
- ✅ `scripts/` (scripts de utilidad)
- ✅ `templates/`
- ✅ `static/` (archivos fuente estáticos)
- ✅ `gestion/` (aplicación Django)

### 3. Verificar .gitignore

Asegúrate de que `.gitignore` incluya:

```
.env
.env.local
.env.production
db.sqlite3
*.log
venv/
env/
__pycache__/
backups/
media/
staticfiles/
```

### 4. Verificar Cambios Recientes

Los siguientes archivos fueron modificados/creados para el deployment:

- ✅ `contratos/settings_production.py` - Agregado django.contrib.humanize y configuración de email
- ✅ `scripts/verificar_deployment.py` - Script de verificación
- ✅ `docs/deployment/CHECKLIST_DEPLOYMENT_FINAL.md` - Checklist completo
- ✅ `docs/deployment/DEPLOYMENT_DESDE_GITHUB.md` - Guía de despliegue desde GitHub

### 5. Ejecutar Script de Verificación

```bash
# Ejecutar script de verificación antes de hacer push
python scripts/verificar_deployment.py
```

El script debe mostrar:
- ✅ Todos los archivos requeridos presentes
- ✅ Directorios creados
- ✅ Dependencias en requirements.txt
- ✅ Configuración correcta

## 📝 Comandos para hacer Push

```bash
# 1. Verificar estado
git status

# 2. Agregar cambios
git add .

# 3. Verificar que NO se agreguen archivos sensibles
git status

# 4. Commit
git commit -m "Preparación para deployment en PythonAnywhere

- Agregado django.contrib.humanize a settings_production.py
- Agregada configuración de email a settings_production.py
- Creado script de verificación pre-deployment
- Creada documentación de despliegue desde GitHub
- Mejorado manejo de CSRF_TRUSTED_ORIGINS"

# 5. Push a GitHub
git push origin main
# (o git push origin master según tu rama principal)
```

## ⚠️ Si encuentras archivos sensibles en Git

Si accidentalmente subiste archivos sensibles:

```bash
# Eliminar del tracking (NO del disco)
git rm --cached .env
git rm --cached db.sqlite3

# Commit
git commit -m "Eliminar archivos sensibles del tracking"

# Push
git push origin main

# IMPORTANTE: Si ya subiste archivos sensibles, cambia las credenciales:
# - Genera nueva SECRET_KEY
# - Cambia contraseñas de base de datos
# - Regenera tokens de API si los hay
```

## ✅ Checklist Final Pre-Push

- [ ] No hay archivos `.env` en el repositorio
- [ ] No hay `db.sqlite3` en el repositorio
- [ ] `.gitignore` está actualizado
- [ ] `requirements.txt` está actualizado
- [ ] Script de verificación ejecutado sin errores críticos
- [ ] Cambios probados localmente
- [ ] Mensaje de commit descriptivo
- [ ] Listo para hacer push

## 🚀 Después del Push

Una vez que hagas push a GitHub, sigue la guía:
`docs/deployment/DEPLOYMENT_DESDE_GITHUB.md`

---

**Última actualización:** 2025-01-27
