# Análisis de Código Duplicado y No Utilizado

## Resumen Ejecutivo

Este documento identifica código duplicado, redundante y no utilizado en el proyecto de gestión de contratos. El análisis se realizó mediante búsqueda de referencias cruzadas para asegurar que ningún código en uso sea eliminado incorrectamente.

## Archivos Más Robustos (por complejidad)

1. **`gestion/views.py`** - ~2,400+ líneas
   - Contiene 30+ funciones de vista
   - Lógica compleja de gestión de contratos y pólizas
   - Múltiples exportaciones Excel

2. **`gestion/models.py`** - ~1,144 líneas
   - 9 modelos principales
   - Lógica de negocio en métodos de modelos
   - Modelo `Poliza` marcado como DEPRECATED pero aún en uso

3. **`gestion/forms_otrosi.py`** - ~923 líneas
   - Formulario complejo con validaciones extensas
   - Manejo de múltiples tipos de pólizas

4. **`gestion/utils_otrosi.py`** - ~657 líneas
   - Funciones de utilidad para Otrosí
   - Lógica de efecto cadena y vigencias

5. **`gestion/forms.py`** - ~490 líneas
   - Múltiples formularios
   - Validaciones duplicadas

---

## 1. Código Duplicado Identificado

### 1.1. Funciones de Limpieza de Datos Numéricos

**Ubicación:** `gestion/forms.py` y `gestion/forms_otrosi.py`

**Problema:** Las funciones `limpiar_valor_numerico()` y `_limpiar_datos_post()` están duplicadas con lógica casi idéntica.

**Código Duplicado:**

```python
# En forms.py (líneas 124-158 y 160-189)
def _limpiar_datos_post(self, data):
    """Limpia los datos POST antes de la validación"""
    campos_numericos = [...]
    for campo in campos_numericos:
        if campo in data and data[campo]:
            valor = data[campo]
            if isinstance(valor, str):
                valor = valor.strip()
                if valor.endswith('%'):
                    valor = valor[:-1]
                valor = valor.replace('.', '')
                valor = valor.replace(',', '')
                data[campo] = valor

def limpiar_valor_numerico(self, value, campo_nombre="campo"):
    """Función universal para limpiar valores numéricos con formateo"""
    # Lógica similar...
```

```python
# En forms_otrosi.py (líneas 629-672 y 674-710)
def _limpiar_datos_post(self, data):
    """Limpia los datos POST antes de la validación (igual que ContratoForm)"""
    # Código idéntico...

def limpiar_valor_numerico(self, value):
    """Función para limpiar valores numéricos con formateo"""
    # Lógica similar pero sin parámetro campo_nombre...
```

**Solución Propuesta:**
- Crear módulo `gestion/utils_formateo.py` con funciones reutilizables
- Mover `limpiar_valor_numerico()` y `_limpiar_datos_post()` como funciones de utilidad
- Importar en ambos formularios

**Impacto:** Reducción de ~100 líneas duplicadas

---

### 1.2. Métodos Duplicados en Modelos Poliza y PolizaAportada

**Ubicación:** `gestion/models.py`

**Problema:** Los modelos `Poliza` (DEPRECATED) y `PolizaAportada` tienen métodos idénticos:

- `obtener_estado_vigencia()` (líneas 447-453 y 646-652)
- `obtener_dias_para_vencer()` (líneas 455-459 y 654-658)
- `obtener_estado_legible()` (líneas 461-471 y 660-670)

**Código Duplicado:**

```python
# PolizaAportada (líneas 447-471)
def obtener_estado_vigencia(self):
    from datetime import date
    if self.fecha_vencimiento < date.today():
        return 'Vencida'
    else:
        return 'Vigente'

def obtener_dias_para_vencer(self):
    from datetime import date
    diferencia = (self.fecha_vencimiento - date.today()).days
    return diferencia

def obtener_estado_legible(self):
    dias = self.obtener_dias_para_vencer()
    if dias < 0:
        return f'Vencida hace {abs(dias)} días'
    elif dias == 0:
        return 'Vence hoy'
    elif dias <= 30:
        return f'Vigente - Vence en {dias} días'
    else:
        return f'Vigente - Vence en {dias} días'
```

```python
# Poliza (DEPRECATED) - Código idéntico (líneas 646-670)
```

