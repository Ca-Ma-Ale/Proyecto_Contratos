# Análisis de Usuarios y Permisos

## Resumen Ejecutivo

El sistema implementa dos niveles de acceso:
- **Usuario Normal (Empleado)**: Acceso a operaciones básicas de gestión
- **Usuario Admin (Staff)**: Acceso completo incluyendo configuraciones y operaciones críticas

---

## Sistema de Autenticación

### Decoradores Implementados

#### `@login_required_custom`
- **Ubicación**: `gestion/decorators.py`
- **Función**: Requiere que el usuario esté autenticado
- **Comportamiento**: Redirige a `/login/` si no está autenticado

#### `@admin_required`
- **Ubicación**: `gestion/decorators.py`
- **Función**: Requiere que el usuario sea staff/admin (`is_staff = True`)
- **Comportamiento**: 
  - Si no está autenticado: redirige a login
  - Si está autenticado pero no es staff: redirige a dashboard con mensaje de error

---

## Permisos por Rol

### 👤 Usuario Normal (Empleado)

#### ✅ Contratos
- Ver dashboard
- Ver lista de contratos
- Ver detalle de contratos
- Crear nuevos contratos
- Editar contratos existentes
- Exportar contratos (con filtros)
- Ver vista vigente de contratos
- **NO puede**: Eliminar contratos

#### ✅ Arrendatarios
- Ver lista de arrendatarios
- Crear nuevos arrendatarios
- Editar arrendatarios existentes
- Eliminar arrendatarios (si no tienen contratos asociados)

#### ✅ Locales
- Ver lista de locales
- Crear nuevos locales
- Editar locales existentes
- Eliminar locales (si no tienen contratos asociados)

#### ✅ Tipos de Contrato
- Ver lista de tipos de contrato
- Crear nuevos tipos
- Editar tipos existentes
- Eliminar tipos

#### ✅ Pólizas
- Gestionar pólizas de contratos
- Crear nuevas pólizas
- Editar pólizas existentes
- Validar pólizas
- Eliminar pólizas

#### ✅ Otro Sí
- Ver lista de Otro Sí de un contrato
- Crear nuevos Otro Sí
- Ver detalle de Otro Sí
- Enviar Otro Sí a revisión (desde estado BORRADOR)
- **NO puede**: 
  - Editar Otro Sí existentes
  - Eliminar Otro Sí
  - Aprobar/Rechazar Otro Sí

#### ✅ Informes de Ventas
- Ver lista de informes
- Crear nuevos informes
- Editar informes existentes
- Marcar informes como entregados/pendientes
- Eliminar informes
- Calcular facturación
- Ver resultados de cálculos
- Finalizar informes
- Exportar informes a Excel
- Descargar PDF/Excel de cálculos

#### ✅ IPC (Índice de Precios al Consumidor)
- Ver histórico de IPC
- Crear nuevos registros IPC
- Editar registros IPC
- Eliminar registros IPC
- Calcular IPC para contratos
- Confirmar cálculos IPC
- Ver detalle de cálculos
- Editar cálculos IPC
- Eliminar cálculos IPC
- Ver contratos pendientes de IPC
- Gestionar tipos de condición IPC
- Gestionar periodicidades IPC

#### ✅ Exportaciones
- Exportar contratos
- Exportar alertas de vencimiento
- Exportar alertas de pólizas
- Exportar alertas de preaviso
- Exportar alertas de IPC

#### ❌ Configuración
- **NO puede**: Acceder a configuración de empresa

#### ❌ Administración Django
- **NO puede**: Acceder al panel de administración (`/admin/`)

---

### 🔐 Usuario Admin (Staff)

#### ✅ Todo lo del Usuario Normal +
- Eliminar contratos
- Editar Otro Sí existentes (cualquier estado)
- Eliminar Otro Sí
- Aprobar/Rechazar Otro Sí (cambiar estado de EN_REVISION a APROBADO/RECHAZADO)
- Acceder a configuración de empresa
- Acceder al panel de administración Django (`/admin/`)

---

## Vistas Protegidas con `@admin_required`

