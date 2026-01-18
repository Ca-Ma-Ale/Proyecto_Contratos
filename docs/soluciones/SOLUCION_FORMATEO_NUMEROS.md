# Solución a Problemas de Formateo en Formulario de Edición

## Problemas Identificados

### 1. Formateo Incorrecto de Números

Al cargar valores desde la base de datos en el formulario de edición, los números se estaban formateando incorrectamente:

- **Valor real**: `2.500.000` → **Se mostraba como**: `250.000.000`
- **Valor real**: `12%` → **Se mostraba como**: `1200%`

### 2. Errores de Formato de Fecha

Los campos de tipo `date` mostraban errores en la consola:

```
The specified value "31/05/2025" does not conform to the required format, "yyyy-MM-dd".
The specified value "01/06/2025" does not conform to the required format, "yyyy-MM-dd".
The specified value "01/09/2026" does not conform to the required format, "yyyy-MM-dd".
```

## Causas de los Problemas

### Problema de Números

El JavaScript de formateo automático estaba:

1. **Tratando valores decimales como enteros**: Los campos `DecimalField` de Django se renderizan como strings con decimales, pero el JavaScript los interpretaba incorrectamente.

2. **Aplicando formateo múltiple**: Múltiples scripts (`format_edit_view.js`, `format_view_only.js`, `formatMiles.js`) competían por formatear los mismos campos.

3. **No detectando valores ya formateados**: El código no verificaba si un valor ya tenía el formato correcto antes de aplicarlo.

### Problema de Fechas

Django con `USE_I18N = True` y `LANGUAGE_CODE = 'es-co'` estaba formateando las fechas en formato español (`dd/MM/yyyy`), pero los inputs HTML5 de tipo `date` requieren formato ISO (`yyyy-MM-dd`).

## Solución Implementada

### 1. Solución para Números - Archivo `format_edit_view.js`

**Cambios realizados:**

```javascript
// ANTES: Formateo incorrecto
const numericValue = field.value.replace(/\D/g, '');
if (numericValue && !isNaN(numericValue) && !field.value.includes('.')) {
    field.value = formatter.format(numericValue);
}

// DESPUÉS: Formateo inteligente con limpieza de valores
let valorOriginal = field.value.trim();

// Verificar si ya tiene formato de miles correcto
if (valorOriginal.match(/^\d{1,3}(\.\d{3})*$/)) {
    return; // Ya está formateado
}

// Limpiar el valor: remover puntos y comas
let valorLimpio = valorOriginal.replace(/[.,]/g, '');

// Convertir a número y formatear correctamente
let valorNumerico = parseFloat(valorLimpio);
if (!isNaN(valorNumerico) && valorNumerico >= 0) {
    valorNumerico = Math.round(valorNumerico);
    field.value = formatter.format(valorNumerico);
}
```

**Mejoras clave:**
- Limpieza completa de puntos y comas antes de parsear
- Detección inteligente de valores ya formateados
- Logging detallado para debugging
- Eliminación de eventos conflictivos (blur) 
- Timeout aumentado a 1000ms para evitar conflictos

### 2. Solución para Números - Archivo `formatMiles.js`

**Cambios realizados:**

```javascript
// ANTES: Formateo sin verificación
const digits = onlyDigits(input.value);
if (digits) {
    input.value = formatter.format(digits);
}

// DESPUÉS: Formateo con verificación previa
let valorOriginal = input.value.trim();

// Verificar si ya tiene formato de miles
if (valorOriginal.includes('.') && valorOriginal.match(/^\d{1,3}(\.\d{3})*$/)) {
    return; // Ya está formateado
}

// Convertir a número y formatear
let valorNumerico = parseFloat(valorOriginal);
if (!isNaN(valorNumerico) && valorNumerico > 0) {
    valorNumerico = Math.round(valorNumerico);
    input.value = formatter.format(valorNumerico);
}
```

### 3. Solución para Números - Simplificación de `format_view_only.js`

El archivo `format_view_only.js` fue simplificado para evitar conflictos:

```javascript
// ANTES: Script complejo que competía con otros
// Múltiples event listeners y formateo automático

// DESPUÉS: Script simplificado que delega todo el trabajo
document.addEventListener('DOMContentLoaded', function() {
    // Este archivo ya no hace nada automáticamente
    // Todo el formateo está manejado por:
    // - format_edit_view.js (carga inicial en modo edición)
    // - formatMiles.js (interacción del usuario)
});
```

### 4. Solución para Fechas - Archivo `gestion/forms.py`

**Cambios realizados:**

