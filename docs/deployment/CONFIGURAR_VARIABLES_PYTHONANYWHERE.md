# 🚀 Configurar Variables de Entorno en PythonAnywhere - Guía Rápida

## Método Más Fácil y Recomendado

### Paso 1: Generar SECRET_KEY

Abre una **consola Bash** en PythonAnywhere y ejecuta:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Copia la clave que aparece** (será algo como: `django-insecure-abc123xyz...`)

---

### Paso 2: Configurar en el Panel Web

1. **Ve al Dashboard de PythonAnywhere**
   - Inicia sesión en https://www.pythonanywhere.com
   - En el menú superior, haz clic en **"Web"**

2. **Desplázate hasta "Environment variables"**
   - Busca la sección que dice **"Environment variables"**
   - Haz clic en **"Add a new environment variable"**

3. **Agrega cada variable una por una:**

   **Variable 1:**
   - **Name:** `SECRET_KEY`
   - **Value:** `(pega la clave que copiaste en el paso 1)`
   - Haz clic en el check ✓

   **Variable 2:**
   - **Name:** `DEBUG`
   - **Value:** `False`
   - Haz clic en el check ✓

   **Variable 3:**
   - **Name:** `ALLOWED_HOSTS`
   - **Value:** `tu-usuario.pythonanywhere.com`
     *(Reemplaza "tu-usuario" con tu nombre de usuario real)*
   - Haz clic en el check ✓

   **Variable 4:**
   - **Name:** `CSRF_TRUSTED_ORIGINS`
   - **Value:** `https://tu-usuario.pythonanywhere.com`
     *(Con https:// y tu nombre de usuario)*
   - Haz clic en el check ✓

4. **Recargar la aplicación**
   - En la parte superior de la página, haz clic en el botón verde **"Reload tu-usuario.pythonanywhere.com"**
   - Espera unos segundos hasta que aparezca el mensaje de éxito

---

## ✅ Verificar que Funcionó

### Opción 1: Desde el Panel Web
- Ve a tu sitio: `https://tu-usuario.pythonanywhere.com`
- Si carga sin errores, ¡está funcionando!

### Opción 2: Desde la Consola Bash

```bash
# Activar tu entorno virtual (si usas uno)
workon tu-entorno-virtual

# Verificar variables
python3 -c "import os; print('SECRET_KEY:', 'OK' if os.environ.get('SECRET_KEY') else 'NO CONFIGURADA')"
python3 -c "import os; print('DEBUG:', os.environ.get('DEBUG', 'NO CONFIGURADA'))"
python3 -c "import os; print('ALLOWED_HOSTS:', os.environ.get('ALLOWED_HOSTS', 'NO CONFIGURADA'))"
```

### Opción 3: Verificar con Django

```bash
cd ~/tu-proyecto
workon tu-entorno-virtual
python manage.py check --settings=contratos.settings_production
```

Deberías ver:
```
System check identified no issues (0 silenced).
```

---

## 📸 Capturas de Pantalla (Referencia Visual)

### Dónde encontrar "Environment variables":

```
Dashboard → Web → (Desplázate hacia abajo) → Environment variables
```

### Cómo se ve al agregar una variable:

```
┌─────────────────────────────────────┐
│ Environment variables                │
├─────────────────────────────────────┤
│ Name:  [SECRET_KEY        ]         │
│ Value: [tu-clave-aqui...  ]         │
│        [✓] Add                       │
└─────────────────────────────────────┘
```

---

## 🔄 Método Alternativo: Archivo .env

Si prefieres usar un archivo `.env`:

### Paso 1: Crear archivo .env

En una consola Bash:

```bash
cd ~/tu-proyecto
nano .env
```

### Paso 2: Agregar contenido

Pega esto (ajusta los valores):

```bash
SECRET_KEY=tu-clave-generada-aqui
DEBUG=False
ALLOWED_HOSTS=tu-usuario.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://tu-usuario.pythonanywhere.com
```

### Paso 3: Guardar

- Presiona `Ctrl + O` (guardar)
- Presiona `Enter` (confirmar)
- Presiona `Ctrl + X` (salir)

### Paso 4: Modificar WSGI

1. Ve a **Web** → **WSGI configuration file**
2. Agrega esto **al inicio** del archivo (antes de importar Django):

```python
import os
from pathlib import Path

# Cargar variables de entorno desde .env
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
```

3. Guarda y haz clic en **"Reload"**

---

## ⚠️ Errores Comunes y Soluciones

### Error: "SECRET_KEY no está configurada"

**Solución:**
1. Verifica que agregaste la variable en el panel web
2. Asegúrate de hacer clic en el check ✓ después de agregar cada variable
3. Haz clic en "Reload" después de agregar todas las variables

### Error: "DisallowedHost"

**Solución:**
1. Verifica que `ALLOWED_HOSTS` tenga exactamente: `tu-usuario.pythonanywhere.com`
2. No incluyas `http://` o `https://` en `ALLOWED_HOSTS`
3. Haz clic en "Reload"

### Error: "CSRF verification failed"

**Solución:**
1. Verifica que `CSRF_TRUSTED_ORIGINS` tenga: `https://tu-usuario.pythonanywhere.com`
2. **Debe** incluir `https://` al inicio
3. Haz clic en "Reload"

### Las variables no se cargan

**Solución:**
1. Verifica que el nombre de la variable sea exacto (mayúsculas/minúsculas)
2. No debe haber espacios antes o después del nombre
3. Reinicia la aplicación web (botón Reload)
4. Si usas .env, verifica que el archivo esté en la raíz del proyecto

---

## 📋 Checklist Rápido

- [ ] Generé una SECRET_KEY segura
- [ ] Agregué `SECRET_KEY` en Environment variables
- [ ] Agregué `DEBUG=False` en Environment variables
- [ ] Agregué `ALLOWED_HOSTS` con mi dominio de PythonAnywhere
- [ ] Agregué `CSRF_TRUSTED_ORIGINS` con https:// y mi dominio
- [ ] Hice clic en "Reload" después de agregar todas las variables
- [ ] Verifiqué que mi sitio carga correctamente
- [ ] Ejecuté `python manage.py check` sin errores

---

## 🎯 Ejemplo Completo

Supongamos que tu usuario de PythonAnywhere es `miempresa`:

**Variables a configurar:**

```
SECRET_KEY = django-insecure-abc123xyz789... (50+ caracteres)
DEBUG = False
ALLOWED_HOSTS = miempresa.pythonanywhere.com
CSRF_TRUSTED_ORIGINS = https://miempresa.pythonanywhere.com
```

**URL de tu sitio:**
```
https://miempresa.pythonanywhere.com
```

---

## 💡 Tips Adicionales

1. **Guarda tu SECRET_KEY en un lugar seguro**
   - Si la pierdes, los usuarios tendrán que iniciar sesión nuevamente
   - No la compartas públicamente

2. **Usa el método del Panel Web** (más fácil)
   - Es más visual y menos propenso a errores
   - PythonAnywhere lo recomienda

3. **Verifica después de cada cambio**
   - Siempre haz clic en "Reload" después de cambiar variables
   - Prueba que tu sitio carga correctamente

4. **Si algo falla**
   - Revisa los logs de error en la pestaña "Web"
   - Verifica que los nombres de las variables sean exactos
   - Asegúrate de que no haya espacios extra

---

## ✅ ¡Listo!

Una vez configuradas las variables y recargada la aplicación, tu sitio debería estar funcionando correctamente en producción.

**¿Necesitas ayuda?** Revisa `GUIA_CONFIGURAR_VARIABLES_ENTORNO.md` para más detalles y otras plataformas.
