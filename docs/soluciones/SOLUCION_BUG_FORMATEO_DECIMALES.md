# Solución Bug: Formateo Incorrecto de Números con Decimales

## Problema Identificado

Al cargar valores desde la base de datos en modo edición, el sistema de formateo multiplicaba incorrectamente los valores por 100.

### Ejemplo del Bug:
- **Valor almacenado en BD**: 2.500.000
- **Valor renderizado por Django**: `2500000.00` (DecimalField con 2 decimales)
- **Valor mostrado en pantalla**: 250.000.000 ❌ (error de multiplicación)

## Causa Raíz

El archivo `format_edit_view.js` tenía el siguiente código:

```javascript
// CÓDIGO CON BUG
let valorLimpio = valorOriginal.replace(/[^\d]/g, '');
```

Cuando el valor venía como `"2500000.00"`:
1. El regex `/[^\d]/g` eliminaba TODOS los caracteres no numéricos, incluyendo el punto decimal
2. Resultado: `"2500000" + "00"` = `"250000000"` (concatenación incorrecta)
3. Se formateaba como 250.000.000

## Solución Implementada

Se modificó la lógica para separar primero la parte entera de la decimal:

```javascript
// CÓDIGO CORREGIDO
// 1. Primero separar por el punto decimal y tomar solo la parte entera
let valorSinDecimales = valorOriginal.split('.')[0];

// 2. Luego limpiar otros caracteres no numéricos
let valorLimpio = valorSinDecimales.replace(/[^\d]/g, '');
```

### Flujo Corregido:
- Entrada: `"2500000.00"`
- Después de `split('.')[0]`: `"2500000"`
- Después de limpiar: `"2500000"`
- Resultado formateado: `"2.500.000"` ✅

## Archivos Modificados

1. **`static/js/format_edit_view.js`** (líneas 44-54)
   - Agregado: Separación de parte decimal antes de limpiar
   - Agregado: Log adicional para depuración

2. **`staticfiles/js/format_edit_view.js`** (líneas 44-54)
   - Misma corrección para mantener coherencia

3. **`static/js/formatMiles.js`** (líneas 34-35)
   - Agregado: Comentario explicativo sobre el manejo de decimales
   - Nota: Este archivo ya usaba `parseFloat` correctamente

4. **`staticfiles/js/formatMiles.js`** (líneas 34-35)
   - Misma documentación para coherencia

## Casos de Uso Cubiertos

La solución ahora maneja correctamente:

✅ Valores con decimales de Django: `"2500000.00"` → `"2.500.000"`
✅ Valores sin decimales: `"2500000"` → `"2.500.000"`
✅ Valores ya formateados: `"2.500.000"` → No se modifica
✅ Valores con separador de coma: `"2,500,000"` → `"2.500.000"`

## Logs de Depuración

El sistema ahora incluye logs detallados en consola:

```
[MONEY] Campo: canon_minimo_garantizado, Valor original: "2500000.00"
[MONEY] Valor sin decimales: "2500000"
[MONEY] Valor limpio: "2500000"
[MONEY] ✅ Formateando canon_minimo_garantizado: "2500000.00" -> "2.500.000"
```

## Verificación

Para verificar que el bug está solucionado:

1. Editar un contrato existente con valores monetarios
2. Abrir la consola del navegador (F12)
3. Verificar que los valores se formatean correctamente
4. Los logs deben mostrar la transformación paso a paso

## Configuración Global

El sistema utiliza la configuración de formateo de Colombia:

```javascript
const formatter = new Intl.NumberFormat('es-CO', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
});
```

Esta configuración se aplica de forma consistente en:
- Modo de creación de contratos
- Modo de edición de contratos  
- Vista de solo lectura de contratos

## Fecha de Corrección

26 de Octubre de 2025

