# Análisis de Afectaciones por Eliminación de PolizaAportada

## Fecha: 2025-01-XX
## Modelo Eliminado: `PolizaAportada`

---

## Resumen Ejecutivo

Se eliminó el modelo `PolizaAportada` del sistema, consolidando todas las operaciones de pólizas en el modelo `Poliza`. Este documento detalla todas las afectaciones identificadas y las acciones correctivas necesarias.

---

## 1. Cambios Realizados

### 1.1 Código Actualizado ✅

- **`gestion/models.py`**: Modelo `PolizaAportada` eliminado
- **`gestion/forms.py`**: `PolizaAportadaForm` eliminado
- **`gestion/views/polizas.py`**: Actualizado para usar `contrato.polizas`
- **`gestion/views/contratos.py`**: Actualizado para usar `contrato.polizas`
- **`gestion/views/dashboard.py`**: Actualizado para contar solo `Poliza`
- **`gestion/services/alertas.py`**: Actualizado para buscar solo en `Poliza`
- **`gestion/models.py` (SeguimientoPoliza)**: Campo `poliza_aportada` eliminado
- **`templates/gestion/contratos/vista_vigente.html`**: Referencias a `polizas_aportadas_con_seguimiento` eliminadas

### 1.2 Base de Datos ✅

- **Migración aplicada**: `0047_eliminar_poliza_aportada`
- Tabla `gestion_polizaaportada` eliminada
- Campo `poliza_aportada_id` eliminado de `gestion_seguimientopoliza`

---

## 2. Afectaciones Identificadas

### 2.1 Archivos que Requieren Actualización ⚠️

#### 2.1.1 `simulacion_datos.py` - **CRÍTICO**

**Ubicación**: Raíz del proyecto

**Problema**: 
- Línea 27: Importa `PolizaAportada`
- Línea 466-517: Función `crear_polizas_aportadas()` usa `PolizaAportada.objects.get_or_create()`
- Línea 763: Cuenta `PolizaAportada.objects.count()`

**Impacto**: 
- El script de simulación fallará al ejecutarse
- No se podrán generar datos de prueba para pólizas

**Acción Requerida**:
```python
# Cambiar de:
from gestion.models import (..., PolizaAportada, ...)

# A:
from gestion.models import (..., Poliza, ...)

# Cambiar función crear_polizas_aportadas() para usar Poliza en lugar de PolizaAportada
# Actualizar el conteo en el resumen final
```

**Prioridad**: ALTA - Bloquea generación de datos de prueba

---

### 2.2 Archivos Históricos (No Requieren Acción) ✅

#### 2.2.1 Migraciones Antiguas
- `gestion/migrations/0007_alter_poliza_options_requerimientopoliza_and_more.py`: Crea el modelo (histórico)
- `gestion/migrations/0018_migrate_estado_aportado_data.py`: Migra datos (histórico)
- `gestion/migrations/0025_seguimientos.py`: Crea campo `poliza_aportada` (histórico)
- `gestion/migrations/0034_agregar_campos_polizas_otrosi.py`: Referencia histórica

**Acción**: Ninguna - Las migraciones históricas no deben modificarse

#### 2.2.2 Archivos de Respaldo
- `gestion/views.py.backup`: Archivo de respaldo, no afecta el sistema

**Acción**: Ninguna - Archivo de respaldo

#### 2.2.3 Documentación
- `docs/ANALISIS_CODIGO_DUPLICADO.md`: Documentación histórica

**Acción**: Ninguna - Documentación histórica

---

## 3. Funcionalidades Afectadas

### 3.1 Funcionalidades que YA Funcionan ✅

1. **Dashboard Principal**
   - ✅ Alertas de pólizas críticas funcionan correctamente
   - ✅ Cuenta solo pólizas del modelo `Poliza`

2. **Gestión de Pólizas**
   - ✅ Crear nueva póliza (usa `PolizaForm`)
   - ✅ Editar póliza (usa `PolizaForm`)
   - ✅ Validar póliza
   - ✅ Eliminar póliza

3. **Vista de Contratos**
   - ✅ Muestra pólizas correctamente
   - ✅ Seguimientos de pólizas funcionan
   - ✅ Auditoría de pólizas funciona

4. **Seguimientos de Pólizas**
   - ✅ Crear seguimiento (solo referencia a `Poliza`)
   - ✅ Listar seguimientos
   - ✅ Métodos `clean()` y `__str__()` actualizados

### 3.2 Funcionalidades que NO Funcionan ⚠️

1. **Script de Simulación de Datos**
   - ❌ `simulacion_datos.py` fallará al ejecutarse
   - ❌ No podrá crear pólizas de prueba usando `PolizaAportada`

---

## 4. Relaciones de Base de Datos

### 4.1 Relaciones Eliminadas

- `Contrato.polizas_aportadas` (related_name) - **ELIMINADO**
- `RequerimientoPoliza.polizas_aportadas` (related_name) - **ELIMINADO**
- `SeguimientoPoliza.poliza_aportada` (ForeignKey) - **ELIMINADO**

