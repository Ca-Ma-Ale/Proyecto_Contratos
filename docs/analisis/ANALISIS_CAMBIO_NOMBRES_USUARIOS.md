# 📋 Análisis: Comportamiento al Cambiar Nombres de Usuarios del Sistema

## 🔍 Estructura Actual del Sistema

### Modelo de Auditoría

El sistema utiliza **campos de texto (CharField)** para almacenar los nombres de usuarios en los campos de auditoría:

```python
# En gestion/models.py - AuditoriaMixin

class AuditoriaMixin(models.Model):
    creado_por = models.CharField(max_length=150, ...)      # Campo de TEXTO
    modificado_por = models.CharField(max_length=150, ...) # Campo de TEXTO
    eliminado_por = models.CharField(max_length=150, ...)  # Campo de TEXTO
```

**Características importantes:**
- ✅ Los nombres se guardan como **texto** (no como ForeignKey)
- ✅ Se almacena el valor al momento de crear/modificar/eliminar
- ✅ El valor guardado **NO se actualiza automáticamente** si el usuario cambia su nombre

### Cómo se Guarda el Nombre del Usuario

```python
# En gestion/utils_auditoria.py (líneas 16, 37, 54)

def registrar_creacion(instancia, usuario):
    if usuario and usuario.is_authenticated:
        nombre_usuario = usuario.get_full_name() or usuario.username
        instancia.creado_por = nombre_usuario  # Se guarda como TEXTO
        
def registrar_modificacion(instancia, usuario):
    nombre_usuario = usuario.get_full_name() or usuario.username
    instancia.modificado_por = nombre_usuario  # Se guarda como TEXTO
```

**Lógica de guardado:**
1. Primero intenta usar `usuario.get_full_name()` (retorna `first_name + " " + last_name`)
2. Si no hay nombre completo, usa `usuario.username`
3. El valor se guarda como texto en la base de datos

---

## ⚠️ Comportamiento Actual: Cambio de Nombres de Usuarios

### Escenario: Usuario cambia su nombre de usuario o nombre completo

**Ejemplo:**
- Usuario: `Carlos_Gomez` → Cambia a → `Carlos_Rodriguez`
- O cambia: `first_name="Carlos"` + `last_name="Gomez"` → `first_name="Carlos"` + `last_name="Rodriguez"`

### ¿Qué sucede con los registros existentes?

#### ✅ **1. Registros Antiguos (Creados ANTES del cambio)**

**COMPORTAMIENTO:** Mantienen el **nombre antiguo** guardado como texto

**Ejemplo:**
```sql
-- Antes del cambio
gestion_contrato:
  id | num_contrato | creado_por      | modificado_por
  1  | CON-2024-001 | Carlos_Gomez    | Carlos_Gomez
  2  | CON-2024-002 | Carlos_Gomez    | Maria_Lopez

-- Usuario cambia su username a "Carlos_Rodriguez"

-- Después del cambio (los registros NO cambian)
gestion_contrato:
  id | num_contrato | creado_por      | modificado_por
  1  | CON-2024-001 | Carlos_Gomez    | Carlos_Gomez    ← MANTIENE nombre antiguo
  2  | CON-2024-002 | Carlos_Gomez    | Maria_Lopez     ← MANTIENE nombre antiguo
```

**Resultado:**
- ✅ Los registros creados ANTES del cambio → Muestran el **nombre antiguo**
- ✅ Se preserva el historial de quién hizo qué acción
- ✅ Útil para auditorías y trazabilidad

#### ✅ **2. Registros Nuevos (Creados DESPUÉS del cambio)**

**COMPORTAMIENTO:** Muestran el **nuevo nombre** del usuario

**Ejemplo:**
```sql
-- Usuario ya cambió su nombre a "Carlos_Rodriguez"

-- Nuevo registro creado después del cambio
gestion_contrato:
  id | num_contrato | creado_por         | modificado_por
  3  | CON-2024-003 | Carlos_Rodriguez   | Carlos_Rodriguez  ← Muestra nombre nuevo
```

**Resultado:**
- ✅ Los registros creados DESPUÉS del cambio → Muestran el **nuevo nombre**
- ✅ Refleja el nombre actual del usuario

---

## 📊 Resumen del Comportamiento

### Tabla Comparativa

