# 🔐 Guía de Encriptación de Datos Sensibles

**Fecha:** 2025-01-27  
**Propósito:** Proteger información sensible almacenada en SQLite

---

## 📋 Resumen

Este sistema implementa encriptación automática para proteger datos sensibles almacenados en la base de datos SQLite, especialmente **contraseñas de email SMTP**.

---

## 🔑 Configuración Inicial

### Paso 1: Generar Clave de Encriptación

```bash
# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Generar clave de encriptación
python -c "from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())"
```

**Ejemplo de salida:**
```
k7gNU3sdo+OL0wNhqoVWhr3g6s1xYv72el/brIDm3L4=
```

### Paso 2: Configurar Variable de Entorno

Agregar la clave generada al archivo `.env`:

```env
# Encriptación de Datos Sensibles
ENCRYPTION_KEY=k7gNU3sdo+OL0wNhqoVWhr3g6s1xYv72el/brIDm3L4=
```

**⚠️ IMPORTANTE:**
- **NUNCA** compartas esta clave
- **NUNCA** la subas a Git (`.env` debe estar en `.gitignore`)
- **DIFERENTE** para cada entorno (desarrollo, producción)
- **GUÁRDALA** en un lugar seguro (gestor de contraseñas)

---

## 🔒 Datos Protegidos

### Contraseñas de Email SMTP

Las contraseñas de configuración de email se encriptan automáticamente:

- ✅ **Al guardar:** Se encripta automáticamente
- ✅ **Al usar:** Se desencripta automáticamente
- ✅ **En base de datos:** Solo se almacena versión encriptada
- ✅ **En admin:** Campo de contraseña oculto, solo campo de entrada

---

## 🛠️ Uso en el Sistema

### Crear/Editar Configuración de Email

1. **Ir a Admin Django:** `/admin/gestion/configuracionemail/`
2. **Crear nueva configuración:**
   - Llenar todos los campos
   - En "Contraseña", ingresar la contraseña en texto plano
   - Al guardar, se encripta automáticamente

3. **Editar configuración existente:**
   - Si dejas "Contraseña" en blanco → Mantiene la contraseña actual
   - Si ingresas nueva contraseña → Se encripta y reemplaza la anterior

### Uso Programático

```python
from gestion.models import ConfiguracionEmail

# Obtener configuración
config = ConfiguracionEmail.get_activa()

# La contraseña se desencripta automáticamente al usar
password = config.get_password()  # Retorna contraseña desencriptada

# Guardar nueva contraseña
config.set_password("nueva_contraseña")
config.save()
```

---

## 🔄 Migración de Datos Existentes

Si ya tienes contraseñas en texto plano en la base de datos:

### Opción 1: Comando Automático (Recomendado)

```bash
# Verificar qué se encriptará (sin guardar)
python manage.py encriptar_contraseñas_email --dry-run

# Encriptar todas las contraseñas
python manage.py encriptar_contraseñas_email

# Forzar re-encriptación (si cambiaste ENCRYPTION_KEY)
python manage.py encriptar_contraseñas_email --force
```

### Opción 2: Manual desde Admin

1. Ir a `/admin/gestion/configuracionemail/`
2. Editar cada configuración
3. Ingresar la contraseña nuevamente en el campo "Contraseña"
4. Guardar (se encriptará automáticamente)

---

## 🔧 Funcionamiento Técnico

### Módulo de Encriptación

**Archivo:** `gestion/utils_encryption.py`

**Funciones principales:**
- `encrypt_value(plain_text)`: Encripta texto plano
- `decrypt_value(encrypted_text)`: Desencripta texto encriptado
- `get_encryption_key()`: Obtiene clave desde variables de entorno
- `generate_encryption_key()`: Genera nueva clave

**Algoritmo:** Fernet (symmetric encryption)
- Basado en AES-128 en modo CBC
- Autenticación integrada
- Base64 encoding para almacenamiento

### Modelo ConfiguracionEmail

**Métodos agregados:**
- `set_password(plain_password)`: Encripta y guarda contraseña
- `get_password()`: Desencripta y retorna contraseña

**Campo modificado:**
- `email_host_password`: Cambiado de `CharField` a `TextField` (para texto encriptado más largo)

---

## ⚠️ Consideraciones Importantes

### Seguridad de la Clave

1. **ENCRYPTION_KEY debe ser única y segura**
   - Generar con el comando proporcionado
   - No usar SECRET_KEY directamente
   - Diferente para cada entorno

2. **Si pierdes ENCRYPTION_KEY:**
   - ❌ **NO podrás desencriptar las contraseñas existentes**
   - ✅ Deberás re-ingresar todas las contraseñas manualmente
   - ✅ **GUARDA la clave en un lugar seguro**

