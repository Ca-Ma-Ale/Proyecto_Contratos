# Diseño: Logo real y fondo del login

**Fecha:** 2026-08-09
**Estado:** Aprobado, pendiente de plan de implementación

## Contexto

El sistema muestra hoy un "logo" hecho con 4 `<div>` de color (cuadrados CSS) en dos lugares: el panel izquierdo del login (`templates/registration/login.html`) y el navbar superior (`templates/base.html`). El cliente (Centro Comercial Avenida de Chile) tiene un logo real: un ícono de 4 figuras (triángulo verde, triángulo invertido naranja, media luna cian, cuadrado magenta) que usa exactamente los mismos colores de marca ya definidos en las variables CSS (`--avenida-green`, `--avenida-orange`, `--avenida-cyan`, `--avenida-magenta`). El logo fue extraído de `Logo CC Av Chile Modos.pdf` (provisto por el cliente) como SVG vectorial con fondo transparente.

Adicionalmente, el fondo del `body` del login es un degradado plano oscuro sin elementos gráficos. Se pide mejorarlo visualmente.

## Alcance

1. Campo de logo configurable por empresa (el sistema ya tiene un modelo `ConfiguracionEmpresa` pensado para multi-cliente).
2. Reemplazar el logo CSS por el logo real en navbar y login, con fallback al logo de Avenida de Chile cuando no hay uno cargado.
3. Rediseñar el fondo del `body` del login con las figuras del ícono de marca, en grande y baja opacidad, ancladas en las esquinas.

Fuera de alcance: rediseño del panel izquierdo del login (`.login-left`, degradado naranja-magenta) — se mantiene igual, solo cambia el logo que contiene. No se toca el logo de otros módulos/reportes (PDF, Excel) si los hubiera.

## 1. Almacenamiento del logo

- Se agrega `logo = models.ImageField(upload_to='empresa/logos/', blank=True, null=True, verbose_name='Logo de la Empresa')` al modelo `ConfiguracionEmpresa` (`gestion/models.py`), con su migración correspondiente.
- `ConfiguracionEmpresaForm` (`gestion/forms.py`) usa `exclude`, no `fields` — el campo nuevo aparece automáticamente en el formulario sin tocar esa clase.
- `Pillow` ya está en `requirements.txt`; `MEDIA_ROOT`/`MEDIA_URL` ya están configurados en `settings.py` y `settings_production.py` — no se necesita infraestructura nueva.
- Cambios de template en `templates/gestion/configuracion/empresa.html`:
  - Agregar `enctype="multipart/form-data"` al `<form>` (línea 52).
  - Agregar una sección de subida de archivo con vista previa del logo actual (si existe), siguiendo el mismo patrón visual (`form-label`, `form-control`) que los demás campos de esa página.

## 2. Renderizado del logo (navbar + login)

- **Patrón "chip blanco":** en ambos lugares, el logo se muestra dentro de una tarjeta blanca redondeada (fondo blanco, `border-radius`, padding pequeño), nunca directo sobre el fondo oscuro/degradado. Esto garantiza legibilidad sin importar qué logo suba un cliente futuro (la mayoría de logos corporativos están diseñados para fondo claro), evitando mantener una variante "para fondo oscuro" de cada logo.
- **Fallback:** si `empresa_config.logo` está vacío (caso actual, la fila de configuración no tiene logo cargado todavía), se usa como imagen por defecto el ícono real de Avenida de Chile (SVG a color, fondo transparente, solo las 4 figuras — sin el wordmark, porque el nombre de la empresa ya se muestra aparte como texto). Este archivo se empaqueta en `static/gestion/img/avenida-chile-icono.svg`.
- **Reemplazos concretos:**
  - `templates/registration/login.html`: el bloque `.logo-squares` (líneas ~59-70 de estilos, ~104-111 de markup) pasa a ser un chip con `<img>`.
  - `templates/base.html`: el bloque de cuadros dentro de `.navbar-brand` (líneas ~213-222) pasa a ser un chip con `<img>`.
- **Tamaños:** navbar ~40px de alto; panel del login ~80-90px de alto. `object-fit: contain` para no deformar el logo subido por el cliente.
- El texto (`nombre_empresa`, `nit_empresa`, etc.) sigue igual, sin cambios — solo cambia el elemento gráfico.

## 3. Fondo del login

- El `body` de `login.html` mantiene su degradado oscuro actual (`linear-gradient(135deg, var(--avenida-dark) 0%, #34495e 100%)`) y se le agregan las 4 figuras del ícono de marca (triángulo, triángulo invertido, media luna, cuadrado) en tamaño grande, ancladas en las esquinas de la ventana, con opacidad baja (~15-20%) y desenfoque suave — puramente decorativas, sin competir visualmente con la tarjeta de login.
- Se usa el mismo asset `avenida-chile-icono.svg` (o las figuras recortadas individualmente) reutilizado a mayor escala, no una aproximación en CSS, para que se vea nítido en cualquier resolución de pantalla.
- No se introducen colores nuevos: se reutilizan las variables CSS de marca ya definidas (`--avenida-green`, `--avenida-orange`, `--avenida-cyan`, `--avenida-magenta`) y el tono oscuro ya existente (`--avenida-dark`).
- El panel `.login-left` (degradado naranja-magenta) no cambia — sigue igual, solo el logo que contiene.

## Testing / validación

- Verificar visualmente el login y el navbar con y sin logo cargado en `ConfiguracionEmpresa` (fallback vs. logo subido).
- Probar subida de logo desde el panel de configuración (formato PNG/SVG/JPG, tamaño razonable) y confirmar que se guarda en `media/empresa/logos/` y se refleja de inmediato en navbar y login.
- Confirmar que el fondo del login se ve bien en pantallas anchas y angostas (responsive) — las figuras de esquina no deben tapar el formulario en móvil.