| Tipo de Registro | Antes del Cambio | Después del Cambio | Comportamiento |
|------------------|------------------|---------------------|----------------|
| **Registros Antiguos** | Nombre antiguo guardado | ✅ Mantienen nombre antiguo | Preserva historial |
| **Registros Nuevos** | N/A | ✅ Muestran nombre nuevo | Refleja cambio |
| **Interfaz Web** | Muestra nombre guardado | ✅ Muestra nombre guardado (antiguo o nuevo según fecha) | Depende de cuándo se creó |

---

## 🔍 Ejemplos Prácticos

### Ejemplo 1: Cambio de Username

**Situación:**
- Usuario: `Carlos_Gomez` crea un contrato el 15 de enero de 2024
- El 20 de febrero de 2024, el usuario cambia su username a `Carlos_Rodriguez`
- El 25 de febrero de 2024, el mismo usuario crea otro contrato

**Resultado:**

```python
# Contrato creado el 15 de enero (ANTES del cambio)
contrato_1 = Contrato.objects.get(num_contrato='CON-2024-001')
print(contrato_1.creado_por)  # Output: "Carlos_Gomez" ← Nombre antiguo

# Contrato creado el 25 de febrero (DESPUÉS del cambio)
contrato_2 = Contrato.objects.get(num_contrato='CON-2024-002')
print(contrato_2.creado_por)  # Output: "Carlos_Rodriguez" ← Nombre nuevo
```

### Ejemplo 2: Cambio de Nombre Completo

**Situación:**
- Usuario tiene: `first_name="Carlos"`, `last_name="Gomez"`, `username="carlos_g"`
- Crea un contrato → Se guarda: `creado_por = "Carlos Gomez"`
- Luego cambia: `last_name="Rodriguez"` → Ahora `get_full_name()` retorna `"Carlos Rodriguez"`
- Crea otro contrato → Se guarda: `creado_por = "Carlos Rodriguez"`

**Resultado:**

```python
# Contrato creado ANTES del cambio de apellido
contrato_1.creado_por  # "Carlos Gomez" ← Nombre antiguo preservado

# Contrato creado DESPUÉS del cambio de apellido
contrato_2.creado_por  # "Carlos Rodriguez" ← Nombre nuevo
```

### Ejemplo 3: Modificación de Registros Existentes

**Situación:**
- Contrato creado por `Carlos_Gomez` el 15 de enero
- El 20 de febrero, `Carlos_Gomez` cambia su username a `Carlos_Rodriguez`
- El 25 de febrero, el mismo usuario modifica el contrato creado el 15 de enero

**Resultado:**

```python
contrato = Contrato.objects.get(num_contrato='CON-2024-001')
print(contrato.creado_por)      # "Carlos_Gomez" ← Nombre antiguo (no cambia)
print(contrato.modificado_por) # "Carlos_Rodriguez" ← Nombre nuevo (actualizado en modificación)
```

---

## ✅ Ventajas del Sistema Actual

### 1. **Preservación de Historial**
- Los registros antiguos mantienen el nombre que tenía el usuario cuando realizó la acción
- Útil para auditorías y cumplimiento legal
- Permite rastrear cambios históricos

### 2. **Trazabilidad Completa**
- Se puede saber exactamente qué usuario (con su nombre de ese momento) hizo cada acción
- Importante para investigaciones y análisis de responsabilidades

### 3. **Flexibilidad**
- Los usuarios pueden cambiar sus nombres sin afectar registros históricos
- Los nuevos registros reflejan el nombre actual

---

## ⚠️ Consideraciones Importantes

### 1. **Búsquedas por Nombre de Usuario**

Si buscas registros creados por un usuario que cambió su nombre, necesitas buscar por **ambos nombres**:

```python
# Buscar registros creados por Carlos (tanto con nombre antiguo como nuevo)
contratos_antiguos = Contrato.objects.filter(creado_por='Carlos_Gomez')
contratos_nuevos = Contrato.objects.filter(creado_por='Carlos_Rodriguez')
todos_los_contratos = contratos_antiguos | contratos_nuevos
```

### 2. **Reportes y Exportaciones**

Los reportes mostrarán el nombre que tenía el usuario **al momento de crear/modificar** cada registro:

```python
# Exportación Excel mostrará:
# - Registros antiguos: "Carlos_Gomez"
# - Registros nuevos: "Carlos_Rodriguez"
```

### 3. **Identificación de Usuario Actual**

Para identificar al usuario actual en el sistema, siempre usar:
- `request.user.username` → Siempre muestra el username actual
- `request.user.get_full_name()` → Siempre muestra el nombre completo actual

**NO usar** los campos de auditoría para identificar usuarios actuales, ya que pueden tener nombres antiguos.