### Contratos
- `eliminar_contrato` (línea 515 en `gestion/views/contratos.py`)

### Configuración
- `configuracion_empresa` (línea 10 en `gestion/views/configuracion.py`)

### Otro Sí
- `editar_otrosi` (línea 232 en `gestion/views/otrosi.py`)
- `aprobar_otrosi` (línea 428 en `gestion/views/otrosi.py`)
- `eliminar_otrosi` (línea 500 en `gestion/views/otrosi.py`)

---

## Controles en Templates

### Verificación de `user.is_staff`

#### `templates/base.html`
- Link a "Configuración" visible para todos (pero protegido por decorador)
- Link a "Administración" solo visible para staff

#### `templates/gestion/contratos/detalle.html`
- Botón "Eliminar Contrato" solo visible para staff (líneas 1032, 1037)

#### `templates/gestion/otrosi/lista.html`
- Botones "Editar" y "Eliminar" Otro Sí solo visibles para staff (líneas 162, 167)

#### `templates/gestion/otrosi/detalle.html`
- Botones de aprobación/rechazo solo visibles para staff cuando el Otro Sí está en estado EN_REVISION (línea 22)
- Botones "Editar" y "Eliminar" solo visibles para staff (líneas 28, 34)

---

## Problemas Identificados y Resueltos

### ✅ Correcciones Aplicadas

1. **Link de Configuración Visible para Todos** - ✅ RESUELTO
   - Link oculto para usuarios normales en `templates/base.html`

2. **Eliminaciones Sin Restricción** - ✅ RESUELTO
   - `eliminar_arrendatario` restringido a admin
   - `eliminar_local` restringido a admin
   - `eliminar_tipo_contrato` restringido a admin
   - `eliminar_poliza` restringido a admin
   - Botones de eliminación ocultos en templates para usuarios normales

3. **Configuración IPC Accesible para Todos** - ✅ RESUELTO
   - `nuevo_tipo_condicion_ipc` restringido a admin
   - `editar_tipo_condicion_ipc` restringido a admin
   - `eliminar_tipo_condicion_ipc` restringido a admin
   - `nueva_periodicidad_ipc` restringido a admin
   - `editar_periodicidad_ipc` restringido a admin
   - `eliminar_periodicidad_ipc` restringido a admin
   - `nuevo_ipc_historico` restringido a admin
   - `editar_ipc_historico` restringido a admin
   - `eliminar_ipc_historico` restringido a admin
   - `eliminar_calculo_ipc` restringido a admin
   - Botones de creación/edición/eliminación ocultos en templates para usuarios normales

## Problemas Identificados (Histórico)

### ⚠️ Problema 1: Link de Configuración Visible para Todos
**Ubicación**: `templates/base.html` línea 209

**Problema**: El link "Configuración" está visible para todos los usuarios autenticados, pero la vista está protegida con `@admin_required`. Esto puede confundir a los usuarios normales.

**Recomendación**: Agregar `{% if user.is_staff %}` alrededor del link.

### ⚠️ Problema 2: Eliminación de Arrendatarios y Locales
**Ubicación**: `gestion/views/arrendatarios.py` y `gestion/views/locales.py`

**Problema**: Los usuarios normales pueden eliminar arrendatarios y locales. Aunque hay validación para evitar eliminación si tienen contratos asociados, esta es una operación crítica que debería estar restringida a administradores.

**Recomendación**: Agregar `@admin_required` a las vistas `eliminar_arrendatario` y `eliminar_local`.

### ⚠️ Problema 3: Eliminación de Tipos de Contrato
**Ubicación**: `gestion/views/tipos_contrato.py`

**Problema**: Similar al anterior, los usuarios normales pueden eliminar tipos de contrato, lo cual puede afectar la integridad de los datos.

**Recomendación**: Agregar `@admin_required` a la vista `eliminar_tipo_contrato`.

### ⚠️ Problema 4: Eliminación de Pólizas
**Ubicación**: `gestion/views/polizas.py`

**Problema**: Los usuarios normales pueden eliminar pólizas, lo cual es una operación crítica.