**Solución Propuesta:**
- Crear clase base abstracta `PolizaBase` con estos métodos
- Hacer que ambos modelos hereden de ella
- O mover métodos a mixin compartido

**Impacto:** Reducción de ~50 líneas duplicadas

---

### 1.3. Importaciones Duplicadas de `datetime`

**Ubicación:** Múltiples archivos

**Problema:** Importaciones redundantes de `datetime` dentro de funciones cuando ya están al inicio del archivo.

**Ejemplos:**

```python
# gestion/models.py
# Línea 449, 457, 648, 656, 677: from datetime import date (dentro de métodos)
# Ya existe importación al inicio del archivo

# gestion/views.py
# Líneas 184, 818, 1498, 1607, 1945, 1995, 2124, 2308, 2402, 2410
# Importaciones locales cuando ya existe: from datetime import date, timedelta
```

**Solución Propuesta:**
- Eliminar importaciones locales redundantes
- Usar las importaciones del nivel de módulo

**Impacto:** Reducción de ~15 líneas redundantes

---

### 1.4. Patrón Repetitivo en `_construir_requisitos_poliza()`

**Ubicación:** `gestion/views.py` (líneas 177-298)

**Problema:** Código repetitivo para mapear cada tipo de póliza:

```python
if 'RCE - Responsabilidad Civil' in polizas_requeridas:
    pol_rce = polizas_requeridas['RCE - Responsabilidad Civil']
    requisitos['rce'] = {
        'exigida': True,
        'valor': pol_rce.get('valor_requerido'),
        'vigencia': pol_rce.get('meses_vigencia'),
        'fecha_fin': pol_rce.get('fecha_fin_requerida'),
        'fuente': fuente,
        'detalles': pol_rce.get('detalles', {})
    }
# Se repite 5 veces para diferentes tipos
```

**Solución Propuesta:**
- Crear función auxiliar `_mapear_poliza_requerida()` que reciba tipo y clave
- Usar diccionario de mapeo para iterar

**Impacto:** Reducción de ~80 líneas repetitivas

---

## 2. Código No Utilizado o Obsoleto

### 2.1. Modelo `Poliza` (DEPRECATED)

**Ubicación:** `gestion/models.py` (líneas 496-820)

**Estado:** Marcado como DEPRECATED pero aún en uso activo

**Referencias Encontradas:**
- `gestion/views.py`: Líneas 370, 1853 (uso de `Poliza.objects`)
- `gestion/services/alertas.py`: Línea 182 (`Poliza.objects.filter`)
- `gestion/utils_otrosi.py`: Línea 372 (`Poliza.objects.filter`)
- `gestion/forms.py`: Línea 416 (`Poliza.objects.filter`)
- `gestion/admin.py`: Línea 9 (`admin.site.register(Poliza)`)

**Análisis:**
- El modelo está marcado como DEPRECATED pero sigue siendo usado en múltiples lugares
- Existe `PolizaAportada` que parece ser el reemplazo, pero no se ha completado la migración

**Recomendación:**
- **NO ELIMINAR** hasta completar migración a `PolizaAportada`
- Crear plan de migración para reemplazar todas las referencias
- Documentar dependencias antes de eliminar

---

### 2.2. Formulario `ContratoConPolizasForm`

**Ubicación:** `gestion/forms.py` (líneas 277-305)

**Estado:** Definido pero no utilizado

**Referencias Encontradas:**
- Solo importado en `gestion/views.py` línea 14 pero nunca usado
- No hay vistas que lo utilicen

**Recomendación:**
- **ELIMINAR** si no hay planes de uso futuro
- Verificar que no se use en templates o JavaScript

**Impacto:** Reducción de ~30 líneas no utilizadas

---

### 2.3. Función `get_polizas_vigentes()`

**Ubicación:** `gestion/utils_otrosi.py` (líneas 354-385)

**Estado:** Definida pero posiblemente no utilizada

**Referencias Encontradas:**
- Solo importada en `gestion/views.py` línea 47 pero no se encontró uso real

**Recomendación:**
- Verificar uso en templates o código JavaScript
- Si no se usa, considerar eliminación o documentar propósito

---

### 2.4. Función `formatear_fecha_espanol()`

