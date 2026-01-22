# 📋 Análisis: Comportamiento al Cambiar Nombres de Arrendatarios y Locales

## 🔍 Estructura Actual del Sistema

### Modelo de Datos

El sistema utiliza **relaciones ForeignKey** para vincular contratos con arrendatarios y locales:

```python
# En gestion/models.py

class Contrato(models.Model):
    # Relaciones (NO campos de texto)
    arrendatario = models.ForeignKey('Tercero', ...)
    proveedor = models.ForeignKey('Tercero', ...)
    local = models.ForeignKey(Local, ...)

class Tercero(models.Model):
    razon_social = models.CharField(max_length=200)  # Nombre almacenado aquí
    
class Local(models.Model):
    nombre_comercial_stand = models.CharField(max_length=100)  # Nombre almacenado aquí
```

**Características importantes:**
- ✅ Los contratos **NO guardan el nombre como texto**
- ✅ Los contratos guardan **solo la referencia** (ForeignKey) al arrendatario/local
- ✅ Los nombres se acceden dinámicamente: `contrato.arrendatario.razon_social`
- ✅ No existe sistema de historial de nombres

---

## ⚠️ Comportamiento Actual: Cambio de Nombres

### Escenario: Usuario cambia el nombre de un Arrendatario o Local

**Ejemplo:**
- Arrendatario: "Empresa ABC S.A.S." → Cambia a → "Empresa XYZ S.A.S."
- Local: "Stand 101" → Cambia a → "Stand 201"

### ¿Qué sucede con los documentos existentes?

#### ✅ **1. Interfaz Web (Vistas HTML)**

**COMPORTAMIENTO:** Todos los contratos muestran el **nuevo nombre inmediatamente**

**Razón:** Los templates acceden directamente a través de la relación:
```django
{{ contrato.arrendatario.razon_social }}
{{ contrato.local.nombre_comercial_stand }}
```

**Ejemplo en templates:**
- `templates/gestion/contratos/detalle.html` (línea 1215)
- `templates/gestion/otrosi/form.html` (línea 595)
- `templates/gestion/contratos/vista_vigente.html`

**Resultado:**
- ✅ Contratos creados ANTES del cambio → Muestran el **nuevo nombre**
- ✅ Contratos creados DESPUÉS del cambio → Muestran el **nuevo nombre**
- ⚠️ **NO hay forma de ver el nombre histórico** en la interfaz web

#### ✅ **2. Documentos Exportados (Excel/PDF)**

**COMPORTAMIENTO:** Los documentos generados **después del cambio** mostrarán el nuevo nombre

**Razón:** Los documentos se generan dinámicamente en tiempo real accediendo a través de la relación:

**Ejemplo en exportaciones:**
```python
# gestion/services/exportes.py (líneas 349-351)
informe.contrato.arrendatario.razon_social,
informe.contrato.arrendatario.nit,
informe.contrato.local.nombre_comercial_stand,

# gestion/services/exportes.py (líneas 560-561)
['Arrendatario:', calculo.contrato.arrendatario.razon_social],
['Local:', calculo.contrato.local.nombre_comercial_stand],
```

**Resultado:**
- ✅ Documentos exportados **ANTES del cambio** → Mantienen el nombre **antiguo** (ya están guardados)
- ✅ Documentos exportados **DESPUÉS del cambio** → Muestran el **nuevo nombre**
- ⚠️ **Los documentos ya guardados NO se actualizan automáticamente**

#### ✅ **3. Base de Datos**

**COMPORTAMIENTO:** Solo se actualiza el registro del Tercero o Local

**Estructura:**
```sql
-- Tabla: gestion_tercero
UPDATE gestion_tercero 
SET razon_social = 'Empresa XYZ S.A.S.' 
WHERE id = 123;

-- Tabla: gestion_local
UPDATE gestion_local 
SET nombre_comercial_stand = 'Stand 201' 
WHERE id = 456;

-- Tabla: gestion_contrato (NO se modifica)
-- Los contratos siguen apuntando al mismo ID:
-- arrendatario_id = 123 (sigue igual)
-- local_id = 456 (sigue igual)
```

**Resultado:**
- ✅ La relación ForeignKey se mantiene (mismo ID)
- ✅ Solo cambia el campo `razon_social` o `nombre_comercial_stand`
- ✅ Todos los contratos vinculados reflejan el cambio automáticamente

---

## 📊 Resumen del Comportamiento

### Tabla Comparativa

| Elemento | Antes del Cambio | Después del Cambio | Documentos Guardados |
|----------|------------------|---------------------|----------------------|
| **Interfaz Web** | Muestra nombre antiguo | ✅ Muestra nombre nuevo | N/A |
| **Exportaciones Nuevas** | N/A | ✅ Muestran nombre nuevo | N/A |
| **Exportaciones Antiguas** | Nombre antiguo guardado | ⚠️ Siguen con nombre antiguo | ✅ Mantienen nombre histórico |
| **Base de Datos** | Nombre antiguo en tabla Tercero/Local | ✅ Nombre nuevo en tabla Tercero/Local | N/A |

---

## ⚠️ Implicaciones Importantes

### ✅ Ventajas del Sistema Actual

1. **Consistencia Automática**
   - Todos los contratos muestran el nombre actualizado automáticamente
   - No requiere actualización manual de cada contrato

2. **Mantenimiento Simplificado**
   - Un solo cambio actualiza todos los contratos relacionados
   - Reduce errores de inconsistencia

3. **Documentos Exportados Antiguos Preservan Historia**
   - Los documentos ya guardados mantienen el nombre que tenían al momento de exportación
   - Útil para auditorías históricas