---

## 🔧 Cómo Cambiar el Nombre de un Usuario

### Opción 1: Desde Django Admin

1. Ir a `/admin/auth/user/`
2. Seleccionar el usuario
3. Cambiar:
   - `username` → Nuevo username
   - `first_name` → Nuevo nombre
   - `last_name` → Nuevo apellido
4. Guardar

### Opción 2: Desde Django Shell

```python
python manage.py shell

from django.contrib.auth.models import User

# Cambiar username
usuario = User.objects.get(username='Carlos_Gomez')
usuario.username = 'Carlos_Rodriguez'
usuario.save()

# Cambiar nombre completo
usuario.first_name = 'Carlos'
usuario.last_name = 'Rodriguez'
usuario.save()
```

### Opción 3: Desde Código (Vista Personalizada)

```python
from django.contrib.auth.models import User

def cambiar_nombre_usuario(request, user_id):
    usuario = User.objects.get(id=user_id)
    usuario.username = request.POST.get('nuevo_username')
    usuario.first_name = request.POST.get('nuevo_first_name')
    usuario.last_name = request.POST.get('nuevo_last_name')
    usuario.save()
    # Los registros antiguos NO se actualizan automáticamente
```

---

## 📝 Recomendaciones

### ✅ Buenas Prácticas

1. **Documentar Cambios de Nombre**
   - Mantener registro de cuándo y por qué cambió un nombre de usuario
   - Útil para auditorías futuras

2. **Usar Username para Identificación**
   - Para identificar usuarios actuales, usar `username` (único e inmutable en la práctica)
   - Los campos de auditoría son para historial, no para identificación actual

3. **Búsquedas Históricas**
   - Al buscar registros de un usuario, considerar buscar por todos los nombres que haya tenido

### ⚠️ Consideraciones Especiales

1. **No Actualizar Registros Antiguos**
   - **NO** actualizar manualmente los campos `creado_por`/`modificado_por` en registros antiguos
   - Esto destruiría el historial de auditoría

2. **Reportes Históricos**
   - Los reportes mostrarán nombres históricos, lo cual es correcto
   - Si necesitas el nombre actual, hacer join con la tabla `auth_user`

3. **Migraciones de Usuarios**
   - Si un usuario se va y otro toma su lugar, crear un nuevo usuario en lugar de cambiar el username
   - Esto preserva mejor el historial

---

## 🔍 Verificación del Comportamiento

### Código Relevante

**Modelos:**
- `gestion/models.py` líneas 15-51: Definición de campos de auditoría (CharField)

**Utilidades:**
- `gestion/utils_auditoria.py` líneas 7-80: Funciones de registro de auditoría
- Línea 16: `nombre_usuario = usuario.get_full_name() or usuario.username`

**Vistas:**
- `gestion/views/contratos.py` línea 51: Uso de `guardar_con_auditoria()`
- `gestion/views/terceros.py` línea 34: Uso de `guardar_con_auditoria()`

---

## 📚 Conclusión

**Respuesta directa a la pregunta:**

> "¿Qué pasa si un usuario admin del sistema que hoy se llama Carlos_Gomez después se cambie el nombre?"

**Respuesta:**

1. **Registros Antiguos:** ✅ Mantienen el nombre **"Carlos_Gomez"** (preservan historial)

2. **Registros Nuevos:** ✅ Muestran el **nuevo nombre** (ej: "Carlos_Rodriguez")

3. **Comportamiento:**
   - Los campos de auditoría (`creado_por`, `modificado_por`, `eliminado_por`) guardan el nombre como **texto**
   - El texto guardado **NO se actualiza automáticamente** cuando el usuario cambia su nombre
   - Esto preserva el historial de auditoría correctamente

**Ejemplo práctico:**
- Contrato creado el 15/01/2024 por `Carlos_Gomez` → `creado_por = "Carlos_Gomez"`
- Usuario cambia su nombre a `Carlos_Rodriguez` el 20/02/2024
- Contrato creado el 25/02/2024 por el mismo usuario → `creado_por = "Carlos_Rodriguez"`
- El contrato del 15/01 sigue mostrando `creado_por = "Carlos_Gomez"` (historial preservado)

**Ventaja:** El sistema preserva correctamente el historial de auditoría, permitiendo saber exactamente qué usuario (con su nombre de ese momento) realizó cada acción.

---

**Última actualización:** Enero 2025  
**Archivos analizados:** `gestion/models.py`, `gestion/utils_auditoria.py`, `gestion/views/`
