# Diseño: Refactorización Dashboard + Centro de Alertas

**Fecha:** 2026-04-16  
**Proyecto:** Gestión de Contratos — Avenida Chile  
**Problema:** El dashboard principal es lento en producción porque ejecuta 8 funciones de cálculo de alertas de forma síncrona antes de responder. A mayor volumen de contratos, mayor latencia.  
**Solución:** Separar el inicio (liviano, carga inmediata) del centro de alertas (vista dedicada con carga diferida).

---

## 1. Alcance

### Lo que cambia
- Vista `dashboard()` en `gestion/views/dashboard.py` — se vuelve liviana
- Template `templates/gestion/dashboard/index.html` — se refactoriza
- URL raíz `/` sigue apuntando al dashboard; se agrega `/alertas/`
- Se agregan 2 nuevos endpoints AJAX y 1 nueva vista

### Lo que NO cambia
- `gestion/services/alertas.py` — toda la lógica y cálculos de alertas permanecen intactos
- Estilos y paleta corporativa (variables CSS: `--avenida-orange`, `--avenida-green`, `--avenida-cyan`, `--avenida-magenta`)
- `base.html` — sin modificaciones
- Toda la lógica de exportaciones

---

## 2. Arquitectura

```
GET /                        → dashboard()              → index.html (inicio liviano)
GET /alertas/                → centro_alertas()         → alertas/index.html (vista dedicada)
GET /api/conteos-alertas/    → api_conteos_alertas()    → JSON con conteos + stats
GET /api/detalle-alertas/    → api_detalle_alertas()    → HTML pre-renderizado de todas las alertas
```

### Piezas nuevas

| Pieza | Archivo | Propósito |
|---|---|---|
| `centro_alertas()` | `gestion/views/dashboard.py` | Vista nueva — renderiza el contenedor de alertas |
| `api_conteos_alertas()` | `gestion/views/dashboard.py` | Endpoint AJAX — conteos + stats pesadas |
| `api_detalle_alertas()` | `gestion/views/dashboard.py` | Endpoint AJAX — HTML pre-renderizado con todas las alertas |
| `templates/gestion/alertas/index.html` | nuevo | Vista dedicada de alertas con indicador de progreso |
| `templates/gestion/alertas/_detalle_alertas.html` | nuevo | Partial con las tarjetas de alertas (reutiliza HTML actual) |

---

## 3. Nuevo inicio (dashboard liviano)

### Carga síncrona (rápida — solo queries de conteo O(1))
```python
total_contratos = Contrato.objects.count()   # query COUNT simple
total_polizas   = Poliza.objects.count()     # query COUNT simple
fecha_actual    = timezone.now().date()
```

El bucle de contratos vigentes/vencidos/modalidades **se mueve** a `api_conteos_alertas()`.

### Panel "Estado de Alertas" en el inicio
- 8 tarjetas pequeñas, una por categoría de alerta
- Cada tarjeta muestra un spinner (`<span class="spinner-border spinner-border-sm">`) mientras llega el AJAX
- Cuando llega la respuesta JSON, el spinner se reemplaza por el número real
- Números > 0: color naranja/rojo según paleta. Número = 0: verde.
- Botón prominente: **"Ver Centro de Alertas →"** (`href="{% url 'gestion:centro_alertas' %}"`)

### AJAX del inicio
- Un solo `fetch('/api/conteos-alertas/')` al cargar la página
- Actualiza simultáneamente: stats de vigentes/vencidos/modalidades Y los 8 conteos de alertas
- En caso de error: muestra "No disponible" en gris, sin romper la página

### Acciones rápidas
Se conservan idénticas al dashboard actual (Nuevo Contrato, Nuevo Tercero, Nuevo Local, etc.)

---

## 4. Vista dedicada de alertas (`/alertas/`)

### Comportamiento de carga
1. La página renderiza **inmediatamente** con un panel de progreso visible
2. JS ejecuta `fetch('/api/detalle-alertas/?tipo_alerta=X')` al `DOMContentLoaded`
3. Mientras espera, muestra una barra de progreso simulada con mensajes rotativos cada 1.5s:
   - "Revisando vencimientos de contratos..."
   - "Verificando estado de pólizas..."
   - "Calculando ajustes de IPC..."
   - "Revisando alertas de Salario Mínimo..."
   - "Verificando pólizas requeridas..."
   - "Calculando terminaciones anticipadas..."
   - "Verificando renovaciones automáticas..."
   - "Finalizando cálculos..."
4. Cuando llega la respuesta: barra al 100% → fade out del panel de progreso → fade in del contenido
5. En caso de error: mensaje de error con botón "Reintentar"

### Filtro (Todos / Clientes / Proveedores)
- Ubicado al tope, igual que hoy
- Al cambiar el filtro, dispara una nueva carga AJAX (misma experiencia de progreso)
- El filtro seleccionado se pasa como query param: `/api/detalle-alertas/?tipo_alerta=CLIENTE`

### Tarjetas de alertas
- Idénticas al dashboard actual: mismo HTML, mismos estilos CSS, mismo JS de "Ver más / Ver menos"
- Se extraen al partial `_detalle_alertas.html`
- `api_detalle_alertas()` usa `render_to_string('gestion/alertas/_detalle_alertas.html', context)` y devuelve el HTML en JSON: `{"html": "..."}`

---

## 5. Endpoints AJAX

### `GET /api/conteos-alertas/`

**Respuesta JSON:**
```json
{
  "contratos_vigentes": 42,
  "contratos_vencidos": 8,
  "total_polizas": 95,
  "contratos_fijos": 20,
  "contratos_variables": 12,
  "contratos_hibridos": 10,
  "alertas": {
    "vencimiento": 3,
    "polizas_criticas": 7,
    "preaviso": 2,
    "ipc": 5,
    "salario_minimo": 4,
    "polizas_requeridas": 1,
    "terminacion": 0,
    "renovacion_automatica": 6
  }
}
```

**Implementación:** Ejecuta el bucle de vigentes/modalidades + las 8 funciones de alertas (solo `len()` del resultado, no los objetos completos). Requiere login (`@login_required_custom`). Devuelve 403 si no autenticado.

### `GET /api/detalle-alertas/?tipo_alerta=`

**Respuesta JSON:**
```json
{
  "html": "<div class='row'>...</div>",
  "totales": {
    "vencimiento": 3,
    "polizas_criticas": 7,
    ...
  }
}
```

**Implementación:** Ejecuta las mismas 8 funciones del dashboard actual (lógica idéntica, incluyendo deduplicación IPC/Salario Mínimo), construye el contexto y usa `render_to_string` para generar el HTML del partial. Requiere login.

---

## 6. URLs nuevas

```python
# En gestion/urls.py
path('alertas/', views.centro_alertas, name='centro_alertas'),
path('api/conteos-alertas/', views.api_conteos_alertas, name='api_conteos_alertas'),
path('api/detalle-alertas/', views.api_detalle_alertas, name='api_detalle_alertas'),
```

---

## 7. Criterios de éxito

- El dashboard carga en < 300ms independientemente del número de contratos
- El usuario ve el inicio inmediatamente y entiende que las alertas están cargando
- La lógica de alertas no cambia — mismos resultados, mismos filtros
- El estilo de la nueva vista de alertas es consistente con el resto del proyecto
- El filtro Todos / Clientes / Proveedores funciona igual que antes
- Todos los endpoints AJAX requieren autenticación (no accesibles sin login)
