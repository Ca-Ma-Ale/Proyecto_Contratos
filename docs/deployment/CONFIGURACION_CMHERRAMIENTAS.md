# Configuración para cmherramientascontables.pythonanywhere.com

## Variables de Entorno a Configurar en PythonAnywhere

### Paso 1: Generar SECRET_KEY

En una consola Bash de PythonAnywhere:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copia la clave generada.

---

### Paso 2: Configurar en el Panel Web de PythonAnywhere

1. **Ve al Dashboard de PythonAnywhere**
   - Inicia sesión en https://www.pythonanywhere.com
   - Haz clic en **"Web"** en el menú superior

2. **Desplázate hasta "Environment variables"**
   - Busca la sección **"Environment variables"**
   - Haz clic en **"Add a new environment variable"** para cada variable

3. **Agrega estas 4 variables:**

   **Variable 1:**
   - **Name:** `SECRET_KEY`
   - **Value:** `(pega la clave que generaste en el paso 1)`
   - Haz clic en el check ✓

   **Variable 2:**
   - **Name:** `DEBUG`
   - **Value:** `False`
   - Haz clic en el check ✓

   **Variable 3:**
   - **Name:** `ALLOWED_HOSTS`
   - **Value:** `cmherramientascontables.pythonanywhere.com`
   - Haz clic en el check ✓

   **Variable 4:**
   - **Name:** `CSRF_TRUSTED_ORIGINS`
   - **Value:** `https://cmherramientascontables.pythonanywhere.com`
   - Haz clic en el check ✓

4. **Recargar la aplicación**
   - En la parte superior de la página, haz clic en el botón verde **"Reload cmherramientascontables.pythonanywhere.com"**
   - Espera unos segundos hasta que aparezca el mensaje de éxito

---

## Resumen de Variables

```
SECRET_KEY = (tu-clave-generada)
DEBUG = False
ALLOWED_HOSTS = cmherramientascontables.pythonanywhere.com
CSRF_TRUSTED_ORIGINS = https://cmherramientascontables.pythonanywhere.com
```

---

## Verificación

Después de configurar, verifica que funcionó:

### Opción 1: Desde el navegador
- Visita: `https://cmherramientascontables.pythonanywhere.com`
- Si carga sin errores, está funcionando correctamente

### Opción 2: Desde la consola Bash

```bash
# Activar tu entorno virtual (si usas uno)
workon tu-entorno-virtual

# Verificar variables
python3 -c "import os; print('ALLOWED_HOSTS:', os.environ.get('ALLOWED_HOSTS', 'NO CONFIGURADA'))"
python3 -c "import os; print('CSRF_TRUSTED_ORIGINS:', os.environ.get('CSRF_TRUSTED_ORIGINS', 'NO CONFIGURADA'))"
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

## ⚠️ Notas Importantes

1. **ALLOWED_HOSTS** debe ser exactamente: `cmherramientascontables.pythonanywhere.com`
   - Sin `http://` o `https://`
   - Sin espacios al inicio o final

2. **CSRF_TRUSTED_ORIGINS** debe ser exactamente: `https://cmherramientascontables.pythonanywhere.com`
   - Con `https://` al inicio
   - Sin espacios al inicio o final

3. **Después de agregar cada variable**, haz clic en el check ✓ para guardarla

4. **Después de agregar todas las variables**, haz clic en **"Reload"** para aplicar los cambios

---

## 🆘 Solución de Problemas

### Error: "DisallowedHost"

**Causa:** El dominio no está en `ALLOWED_HOSTS` o tiene un formato incorrecto.

**Solución:**
1. Verifica que `ALLOWED_HOSTS` sea exactamente: `cmherramientascontables.pythonanywhere.com`
2. No debe tener `http://` o `https://`
3. No debe tener espacios
4. Haz clic en "Reload" después de corregir

### Error: "CSRF verification failed"

**Causa:** La URL no está en `CSRF_TRUSTED_ORIGINS` o tiene un formato incorrecto.

**Solución:**
1. Verifica que `CSRF_TRUSTED_ORIGINS` sea exactamente: `https://cmherramientascontables.pythonanywhere.com`
2. Debe comenzar con `https://`
3. No debe tener espacios
4. Haz clic en "Reload" después de corregir

---

## ✅ Checklist

- [ ] SECRET_KEY generada y configurada
- [ ] DEBUG configurado como `False`
- [ ] ALLOWED_HOSTS configurado como `cmherramientascontables.pythonanywhere.com`
- [ ] CSRF_TRUSTED_ORIGINS configurado como `https://cmherramientascontables.pythonanywhere.com`
- [ ] Todas las variables guardadas (check ✓ en cada una)
- [ ] Aplicación recargada (botón Reload)
- [ ] Sitio web accesible sin errores

---

**¡Listo!** Tu aplicación debería estar funcionando correctamente en `https://cmherramientascontables.pythonanywhere.com`