**Ubicación:** `gestion/utils.py` (líneas 40-55)

**Estado:** Definida pero no utilizada

**Referencias Encontradas:**
- No se encontraron referencias en el código

**Recomendación:**
- **ELIMINAR** si no se usa en templates
- Verificar uso en templates antes de eliminar

**Impacto:** Reducción de ~15 líneas no utilizadas

---

### 2.5. Función `calcular_meses_vigencia()`

**Ubicación:** `gestion/utils.py` (líneas 25-37)

**Estado:** Definida pero uso limitado

**Referencias Encontradas:**
- Solo usada en `gestion/views.py` línea 132 dentro de `_aplicar_polizas_vigentes_a_requisitos()`

**Recomendación:**
- Mantener si se usa, pero considerar si la lógica es correcta (usa estándar de 30 días por mes)

---

## 3. Código Redundante

### 3.1. Constantes TIPO_CHOICES Duplicadas

**Ubicación:** `gestion/models.py`

**Problema:** `TIPO_CHOICES` definido en múltiples modelos:
- `RequerimientoPoliza.TIPO_CHOICES` (línea 275)
- `PolizaAportada.TIPO_CHOICES` (línea 301)
- `Poliza.TIPO_CHOICES` (línea 499)
- `SeguimientoPoliza.TIPO_SEGUIMIENTO_CHOICES` (línea 853) - referencia a `Poliza.TIPO_CHOICES`

**Solución Propuesta:**
- Crear constante global en `gestion/models.py` al inicio del archivo
- Reutilizar en todos los modelos

**Impacto:** Mejora de mantenibilidad

---

### 3.2. Lógica de Validación de Pólizas Duplicada

**Ubicación:** `gestion/models.py`

**Problema:** `cumple_requisitos_contrato()` tiene lógica muy similar pero diferente entre `Poliza` y `PolizaAportada`:
- `PolizaAportada.cumple_requisitos_contrato()` (líneas 473-493) - más simple
- `Poliza.cumple_requisitos_contrato()` (líneas 672-820) - más compleja, considera Otrosí

**Análisis:**
- La versión de `Poliza` es más completa y considera Otrosí vigentes
- La versión de `PolizaAportada` es más simple

**Recomendación:**
- Unificar lógica si ambos modelos deben comportarse igual
- O documentar por qué son diferentes

---

## 4. Mejoras de Estructura

### 4.1. `views.py` Demasiado Grande

**Problema:** `views.py` tiene ~2,400 líneas con 30+ funciones

**Recomendación:**
- Dividir en módulos por funcionalidad:
  - `views/contratos.py` - CRUD de contratos
  - `views/polizas.py` - Gestión de pólizas
  - `views/otrosi.py` - Gestión de Otrosí
  - `views/exportaciones.py` - Exportaciones Excel
  - `views/dashboard.py` - Dashboard y alertas

**Impacto:** Mejora significativa de mantenibilidad

---

### 4.2. Validaciones de Formularios Repetitivas

**Problema:** Múltiples métodos `clean_*()` con lógica similar en `forms_otrosi.py`

**Ejemplo:** Líneas 712-820 tienen ~20 métodos `clean_*()` que llaman a `_clean_campo_monetario()`

**Recomendación:**
- Usar `__getattr__` para generar métodos `clean_*()` dinámicamente
- O usar decorador/metaclase para simplificar

---

## 5. Resumen de Acciones Recomendadas

### Acciones Inmediatas (Sin Riesgo)

1. ✅ **Eliminar `ContratoConPolizasForm`** - No utilizado
2. ✅ **Eliminar `formatear_fecha_espanol()`** - No utilizado (verificar templates primero)
3. ✅ **Consolidar funciones de limpieza numérica** - Crear módulo compartido
4. ✅ **Eliminar importaciones redundantes de datetime** - Usar nivel de módulo

**Reducción estimada:** ~150 líneas

### Acciones a Mediano Plazo (Requieren Planificación)

1. ⚠️ **Migrar de `Poliza` a `PolizaAportada`** - Requiere plan de migración
2. ⚠️ **Unificar métodos duplicados en modelos** - Crear clase base o mixin
3. ⚠️ **Refactorizar `_construir_requisitos_poliza()`** - Reducir repetición
4. ⚠️ **Dividir `views.py`** - Mejorar estructura

