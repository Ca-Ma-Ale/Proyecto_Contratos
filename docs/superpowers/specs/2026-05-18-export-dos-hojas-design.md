# Spec: Export de Contratos en Dos Hojas (Clientes / Proveedores)

**Fecha:** 2026-05-18  
**Estado:** Aprobado

---

## Contexto

El informe de contratos (`exportar_contratos`) actualmente genera un Excel de una sola hoja con columnas fijas diseñadas para contratos CLIENTE (arrendatarios). Los contratos PROVEEDOR tienen campos de pólizas completamente distintos (12 coberturas RCE y 11 amparos de cumplimiento) que no aparecen en el export actual.

---

## Objetivo

Separar el export en **dos hojas** dentro del mismo archivo Excel:
- Hoja `"Clientes"` — contratos con `tipo_contrato_cliente_proveedor = 'CLIENTE'`
- Hoja `"Proveedores"` — contratos con `tipo_contrato_cliente_proveedor = 'PROVEEDOR'`

Cada hoja tiene su propio conjunto de columnas de pólizas, eliminando las columnas que no aplican a cada tipo.

---

## Comportamiento

- Ambas hojas **siempre están presentes** en el archivo, incluso si una no tiene contratos.
- Hoja vacía: encabezados normales + una fila con `"Sin contratos registrados"` en la primera celda.
- `ExportacionVaciaError` solo se lanza si **ambas** hojas están vacías (ningún contrato pasa los filtros activos).
- Los filtros de la vista (estado, local, tipo, etc.) aplican igualmente a ambas hojas.

---

## Estructura de columnas

### Columnas base — idénticas en ambas hojas

| # | Columna |
|---|---------|
| 1 | Num. Contrato |
| 2 | Tipo Cliente/Proveedor |
| 3 | Tipo Contrato |
| 4 | Tipo Servicio |
| 5 | Tercero |
| 6 | NIT Tercero |
| 7 | Local |
| 8 | Ubicación |
| 9 | Área (m²) |
| 10 | Objeto / Destinación |
| 11 | Fecha Firma |
| 12 | Fecha Inicial |
| 13 | Fecha Final Inicial |
| 14 | Fecha Final Vigente |
| 15 | Duración Inicial (meses) |
| 16 | Estado |
| 17 | Prórroga Automática |
| 18 | Días Preaviso No Renovación |
| 19 | Días Terminación Anticipada |
| 20 | Modalidad Pago |
| 21 | Canon Vigente |
| 22 | Canon Mínimo Garantizado Vigente |
| 23 | % Ventas |
| 24 | Reporta Ventas |
| 25 | Día Límite Reporte Ventas |
| 26 | Cobra Servicios Públicos |
| 27 | Tiene Cláusula SARLAFT |
| 28 | Tiene Cláusula Protección de Datos |
| 29 | Interés Mora |
| 30 | Tipo Condición IPC |
| 31 | Puntos Adicionales IPC |
| 32 | Periodicidad IPC |
| 33 | Mes Aumento IPC |
| 34 | Tiene Periodo Gracia |
| 35 | Fecha Inicio Periodo Gracia |
| 36 | Fecha Fin Periodo Gracia |
| 37 | Condición Gracia |

### Bloque Póliza RCE

| Columna | Clientes | Proveedores |
|---------|----------|-------------|
| Exige Póliza RCE | ✓ | ✓ |
| Valor Asegurado RCE | ✓ | ✓ |
| PLO RCE | ✓ | — |
| Patronal RCE | ✓ | — |
| Gastos Médicos RCE | ✓ | — |
| Vehículos RCE | ✓ | — |
| Contratistas RCE | ✓ | — |
| Perjuicios Extrapatrimoniales RCE | ✓ | — |
| Daño Moral RCE | ✓ | — |
| Lucro Cesante RCE | ✓ | — |
| Daños Materiales a Terceros RCE | — | ✓ |
| Lesiones Personales a Terceros RCE | — | ✓ |
| Muerte de Terceros RCE | — | ✓ |
| Daños a Bienes de Terceros RCE | — | ✓ |
| Responsabilidad Patronal RCE | — | ✓ |
| Responsabilidad Cruzada RCE | — | ✓ |
| Daños por Contratistas RCE | — | ✓ |
| Daños en Ejecución Contrato RCE | — | ✓ |
| Daños en Predios Vecinos RCE | — | ✓ |
| Gastos Médicos RCE | — | ✓ |
| Gastos de Defensa RCE | — | ✓ |
| Perjuicios Patrimoniales RCE | — | ✓ |
| Meses Vigencia RCE | ✓ | ✓ |
| Fecha Inicio Vigencia RCE | ✓ | ✓ |
| Fecha Fin Vigencia RCE | ✓ | ✓ |

### Bloque Póliza Cumplimiento

