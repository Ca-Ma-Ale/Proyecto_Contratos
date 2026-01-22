# ⚠️ Verificación de Estructura en GitHub

## Problema Detectado

En GitHub se ven nombres en español que no coinciden con la estructura estándar de Django:

### Nombres en GitHub (Español):
- ❌ `documentos` → Debería ser `docs`
- ❌ `gestión` → Debería ser `gestion`
- ❌ `guiones` → Debería ser `scripts`
- ❌ `estático/js` → Debería ser `static/js`
- ❌ `plantillas` → Debería ser `templates`
- ❌ `LÉAME.md` → Debería ser `README.md`
- ❌ `administrar.py` → Debería ser `manage.py`
- ❌ `requisitos.txt` → Debería ser `requirements.txt`
- ❌ `env_ejemplo.txt` → Debería ser `env_example.txt`

### Estructura Correcta (Local):
- ✅ `docs/` - Documentación
- ✅ `gestion/` - Aplicación Django
- ✅ `scripts/` - Scripts de utilidad
- ✅ `static/` - Archivos estáticos fuente
- ✅ `templates/` - Plantillas HTML
- ✅ `README.md` - Documentación principal
- ✅ `manage.py` - Script de gestión Django
- ✅ `requirements.txt` - Dependencias
- ✅ `env_example.txt` - Plantilla de variables de entorno

## ⚠️ Problemas que esto causa:

1. **Django no funcionará correctamente** - Django busca carpetas con nombres específicos
2. **Importaciones fallarán** - Los módulos Python requieren nombres sin acentos
3. **Deployment fallará** - PythonAnywhere espera la estructura estándar
4. **Scripts no funcionarán** - Los comandos de Django buscan `manage.py`

## ✅ Solución: Actualizar GitHub

Necesitas hacer push de la estructura correcta desde tu proyecto local:

### Opción 1: Renombrar en GitHub (Complejo)
Requiere múltiples commits y puede romper el historial.

### Opción 2: Hacer push de la estructura correcta (Recomendado)

```bash
# 1. Verificar que estás en la rama correcta
git status

# 2. Agregar todos los archivos con nombres correctos
git add .

# 3. Commit
git commit -m "Corregir estructura del proyecto a nombres estándar de Django"

# 4. Force push (si es necesario)
git push origin main --force
```

**⚠️ ADVERTENCIA:** Si otros colaboradores tienen el código, coordina con ellos antes de hacer force push.

## 📋 Verificación Post-Push

Después del push, verifica en GitHub que aparezcan:

- ✅ `docs/` (no "documentos")
- ✅ `gestion/` (no "gestión")
- ✅ `scripts/` (no "guiones")
- ✅ `static/` (no "estático")
- ✅ `templates/` (no "plantillas")
- ✅ `README.md` (no "LÉAME.md")
- ✅ `manage.py` (no "administrar.py")
- ✅ `requirements.txt` (no "requisitos.txt")
- ✅ `env_example.txt` (no "env_ejemplo.txt")
- ✅ `contratos/` con `settings.py`, `wsgi.py`, etc.

## 🔍 Verificar Archivos Críticos Faltantes

Asegúrate de que estos archivos estén en GitHub:

- ✅ `contratos/settings.py`
- ✅ `contratos/settings_production.py`
- ✅ `contratos/wsgi.py`
- ✅ `contratos/urls.py`
- ✅ `.gitignore`
- ✅ `requirements.txt`
- ✅ `manage.py`

## 🚀 Después de Corregir

Una vez que la estructura esté correcta en GitHub:

1. Seguir `docs/deployment/DEPLOYMENT_DESDE_GITHUB.md`
2. Clonar el repositorio en PythonAnywhere
3. El deployment debería funcionar correctamente

---

**Última actualización:** 2025-01-27