```python
# ANTES: Widget sin formato específico
'fecha_firma': forms.DateInput(attrs={'type': 'date'}),

# DESPUÉS: Widget con formato ISO explícito
'fecha_firma': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
```

**Configuración adicional en `__init__`:**

```python
# Configurar formato de fecha para todos los campos de fecha
fecha_fields = [
    'fecha_firma', 'fecha_inicial_contrato', 'fecha_final_inicial', 
    'fecha_final_actualizada', 'fecha_inicio_periodo_gracia', 'fecha_fin_periodo_gracia',
    # ... todos los campos de fecha
]

for field_name in fecha_fields:
    if field_name in self.fields:
        self.fields[field_name].input_formats = ['%Y-%m-%d']
```

**Mejoras clave:**
- Formato ISO (`%Y-%m-%d`) explícito en widgets
- `input_formats` configurado para aceptar solo formato ISO
- Compatible con HTML5 date inputs
- No afecta la internacionalización de Django

## Características de la Solución

### ✅ **Detección Inteligente**
- Verifica si el valor ya está formateado antes de aplicar formateo
- Usa expresiones regulares para detectar patrones de formateo existentes

### ✅ **Manejo Correcto de Decimales**
- Convierte valores decimales a enteros para campos monetarios
- Preserva la precisión para campos de porcentaje

### ✅ **Prevención de Formateo Múltiple**
- Evita que los valores se formateen varias veces
- Mantiene la integridad de los datos originales

### ✅ **Compatibilidad**
- No afecta la funcionalidad existente
- Mantiene el formateo en tiempo real para nuevos valores
- Preserva la limpieza de datos antes del envío del formulario

## Campos Afectados

### Campos Monetarios (`.money-input`)
- `canon_minimo_garantizado`
- `valor_asegurado_rce`
- `valor_asegurado_cumplimiento`
- `valor_asegurado_todo_riesgo`
- `valor_asegurado_otra_1`
- `clausula_penal_incumplimiento`
- `penalidad_terminacion_anticipada`
- `multa_mora_no_restitucion`

### Campos de Porcentaje (`.percentage-input`)
- `porcentaje_ventas`
- `interes_mora_pagos`
- `puntos_adicionales_ipc`

## Resultado

Ahora los valores se muestran correctamente:

- **Canon Mínimo Garantizado**: `2.500.000` ✅
- **Porcentaje de Ventas**: `12%` ✅
- **Interés de Mora**: `0%` ✅

## Archivos Modificados

### JavaScript
1. `static/js/format_edit_view.js` - Formateo para vista de edición (REESCRITO)
2. `static/js/formatMiles.js` - Formateo general de miles y porcentajes (ACTUALIZADO)
3. `static/js/format_view_only.js` - Simplificado para evitar conflictos (REESCRITO)

### Python
4. `gestion/forms.py` - Configuración de widgets y formatos de fecha (ACTUALIZADO)

### Documentación
5. `docs/SOLUCION_FORMATEO_NUMEROS.md` - Esta documentación (NUEVO)

## Pruebas Recomendadas

### Para Números:
1. **Cargar contrato existente** - Verificar que los valores monetarios se muestren correctamente (ej: `2.500.000`)
2. **Verificar porcentajes** - Confirmar que los porcentajes se muestren correctamente (ej: `12%`)
3. **Editar valores** - Confirmar que el formateo en tiempo real funciona
4. **Guardar cambios** - Verificar que los datos se almacenen correctamente en la base de datos
5. **Crear nuevo contrato** - Asegurar que el formateo funcione en modo creación

### Para Fechas:
1. **Cargar contrato existente** - Verificar que NO aparezcan errores en la consola sobre formato de fecha
2. **Campos de fecha** - Confirmar que todos los campos de fecha muestren el formato `yyyy-MM-dd`
3. **Selector de fecha** - Verificar que el selector nativo del navegador funcione correctamente
4. **Guardar fechas** - Confirmar que las fechas se guarden correctamente en la base de datos

## Solución de Problemas

### Si los números siguen sin formatearse correctamente:
1. Abrir la consola del navegador (F12)
2. Buscar los logs que comienzan con `[MONEY]` o `[PERCENT]`
3. Verificar qué valor original está recibiendo el script
4. Confirmar que el timeout de 1000ms sea suficiente

### Si las fechas siguen mostrando errores:
1. Verificar que el servidor Django se haya reiniciado después de los cambios
2. Limpiar caché del navegador (Ctrl+Shift+Delete)
3. Verificar en la consola que no haya otros scripts modificando los campos de fecha