### Acciones de Mejora (Opcionales)

1. 📝 **Consolidar constantes TIPO_CHOICES** - Mejorar mantenibilidad
2. 📝 **Simplificar métodos clean_*()** - Usar metaprogramación
3. 📝 **Documentar diferencias entre Poliza y PolizaAportada** - Clarificar propósito

---

## 6. Verificación de Seguridad

### Código que NO debe eliminarse:

- ✅ `Poliza` model - Aún en uso activo (marcado DEPRECATED pero necesario)
- ✅ `get_polizas_vigentes()` - Verificar uso en templates antes de eliminar
- ✅ Cualquier función referenciada en URLs o templates

### Verificaciones Realizadas:

- ✅ Búsqueda de referencias cruzadas con `grep`
- ✅ Verificación de imports en todos los módulos
- ✅ Análisis de uso en vistas y formularios
- ✅ Verificación de modelos en admin.py

---

## Conclusión

El proyecto tiene código duplicado significativo que puede consolidarse sin afectar funcionalidad. Las acciones inmediatas pueden reducir ~150 líneas de código sin riesgo. Las acciones a mediano plazo requieren planificación cuidadosa, especialmente la migración del modelo `Poliza` DEPRECATED.

**Prioridad:** 
1. ✅ Consolidar funciones de limpieza numérica - **COMPLETADO**
2. ✅ Eliminar código no utilizado verificado - **COMPLETADO**
3. ✅ Crear mixin para métodos comunes de pólizas - **COMPLETADO**
4. ✅ Consolidar constantes TIPO_CHOICES - **COMPLETADO**
5. ✅ Refactorizar _construir_requisitos_poliza() - **COMPLETADO**
6. ⚠️ Planificar migración de Poliza a PolizaAportada - **PENDIENTE**
7. ⚠️ Refactorizar estructura de views.py - **PENDIENTE**

---

## Mejoras Implementadas (Fase 2)

### 1. Creación de PolizaMixin

**Ubicación:** `gestion/models.py` (líneas 51-79)

**Mejora:** Se creó un mixin `PolizaMixin` con los métodos comunes:
- `obtener_estado_vigencia()`
- `obtener_dias_para_vencer()`
- `obtener_estado_legible()`

**Resultado:** 
- `PolizaAportada` y `Poliza` ahora heredan de `PolizaMixin`
- Eliminadas ~50 líneas de código duplicado
- Eliminadas importaciones redundantes de `datetime` dentro de métodos

### 2. Consolidación de Constantes

**Ubicación:** `gestion/models.py` (líneas 35-48)

**Mejora:** Se crearon constantes globales:
- `POLIZA_TIPO_CHOICES` - Reemplaza TIPO_CHOICES duplicados en 3 modelos
- `POLIZA_ESTADO_CHOICES` - Reemplaza ESTADO_CHOICES duplicados en 2 modelos

**Resultado:**
- Eliminadas 3 definiciones duplicadas de TIPO_CHOICES
- Eliminadas 2 definiciones duplicadas de ESTADO_CHOICES
- Mejora significativa en mantenibilidad

### 3. Refactorización de _construir_requisitos_poliza()

**Ubicación:** `gestion/views.py` (líneas 240-264)

**Mejora:** Se reemplazó código repetitivo (5 bloques if similares) con un diccionario de mapeo y un bucle.

**Resultado:**
- Reducción de ~60 líneas repetitivas a ~25 líneas con lógica clara
- Código más mantenible y fácil de extender

### Estadísticas Totales de Mejoras

**Fase 1 (Completada anteriormente):**
- Líneas eliminadas: ~145 líneas
- Archivos modificados: 5
- Archivos creados: 2

**Fase 2 (Completada ahora):**
- Líneas eliminadas: ~110 líneas adicionales
- Métodos consolidados: 3 métodos comunes
- Constantes consolidadas: 5 constantes duplicadas
- Patrones repetitivos eliminados: 1 función refactorizada

**Total General:**
- **Líneas eliminadas:** ~255 líneas
- **Archivos modificados:** 6
- **Archivos creados:** 3
- **Código duplicado restante:** ~50 líneas (principalmente en `cumple_requisitos_contrato()` que tiene lógica diferente entre modelos)