| Columna | Clientes | Proveedores |
|---------|----------|-------------|
| Exige Póliza Cumplimiento | ✓ | ✓ |
| Valor Asegurado Cumplimiento | ✓ | ✓ |
| Remuneraciones Cumplimiento | ✓ | — |
| Servicios Públicos Cumplimiento | ✓ | — |
| IVA Cumplimiento | ✓ | — |
| Cuota Admin Cumplimiento | ✓ | — |
| Amparo Cumplimiento Contrato | — | ✓ |
| Amparo Buen Manejo Anticipo | — | ✓ |
| Amparo Amortización Anticipo | — | ✓ |
| Amparo Salarios y Prestaciones | — | ✓ |
| Amparo Aportes Seguridad Social | — | ✓ |
| Amparo Calidad Servicio | — | ✓ |
| Amparo Estabilidad Obra | — | ✓ |
| Amparo Calidad Bienes | — | ✓ |
| Amparo Multas | — | ✓ |
| Amparo Cláusula Penal | — | ✓ |
| Amparo Sanciones Incumplimiento | — | ✓ |
| Meses Vigencia Cumplimiento | ✓ | ✓ |
| Fecha Inicio Vigencia Cumplimiento | ✓ | ✓ |
| Fecha Fin Vigencia Cumplimiento | ✓ | ✓ |

### Bloques iguales en ambas hojas

**Póliza Arrendamiento:** Exige · Valor Asegurado · Remuneraciones · Servicios Públicos · IVA · Cuota Admin · Meses · Fecha Inicio · Fecha Fin

**Póliza Todo Riesgo:** Exige · Valor Asegurado · Meses · Fecha Inicio · Fecha Fin

**Otras Pólizas:** Exige · Nombre · Valor Asegurado · Meses · Fecha Inicio · Fecha Fin

**Columnas finales:** Cláusula Penal Incumplimiento · Penalidad Terminación Anticipada · Multa Mora No Restitución · NIT · Representante Legal · Marca Comercial · Supervisor Concedente · Supervisor Contraparte · Otrosí Modificador Fecha Final · N° Otrosí · N° Renovaciones Automáticas · Fecha Último Otrosí Aprobado · Fecha Última Renovación Aprobada · Doc. Pendientes Aprobación · Días al Vencimiento · Canon Base · Canon Mínimo Garantizado Base · Fecha Último IPC Aplicado · % Último IPC Aplicado · Recobro Póliza RCE · Recobro Póliza Cumplimiento · Recobro Póliza Arrendamiento · Recobro Póliza Todo Riesgo · Recobro Otras Pólizas

---

## Cambios de código

### 0. `gestion/utils_otrosi.py` — extender `_CAMPOS_POLIZAS_EXPORTACION`

Los campos `rce_cobertura_*` y `cumplimiento_amparo_*` tienen contrapartes `nuevo_*` en `OtroSi`, pero actualmente no están en `_CAMPOS_POLIZAS_EXPORTACION`, por lo que `get_valores_polizas_vigentes` no los resuelve vía efecto cadena.

Se añaden los 23 pares `(nuevo_campo, campo_base)` al final de la lista:

```python
# Coberturas RCE - Proveedor
('nuevo_rce_cobertura_danos_materiales', 'rce_cobertura_danos_materiales'),
('nuevo_rce_cobertura_lesiones_personales', 'rce_cobertura_lesiones_personales'),
... (12 campos)

# Amparos Cumplimiento - Proveedor
('nuevo_cumplimiento_amparo_cumplimiento_contrato', 'cumplimiento_amparo_cumplimiento_contrato'),
... (11 campos)
```

Con esto, `pv = get_valores_polizas_vigentes(contrato, fecha)` ya devuelve los valores correctos (respetando OtroSí) para la hoja Proveedores.

### 1. `gestion/services/exportes.py`

Nueva función:

```python
def generar_excel_multi_hoja(hojas: list[tuple[str, list[ColumnaExportacion], list]]) -> bytes
```

- `hojas`: lista de `(nombre_hoja, columnas, registros)`
- Crea un `Workbook` con una hoja por entrada
- Aplica `FormateadorExcelCorporativo` a cada hoja
- Si `registros` está vacío: escribe encabezados + fila `"Sin contratos registrados"`
- Añade timestamp al pie de cada hoja
- Lanza `ExportacionVaciaError` si **todas** las hojas están vacías

### 2. `gestion/views/contratos.py` — función `exportar_contratos`

- Separar el loop `for contrato in contratos_lista` en dos listas: `registros_clientes` y `registros_proveedores`
- Definir `columnas_clientes` y `columnas_proveedores` (comparten columnas base y finales; difieren en bloque RCE y Cumplimiento)
- Extraer los campos RCE y Cumplimiento de proveedor directamente del contrato base (no pasan por `get_valores_polizas_vigentes` que no los incluye actualmente)
- Llamar `generar_excel_multi_hoja([(\"Clientes\", columnas_clientes, registros_clientes), (\"Proveedores\", columnas_proveedores, registros_proveedores)])`
- Eliminar la llamada a `generar_excel_corporativo` existente

### 3. Datos de póliza proveedor en el registro

Para la hoja Proveedores, los campos `rce_cobertura_*` y `cumplimiento_amparo_*` se leen de `pv` (resultado de `get_valores_polizas_vigentes`), que ya incluye el efecto cadena gracias al paso 0. El gate `exige_poliza_*` aplica igual que para clientes.

---

## Lo que NO cambia

- La URL, la vista y los filtros existentes — ningún cambio en la interfaz de usuario.
- `exportar_otrosi` — fuera del alcance de esta spec.
- La lógica de `get_valores_polizas_vigentes` — no se modifica.