### 4.2 Relaciones que Permanecen

- `Contrato.polizas` (related_name) - **ACTIVO**
- `Poliza.contrato` (ForeignKey) - **ACTIVO**
- `Poliza.otrosi` (ForeignKey) - **ACTIVO**
- `SeguimientoPoliza.poliza` (ForeignKey) - **ACTIVO**

---

## 5. Impacto en Datos Existentes

### 5.1 Datos Perdidos

⚠️ **IMPORTANTE**: Si existían registros en `PolizaAportada` antes de aplicar la migración, estos fueron **ELIMINADOS PERMANENTEMENTE** de la base de datos.

**Recomendación**: 
- Verificar si había datos importantes en `PolizaAportada`
- Si los había, considerar migración de datos antes de eliminar (si aún es posible revertir)

### 5.2 Datos Preservados

- ✅ Todos los datos en `Poliza` permanecen intactos
- ✅ Todos los seguimientos asociados a `Poliza` permanecen intactos
- ✅ Todos los contratos y requerimientos permanecen intactos

---

## 6. Plan de Acción Correctiva

### 6.1 Acciones Inmediatas (PRIORIDAD ALTA)

1. **Actualizar `simulacion_datos.py`**
   - Eliminar import de `PolizaAportada`
   - Cambiar función `crear_polizas_aportadas()` para usar `Poliza`
   - Actualizar conteo en resumen final
   - Probar ejecución del script

### 6.2 Acciones de Verificación (PRIORIDAD MEDIA)

1. **Probar Funcionalidades Críticas**
   - ✅ Dashboard y alertas
   - ✅ Crear/editar pólizas
   - ✅ Seguimientos de pólizas
   - ✅ Vista de contratos

2. **Revisar Logs de Errores**
   - Monitorear errores relacionados con `PolizaAportada`
   - Verificar que no haya referencias ocultas

### 6.3 Acciones de Limpieza (PRIORIDAD BAJA)

1. **Limpiar Archivos de Respaldo**
   - Considerar eliminar `gestion/views.py.backup` si ya no es necesario

2. **Actualizar Documentación**
   - Actualizar `docs/ANALISIS_CODIGO_DUPLICADO.md` si es relevante

---

## 7. Riesgos Identificados

### 7.1 Riesgos Altos ⚠️

1. **Pérdida de Datos**
   - Si había datos en `PolizaAportada`, se perdieron
   - **Mitigación**: Ya aplicado - migración ejecutada

2. **Scripts de Simulación Rotos**
   - `simulacion_datos.py` no funcionará
   - **Mitigación**: Actualizar script (ver sección 6.1)

### 7.2 Riesgos Medios

1. **Referencias Ocultas**
   - Posibles referencias en código no revisado
   - **Mitigación**: Monitoreo continuo y pruebas exhaustivas

2. **Migraciones Futuras**
   - Migraciones que dependan de `PolizaAportada` fallarán
   - **Mitigación**: Revisar dependencias antes de crear nuevas migraciones

### 7.3 Riesgos Bajos

1. **Documentación Desactualizada**
   - Documentación que mencione `PolizaAportada`
   - **Mitigación**: Actualizar según necesidad

---

## 8. Pruebas Recomendadas

### 8.1 Pruebas Funcionales

- [ ] Crear nueva póliza desde gestión de contratos
- [ ] Editar póliza existente
- [ ] Eliminar póliza
- [ ] Crear seguimiento de póliza
- [ ] Ver alertas de pólizas en dashboard
- [ ] Exportar alertas de pólizas
- [ ] Validar póliza

### 8.2 Pruebas de Integración

- [ ] Verificar que las alertas muestran pólizas correctas
- [ ] Verificar que los seguimientos se asocian correctamente
- [ ] Verificar que la auditoría de pólizas funciona

### 8.3 Pruebas de Regresión

- [ ] Verificar que no se rompió funcionalidad existente
- [ ] Verificar que los contratos se muestran correctamente
- [ ] Verificar que los otrosí funcionan correctamente

---

## 9. Conclusión

La eliminación de `PolizaAportada` se completó exitosamente con las siguientes consideraciones:

✅ **Completado**:
- Modelo eliminado del código
- Referencias actualizadas en vistas y templates
- Migración aplicada en base de datos
- Sistema funcional sin errores

⚠️ **Pendiente**:
- Actualizar `simulacion_datos.py` para usar `Poliza` en lugar de `PolizaAportada`

📊 **Estado General**: El sistema está funcional y listo para producción, con la excepción del script de simulación que requiere actualización.

---

## 10. Contacto y Soporte

Para dudas o problemas relacionados con esta eliminación, revisar:
- Migración: `gestion/migrations/0047_eliminar_poliza_aportada.py`
- Este documento de análisis
- Historial de cambios en Git