3. **Si cambias ENCRYPTION_KEY:**
   - Ejecutar: `python manage.py encriptar_contraseñas_email --force`
   - Esto re-encriptará todas las contraseñas con la nueva clave

### Compatibilidad

- ✅ **Funciona con SQLite** (actual)
- ✅ **Funciona con MySQL** (si migras en el futuro)
- ✅ **Funciona con PostgreSQL** (si migras en el futuro)
- ✅ **Sin cambios en el código de aplicación** (transparente)

---

## 🧪 Pruebas

### Verificar que la Encriptación Funciona

```python
# En shell de Django
python manage.py shell

from gestion.models import ConfiguracionEmail
from gestion.utils_encryption import encrypt_value, decrypt_value

# Obtener configuración
config = ConfiguracionEmail.get_activa()

# Verificar que la contraseña está encriptada en BD
print("En BD (encriptado):", config.email_host_password[:50] + "...")

# Desencriptar y mostrar (solo para pruebas)
password = config.get_password()
print("Desencriptado:", password)
```

### Probar Encriptación/Desencriptación

```python
from gestion.utils_encryption import encrypt_value, decrypt_value

texto = "mi_contraseña_secreta"
encriptado = encrypt_value(texto)
print("Encriptado:", encriptado)

desencriptado = decrypt_value(encriptado)
print("Desencriptado:", desencriptado)
print("¿Coinciden?", texto == desencriptado)  # Debe ser True
```

---

## 📝 Checklist de Implementación

### Antes de Producción

- [ ] Generar `ENCRYPTION_KEY` única
- [ ] Agregar `ENCRYPTION_KEY` a `.env` (desarrollo)
- [ ] Agregar `ENCRYPTION_KEY` a `.env` en servidor (producción)
- [ ] Verificar que `.env` está en `.gitignore`
- [ ] Ejecutar comando de migración: `python manage.py encriptar_contraseñas_email`
- [ ] Verificar que las contraseñas se encriptan correctamente
- [ ] Probar envío de emails (verificar que funciona con contraseñas encriptadas)
- [ ] Guardar `ENCRYPTION_KEY` en gestor de contraseñas seguro

### En Producción (PythonAnywhere)

1. **Generar clave:**
   ```bash
   python -c "from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())"
   ```

2. **Agregar a .env en servidor:**
   ```bash
   nano ~/tu_proyecto/.env
   # Agregar: ENCRYPTION_KEY=tu_clave_generada
   ```

3. **Encriptar contraseñas existentes:**
   ```bash
   workon contratos_env
   python manage.py encriptar_contraseñas_email
   ```

4. **Verificar funcionamiento:**
   - Probar envío de email desde el sistema
   - Verificar que funciona correctamente

---

## 🔍 Solución de Problemas

### Error: "ENCRYPTION_KEY debe estar configurada"

**Causa:** Variable de entorno no configurada

**Solución:**
1. Generar clave: `python -c "from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())"`
2. Agregar a `.env`: `ENCRYPTION_KEY=tu_clave`
3. Reiniciar servidor Django

---

### Error: "No se pudo desencriptar la contraseña"

**Causa:** `ENCRYPTION_KEY` incorrecta o cambiada

**Solución:**
1. Verificar que `ENCRYPTION_KEY` en `.env` es la correcta
2. Si cambió, re-ingresar contraseñas manualmente desde admin
3. O usar: `python manage.py encriptar_contraseñas_email --force` (si tienes acceso a las contraseñas)

---

### Error: "Error al encriptar"

**Causa:** Problema con la clave o formato

**Solución:**
1. Verificar formato de `ENCRYPTION_KEY` (debe ser base64 válido)
2. Regenerar clave si es necesario
3. Verificar que no hay espacios o caracteres especiales

---

## 📚 Referencias

- **Módulo de encriptación:** `gestion/utils_encryption.py`
- **Modelo:** `gestion/models.py` → `ConfiguracionEmail`
- **Admin:** `gestion/admin.py` → `ConfiguracionEmailAdmin`
- **Servicio de email:** `gestion/services/email_service.py`
- **Comando de migración:** `gestion/management/commands/encriptar_contraseñas_email.py`

---

## ✅ Beneficios Implementados

1. ✅ **Contraseñas de email encriptadas** en base de datos
2. ✅ **Encriptación transparente** (automática al guardar/usar)
3. ✅ **Sin cambios en código de aplicación** (excepto admin)
4. ✅ **Compatible con cualquier base de datos** (SQLite, MySQL, PostgreSQL)
5. ✅ **Migración simple** de datos existentes
6. ✅ **Seguridad mejorada** para datos sensibles

---

**Última actualización:** 2025-01-27  
**Estado:** ✅ Implementado y listo para uso