### ⚠️ Desventajas del Sistema Actual

1. **Pérdida de Historial en Interfaz Web**
   - No se puede ver qué nombre tenía un arrendatario/local cuando se creó un contrato específico
   - Los contratos antiguos muestran el nombre actual, no el histórico

2. **Documentos Nuevos Pierden Contexto Histórico**
   - Si exportas un contrato creado en 2020 después de cambiar el nombre en 2025, mostrará el nombre de 2025
   - Puede ser confuso para análisis históricos

3. **Riesgo de Confusión Legal**
   - En documentos legales, puede ser importante saber el nombre que tenía la empresa en el momento de la firma
   - El sistema actual no preserva esta información

---

## 🔧 Soluciones Recomendadas

### Opción 1: Agregar Campos de Historial (Recomendado para Producción)

**Implementación:**
Agregar campos de texto en el modelo `Contrato` que guarden el nombre al momento de creación:

```python
class Contrato(models.Model):
    # Campos existentes...
    arrendatario = models.ForeignKey('Tercero', ...)
    local = models.ForeignKey(Local, ...)
    
    # NUEVOS CAMPOS DE HISTORIAL
    razon_social_historica = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name='Razón Social al Momento de Creación'
    )
    nombre_local_historico = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Nombre Local al Momento de Creación'
    )
```

**Ventajas:**
- ✅ Preserva el nombre histórico
- ✅ Permite mostrar nombre histórico o actual según necesidad
- ✅ Compatible con documentos legales

**Desventajas:**
- ⚠️ Requiere migración de base de datos
- ⚠️ Requiere actualizar lógica de creación de contratos

### Opción 2: Sistema de Auditoría de Cambios

**Implementación:**
Usar un sistema de auditoría (como django-simple-history) para registrar cambios:

```python
from simple_history.models import HistoricalRecords

class Tercero(models.Model):
    razon_social = models.CharField(max_length=200)
    history = HistoricalRecords()  # Registra todos los cambios
```

**Ventajas:**
- ✅ Registra todos los cambios históricos automáticamente
- ✅ Permite ver el nombre que tenía en cualquier fecha
- ✅ No requiere cambios en el modelo Contrato

**Desventajas:**
- ⚠️ Requiere librería adicional
- ⚠️ Consultas más complejas para obtener nombre histórico

### Opción 3: Mantener Sistema Actual (Solo Documentos Exportados)

**Implementación:**
Mantener el sistema actual pero documentar claramente:
- Los documentos exportados preservan el nombre histórico
- La interfaz web siempre muestra el nombre actual
- Para análisis históricos, usar documentos exportados guardados

**Ventajas:**
- ✅ No requiere cambios en el código
- ✅ Los documentos exportados ya preservan historia
- ✅ Implementación inmediata

**Desventajas:**
- ⚠️ No hay historial visible en la interfaz web
- ⚠️ Depende de que los usuarios guarden documentos exportados

---

## 📝 Recomendación Final

### Para Uso Actual (Corto Plazo)

**Mantener el sistema actual** pero:
1. ✅ Documentar claramente el comportamiento
2. ✅ Recomendar exportar documentos importantes antes de cambios de nombre
3. ✅ Guardar documentos exportados como respaldo histórico

### Para Producción (Mediano Plazo)

**Implementar Opción 1 (Campos de Historial):**
1. ✅ Agregar campos `razon_social_historica` y `nombre_local_historico`
2. ✅ Actualizar formularios para guardar estos campos al crear contratos
3. ✅ Modificar templates para mostrar nombre histórico en documentos legales
4. ✅ Mantener nombre actual para vistas generales

**Beneficios:**
- Preserva información histórica legalmente importante
- Permite análisis históricos precisos
- Mantiene flexibilidad para mostrar nombre actual o histórico

---

## 🔍 Verificación del Comportamiento Actual

### Código Relevante

**Modelos:**
- `gestion/models.py` líneas 485-487: Definición de ForeignKeys
- `gestion/models.py` líneas 221, 248: Campos de nombre

**Templates:**
- `templates/gestion/contratos/detalle.html` línea 1215: Acceso a nombre
- `templates/gestion/otrosi/form.html` línea 595: Acceso a nombre

**Exportaciones:**
- `gestion/services/exportes.py` líneas 349-351: Exportación Excel
- `gestion/services/exportes.py` líneas 560-561: Exportación PDF

**Vistas:**
- `gestion/views/contratos.py` línea 925: Exportación de contratos

---

## 📚 Conclusión

**Respuesta directa a la pregunta:**

> "¿Qué pasa si un usuario cambia el nombre? ¿Todos los documentos se actualizan o solo a partir del cambio?"

**Respuesta:**

1. **Interfaz Web:** ✅ **TODOS los contratos** (antiguos y nuevos) muestran el **nuevo nombre inmediatamente**

2. **Documentos Exportados:**
   - ✅ Documentos **ya guardados** → Mantienen el nombre **antiguo** (preservan historia)
   - ✅ Documentos **generados después** → Muestran el **nuevo nombre**

3. **Base de Datos:** Solo se actualiza el registro del Tercero/Local, todos los contratos vinculados reflejan el cambio automáticamente

**Recomendación:** Para preservar información histórica legalmente importante, considerar implementar campos de historial en el modelo `Contrato` que guarden el nombre al momento de creación.

---

**Última actualización:** Enero 2025  
**Archivos analizados:** `gestion/models.py`, `gestion/services/exportes.py`, `templates/gestion/contratos/`, `gestion/views/contratos.py`