**Recomendación**: Revisar si la eliminación de pólizas debería estar restringida a administradores.

### ⚠️ Problema 5: Gestión de IPC
**Ubicación**: `gestion/views/configuracion_ipc.py` y `gestion/views/ipc.py`

**Problema**: Los usuarios normales pueden crear, editar y eliminar configuraciones de IPC (tipos de condición, periodicidades) y valores históricos de IPC. Estas son configuraciones críticas del sistema.

**Recomendación**: Considerar restringir las operaciones de configuración IPC a administradores.

---

## Recomendaciones

### Prioridad Alta

1. **Ocultar link de Configuración para usuarios normales**
   - Agregar `{% if user.is_staff %}` en `templates/base.html`

2. **Restringir eliminaciones críticas a administradores**
   - Agregar `@admin_required` a:
     - `eliminar_arrendatario`
     - `eliminar_local`
     - `eliminar_tipo_contrato`
     - `eliminar_poliza` (revisar caso de uso)

### Prioridad Media

3. **Restringir configuración IPC a administradores**
   - Agregar `@admin_required` a:
     - `nuevo_tipo_condicion_ipc`
     - `editar_tipo_condicion_ipc`
     - `eliminar_tipo_condicion_ipc`
     - `nueva_periodicidad_ipc`
     - `editar_periodicidad_ipc`
     - `eliminar_periodicidad_ipc`
     - `nuevo_ipc_historico`
     - `editar_ipc_historico`
     - `eliminar_ipc_historico`

### Prioridad Baja

4. **Documentar flujo de aprobación de Otro Sí**
   - Crear documentación sobre el proceso de creación → revisión → aprobación

5. **Considerar roles adicionales**
   - Evaluar si se necesita un rol intermedio (ej: "Supervisor") con permisos limitados

---

## Flujo de Permisos: Otro Sí

### Usuario Normal
1. Puede crear Otro Sí (estado inicial: BORRADOR)
2. Puede enviar a revisión (BORRADOR → EN_REVISION)
3. **NO puede** editar después de enviar a revisión
4. **NO puede** aprobar/rechazar

### Usuario Admin
1. Puede crear Otro Sí
2. Puede editar Otro Sí en cualquier estado
3. Puede aprobar Otro Sí (EN_REVISION → APROBADO)
4. Puede rechazar Otro Sí (EN_REVISION → RECHAZADO)
5. Puede eliminar Otro Sí

---

## Resumen de Acciones por Módulo

### Contratos
- **Crear/Editar/Ver**: ✅ Todos los usuarios
- **Eliminar**: ❌ Solo Admin

### Arrendatarios/Locales
- **Crear/Editar/Ver**: ✅ Todos los usuarios
- **Eliminar**: ⚠️ Todos los usuarios (recomendado: solo Admin)

### Pólizas
- **Gestionar/Crear/Editar/Validar**: ✅ Todos los usuarios
- **Eliminar**: ⚠️ Todos los usuarios (revisar)

### Otro Sí
- **Crear/Ver/Enviar a Revisión**: ✅ Todos los usuarios
- **Editar/Eliminar/Aprobar**: ❌ Solo Admin

### Configuración
- **Acceso**: ❌ Solo Admin

### IPC
- **Calcular/Ver**: ✅ Todos los usuarios
- **Configurar tipos/periodicidades**: ⚠️ Todos los usuarios (recomendado: solo Admin)
- **Gestionar histórico**: ⚠️ Todos los usuarios (recomendado: solo Admin)

---

## Conclusión

El sistema tiene una base sólida de permisos, pero hay áreas de mejora:

1. **Seguridad**: Algunas operaciones críticas (eliminaciones, configuraciones) deberían estar restringidas a administradores
2. **UX**: El link de configuración debería ocultarse para usuarios normales
3. **Consistencia**: Revisar si todas las eliminaciones deberían requerir permisos de admin

La implementación actual permite que usuarios normales realicen operaciones que podrían afectar la integridad de los datos, aunque hay validaciones de negocio que previenen algunos problemas.

