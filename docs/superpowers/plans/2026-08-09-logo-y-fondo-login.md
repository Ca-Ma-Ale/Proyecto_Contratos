# Logo real y fondo del login — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el logo CSS (cuadros de color) por el logo real del cliente en el navbar y el login, hacerlo configurable por empresa, y mejorar el fondo del login con las figuras del ícono de marca en baja opacidad.

**Architecture:** Se agrega un campo `logo` (ImageField) al modelo `ConfiguracionEmpresa` ya existente, subible desde el panel de configuración ya existente. En las plantillas, el logo (el subido por el cliente, o un ícono SVG por defecto empaquetado como asset estático) se muestra dentro de una tarjeta blanca ("chip") para garantizar contraste sobre fondos oscuros/de color. El fondo del login se decora con el mismo ícono SVG, grande y en baja opacidad, en las 4 esquinas.

**Tech Stack:** Django 5 (templates, ImageField, forms), Pillow (ya instalado), Bootstrap 5, SVG.

## Global Constraints

- Todos los comandos se ejecutan con el entorno virtual activo: `source .venv/Scripts/activate` desde `C:\Users\User\Proyectos\Proyecto_Contratos`.
- Los tests se ejecutan con `python manage.py test <ruta.al.test>` (no hay pytest configurado en este proyecto).
- No modificar `ConfiguracionEmpresaForm` en `gestion/forms.py` — usa `exclude`, así que el campo nuevo del modelo aparece solo en el formulario.
- No introducir colores nuevos: reutilizar las variables CSS ya definidas (`--avenida-green`, `--avenida-orange`, `--avenida-cyan`, `--avenida-magenta`, `--avenida-dark`).
- El panel `.login-left` (degradado naranja-magenta) no cambia de diseño — solo el logo que contiene.
- Spec de referencia: `docs/superpowers/specs/2026-08-09-logo-y-fondo-login-design.md`.

---

### Task 1: Asset del logo por defecto (ícono SVG)

**Files:**
- Create: `static/gestion/img/avenida-chile-icono.svg`

**Interfaces:**
- Produces: la ruta estática `gestion/img/avenida-chile-icono.svg` (resuelta vía `{% static %}`), usada como logo por defecto en las Tareas 3, 4 y 5 cuando `empresa_config.logo` no existe.

- [ ] **Step 1: Crear el archivo SVG con el ícono de marca (4 figuras, extraídas del PDF oficial del cliente, sin el wordmark)**

Crear `static/gestion/img/avenida-chile-icono.svg` con este contenido exacto:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="119.347656 155.773438 298.285156 338.085937">
<path fill-rule="nonzero" fill="rgb(50%, 79.998779%, 15.684509%)" fill-opacity="1" d="M 131.113281 288.316406 C 130.027344 290.515625 129.347656 292.960938 129.347656 295.574219 C 129.347656 304.621094 136.6875 311.96875 145.738281 311.96875 C 146.191406 311.96875 146.621094 311.871094 147.078125 311.828125 L 258.984375 311.96875 C 268.03125 311.96875 275.363281 304.621094 275.363281 295.574219 C 275.363281 293.359375 274.917969 291.246094 274.109375 289.308594 L 274.152344 289.242188 L 233.652344 187.730469 C 229.140625 174.980469 217.09375 165.773438 202.800781 165.773438 C 188.882812 165.773438 177.058594 174.464844 172.273438 186.679688 L 172.246094 186.679688 Z M 131.113281 288.316406 "/>
<path fill-rule="nonzero" fill="rgb(96.469116%, 52.938843%, 7.058716%)" fill-opacity="1" d="M 405.429688 189.425781 C 406.523438 187.222656 407.199219 184.777344 407.199219 182.167969 C 407.199219 173.109375 399.867188 165.773438 390.8125 165.773438 C 390.347656 165.773438 389.917969 165.867188 389.46875 165.914062 L 277.554688 165.773438 C 268.511719 165.773438 261.179688 173.109375 261.179688 182.167969 C 261.179688 184.386719 261.625 186.496094 262.425781 188.429688 L 262.394531 188.5 L 302.898438 290.007812 C 307.410156 302.757812 319.449219 311.960938 333.746094 311.960938 C 347.664062 311.960938 359.492188 303.269531 364.273438 291.0625 L 364.296875 291.0625 Z M 405.429688 189.425781 "/>
<path fill-rule="nonzero" fill="rgb(73.921204%, 4.804993%, 55.487061%)" fill-opacity="1" d="M 407.632812 475.183594 C 407.632812 479.757812 403.886719 483.5 399.320312 483.5 L 287.863281 483.5 C 283.289062 483.5 279.550781 479.757812 279.550781 475.183594 L 279.550781 343.296875 C 279.550781 338.730469 283.289062 334.996094 287.863281 334.996094 L 399.320312 334.996094 C 403.886719 334.996094 407.632812 338.730469 407.632812 343.296875 Z M 407.632812 475.183594 "/>
<path fill-rule="nonzero" fill="rgb(0%, 67.83905%, 93.728638%)" fill-opacity="1" d="M 243.671875 334.996094 L 203.40625 334.996094 L 203.40625 335.171875 C 162.683594 335.539062 129.785156 368.625 129.785156 409.433594 C 129.785156 450.25 162.683594 483.332031 203.40625 483.710938 L 203.40625 483.859375 L 242.71875 483.859375 L 242.71875 483.855469 L 243.671875 483.855469 C 248.25 483.855469 251.992188 480.117188 251.992188 475.527344 L 251.992188 343.308594 C 251.992188 338.738281 248.25 334.996094 243.671875 334.996094 "/>
</svg>
```

- [ ] **Step 2: Verificar que el SVG es XML válido**

Run: `python -c "import xml.dom.minidom; xml.dom.minidom.parse('static/gestion/img/avenida-chile-icono.svg'); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add static/gestion/img/avenida-chile-icono.svg
git commit -m "feat: agregar icono SVG del logo real de Avenida de Chile"
```

---

### Task 2: Campo `logo` en `ConfiguracionEmpresa` (modelo + migración)

**Files:**
- Modify: `gestion/models.py:193-215` (clase `ConfiguracionEmpresa`)
- Create: migración generada por `makemigrations` (siguiente número secuencial después de `0077_cascade_eliminar_calculo_al_eliminar_informe_ventas.py`)
- Test: `gestion/tests/tests_configuracion_empresa_logo.py`

**Interfaces:**
- Produces: `ConfiguracionEmpresa.logo` (`ImageField`, `blank=True`, `null=True`, `upload_to='empresa/logos/'`), usado por las Tareas 3, 4 y 5 como `empresa_config.logo` / `configuracion.logo`.

- [ ] **Step 1: Escribir el test que falla**

Crear `gestion/tests/tests_configuracion_empresa_logo.py`:

```python
import base64
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from gestion.models import ConfiguracionEmpresa

# PNG transparente de 1x1 pixel, válido para Pillow/ImageField
PNG_1PX = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ConfiguracionEmpresaLogoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_guarda_logo_en_configuracion_empresa(self):
        logo_file = SimpleUploadedFile('logo.png', PNG_1PX, content_type='image/png')
        config = ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa Test',
            nit_empresa='900123456-1',
            representante_legal='Juana Ejemplo',
            logo=logo_file,
        )
        config.refresh_from_db()
        self.assertTrue(config.logo.name.startswith('empresa/logos/logo'))

    def test_logo_es_opcional(self):
        config = ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa Sin Logo',
            nit_empresa='900123456-2',
            representante_legal='Juana Ejemplo',
        )
        self.assertFalse(config.logo)
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `python manage.py test gestion.tests.tests_configuracion_empresa_logo -v 2`
Expected: FAIL — `TypeError: ConfiguracionEmpresa() got unexpected keyword arguments: 'logo'`

- [ ] **Step 3: Agregar el campo al modelo**

En `gestion/models.py`, dentro de la clase `ConfiguracionEmpresa` (línea 193), agregar el campo justo después de `activo` (línea 201):

```python
    activo = models.BooleanField(default=True, verbose_name='Configuración Activa')
    logo = models.ImageField(
        upload_to='empresa/logos/',
        blank=True,
        null=True,
        verbose_name='Logo de la Empresa'
    )
```

- [ ] **Step 4: Generar y aplicar la migración**

Run: `python manage.py makemigrations gestion`
Expected: `Migrations for 'gestion': gestion/migrations/00XX_configuracionempresa_logo.py - Add field logo to configuracionempresa`

Run: `python manage.py migrate gestion`
Expected: `Applying gestion.00XX_configuracionempresa_logo... OK`

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `python manage.py test gestion.tests.tests_configuracion_empresa_logo -v 2`
Expected: `OK` (2 tests)

- [ ] **Step 6: Commit**

```bash
git add gestion/models.py gestion/migrations/ gestion/tests/tests_configuracion_empresa_logo.py
git commit -m "feat: agregar campo logo a ConfiguracionEmpresa"
```

---

### Task 3: Subida de logo desde el panel de configuración

**Files:**
- Modify: `gestion/views/configuracion.py:19` (vista `configuracion_empresa`)
- Modify: `templates/gestion/configuracion/empresa.html:52` (formulario) y sección "Ubicación institucional" (después de línea 173)
- Test: `gestion/tests/tests_configuracion_empresa_vista_logo.py`

**Interfaces:**
- Consumes: `ConfiguracionEmpresa.logo` (Tarea 2), `ConfiguracionEmpresaForm` (ya existe, `gestion/forms.py:759`, no requiere cambios porque usa `exclude`).
- Produces: el panel de administración (`gestion:configuracion_empresa`) acepta y persiste archivos subidos en el campo `logo`.

- [ ] **Step 1: Escribir el test que falla**

Crear `gestion/tests/tests_configuracion_empresa_vista_logo.py`:

```python
import base64
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from gestion.models import ConfiguracionEmpresa

PNG_1PX = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ConfiguracionEmpresaVistaLogoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_config', password='testpass123', is_staff=True
        )
        self.client.force_login(self.user)

    def test_formulario_tiene_enctype_multipart(self):
        response = self.client.get(reverse('gestion:configuracion_empresa'))
        self.assertContains(response, 'multipart/form-data')

    def test_subir_logo_desde_panel_configuracion(self):
        logo_file = SimpleUploadedFile('logo.png', PNG_1PX, content_type='image/png')
        response = self.client.post(reverse('gestion:configuracion_empresa'), {
            'nombre_empresa': 'Empresa Test',
            'nit_empresa': '900123456-1',
            'representante_legal': 'Juana Ejemplo',
            'telefono': '',
            'email': '',
            'direccion': '',
            'activo': 'on',
            'logo': logo_file,
        })
        self.assertEqual(response.status_code, 302)
        config = ConfiguracionEmpresa.objects.filter(activo=True).first()
        self.assertIsNotNone(config)
        self.assertTrue(config.logo)
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `python manage.py test gestion.tests.tests_configuracion_empresa_vista_logo -v 2`
Expected: FAIL — `test_formulario_tiene_enctype_multipart` falla porque el HTML no contiene `multipart/form-data`; `test_subir_logo_desde_panel_configuracion` falla porque `config.logo` queda vacío (la vista no pasa `request.FILES` al formulario).

- [ ] **Step 3: Pasar `request.FILES` al formulario en la vista**

En `gestion/views/configuracion.py:19`, cambiar:

```python
        form = ConfiguracionEmpresaForm(request.POST, instance=configuracion)
```

por:

```python
        form = ConfiguracionEmpresaForm(request.POST, request.FILES, instance=configuracion)
```

- [ ] **Step 4: Agregar `enctype` y campo de subida con vista previa en el template**

En `templates/gestion/configuracion/empresa.html:52`, cambiar:

```html
                    <form method="post" novalidate>
```

por:

```html
                    <form method="post" enctype="multipart/form-data" novalidate>
```

Después de la sección "Ubicación institucional" (después del `</section>` de la línea 173, antes del `<div class="border-top pt-4 mt-4">` de la línea 175), agregar una nueva sección:

```html
                        <section class="mb-4">
                            <h6 class="text-muted text-uppercase fw-semibold small mb-3">
                                <i class="fas fa-image text-primary me-2"></i>Logo de la empresa
                            </h6>
                            <div class="row g-3 align-items-center">
                                {% if configuracion and configuracion.logo %}
                                <div class="col-auto">
                                    <img src="{{ configuracion.logo.url }}" alt="Logo actual" style="height: 60px; width: auto; object-fit: contain; background: white; border-radius: 8px; padding: 6px;">
                                </div>
                                {% endif %}
                                <div class="col">
                                    <label for="{{ form.logo.id_for_label }}" class="form-label fw-semibold">
                                        {{ form.logo.label }}
                                    </label>
                                    {{ form.logo|add_class:'form-control' }}
                                    <div class="form-text">PNG, SVG o JPG. Se usará en el login y el menú superior.</div>
                                    {% if form.logo.errors %}
                                        <div class="alert alert-danger mt-2 mb-0 py-2">
                                            <i class="fas fa-exclamation-circle me-2"></i>{{ form.logo.errors }}
                                        </div>
                                    {% endif %}
                                </div>
                            </div>
                        </section>
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `python manage.py test gestion.tests.tests_configuracion_empresa_vista_logo -v 2`
Expected: `OK` (2 tests)

- [ ] **Step 6: Commit**

```bash
git add gestion/views/configuracion.py templates/gestion/configuracion/empresa.html gestion/tests/tests_configuracion_empresa_vista_logo.py
git commit -m "feat: permitir subir el logo de la empresa desde el panel de configuracion"
```

---

### Task 4: Logo real y fondo decorativo en el login

**Files:**
- Modify: `templates/registration/login.html`
- Test: `gestion/tests/tests_login_branding.py`

**Interfaces:**
- Consumes: `empresa_config.logo` (Tarea 2, disponible globalmente vía `gestion/context_processors.py:empresa_config`), asset estático `gestion/img/avenida-chile-icono.svg` (Tarea 1).

- [ ] **Step 1: Escribir el test que falla**

Crear `gestion/tests/tests_login_branding.py`:

```python
import base64
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from gestion.models import ConfiguracionEmpresa

PNG_1PX = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


class LoginBrandingTest(TestCase):
    def test_login_muestra_logo_por_defecto_sin_configuracion(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'logo-chip')
        self.assertContains(response, 'avenida-chile-icono.svg')

    def test_login_muestra_figuras_decorativas_de_fondo(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'bg-shape')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class LoginBrandingConLogoPersonalizadoTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_login_usa_logo_subido_cuando_existe(self):
        logo_file = SimpleUploadedFile('logo.png', PNG_1PX, content_type='image/png')
        ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa Con Logo',
            nit_empresa='900123456-3',
            representante_legal='Juana Ejemplo',
            activo=True,
            logo=logo_file,
        )
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'empresa/logos/logo')
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `python manage.py test gestion.tests.tests_login_branding -v 2`
Expected: FAIL — ninguna de las 3 aserciones (`logo-chip`, `bg-shape`, `empresa/logos/logo`) existe todavía en `login.html`.

- [ ] **Step 3: Reemplazar los estilos CSS del logo por el patrón "chip" y agregar las figuras de fondo**

En `templates/registration/login.html`, reemplazar el bloque de estilos (líneas 19-25, la regla `body`) por:

```css
        body {
            background: linear-gradient(135deg, var(--avenida-dark) 0%, #34495e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .bg-shape {
            position: fixed;
            width: 380px;
            height: auto;
            opacity: 0.15;
            pointer-events: none;
            z-index: 0;
        }
        .bg-shape-tl { top: -80px; left: -80px; transform: rotate(-8deg); }
        .bg-shape-tr { top: -100px; right: -90px; transform: rotate(15deg); }
        .bg-shape-bl { bottom: -100px; left: -70px; transform: rotate(20deg); }
        .bg-shape-br { bottom: -90px; right: -80px; transform: rotate(-15deg); }
```

Reemplazar el bloque de estilos `.login-container` (líneas 27-34) por (agregando `position` y `z-index`):

```css
        .login-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
            max-width: 900px;
            width: 100%;
            position: relative;
            z-index: 1;
        }
```

Reemplazar el bloque de estilos `.logo-squares` y `.square-color` (líneas 59-70) por:

```css
        .logo-chip {
            background: white;
            border-radius: 16px;
            padding: 12px 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 1rem;
        }

        .logo-chip img {
            height: 80px;
            width: auto;
            object-fit: contain;
            display: block;
        }
```

- [ ] **Step 4: Agregar las figuras decorativas al `<body>` y reemplazar el logo del panel izquierdo**

Cambiar la apertura del `<body>` (línea 98) de:

```html
<body>
```

a:

```html
<body>
    <img src="{% static 'gestion/img/avenida-chile-icono.svg' %}" class="bg-shape bg-shape-tl" alt="">
    <img src="{% static 'gestion/img/avenida-chile-icono.svg' %}" class="bg-shape bg-shape-tr" alt="">
    <img src="{% static 'gestion/img/avenida-chile-icono.svg' %}" class="bg-shape bg-shape-bl" alt="">
    <img src="{% static 'gestion/img/avenida-chile-icono.svg' %}" class="bg-shape bg-shape-br" alt="">
```

Reemplazar el bloque `<div class="logo-squares">...</div>` (líneas 105-111) por:

```html
                        <div class="logo-chip">
                            <img src="{% if empresa_config and empresa_config.logo %}{{ empresa_config.logo.url }}{% else %}{% static 'gestion/img/avenida-chile-icono.svg' %}{% endif %}" alt="Logo {% if empresa_config %}{{ empresa_config.nombre_empresa }}{% else %}Centro Comercial Avenida de Chile{% endif %}">
                        </div>
```

- [ ] **Step 5: Ejecutar los tests y confirmar que pasan**

Run: `python manage.py test gestion.tests.tests_login_branding -v 2`
Expected: `OK` (3 tests)

- [ ] **Step 6: Commit**

```bash
git add templates/registration/login.html gestion/tests/tests_login_branding.py
git commit -m "feat: usar el logo real y agregar fondo decorativo de marca en el login"
```

---

### Task 5: Logo real en el navbar

**Files:**
- Modify: `templates/base.html`
- Test: `gestion/tests/tests_navbar_branding.py`

**Interfaces:**
- Consumes: `empresa_config.logo` (Tarea 2), asset estático `gestion/img/avenida-chile-icono.svg` (Tarea 1).

- [ ] **Step 1: Escribir el test que falla**

Crear `gestion/tests/tests_navbar_branding.py`:

```python
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class NavbarBrandingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='navuser', password='testpass123')
        self.client.force_login(self.user)

    def test_navbar_muestra_logo_chip(self):
        response = self.client.get(reverse('gestion:dashboard'))
        self.assertContains(response, 'navbar-logo-chip')
        self.assertContains(response, 'avenida-chile-icono.svg')
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `python manage.py test gestion.tests.tests_navbar_branding -v 2`
Expected: FAIL — `navbar-logo-chip` no existe todavía en `base.html`.

- [ ] **Step 3: Agregar el estilo del chip del navbar**

En `templates/base.html`, después de la regla `.navbar-brand` (líneas 58-61), agregar:

```css
        .navbar-logo-chip {
            background: white;
            border-radius: 10px;
            padding: 6px 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .navbar-logo-chip img {
            height: 40px;
            width: auto;
            object-fit: contain;
            display: block;
        }
```

- [ ] **Step 4: Reemplazar el bloque de cuadros por el logo real**

Reemplazar el bloque (líneas 213-222):

```html
                    <div class="me-3">
                        <div class="d-flex">
                            <div class="square-color" style="background-color: var(--avenida-green); width: 28px; height: 28px; margin: 2px; border-radius: 3px;"></div>
                            <div class="square-color" style="background-color: var(--avenida-orange); width: 28px; height: 28px; margin: 2px; border-radius: 3px;"></div>
                        </div>
                        <div class="d-flex">
                            <div class="square-color" style="background-color: var(--avenida-cyan); width: 28px; height: 28px; margin: 2px; border-radius: 3px;"></div>
                            <div class="square-color" style="background-color: var(--avenida-magenta); width: 28px; height: 28px; margin: 2px; border-radius: 3px;"></div>
                        </div>
                    </div>
```

por:

```html
                    <div class="navbar-logo-chip me-3">
                        <img src="{% if empresa_config and empresa_config.logo %}{{ empresa_config.logo.url }}{% else %}{% static 'gestion/img/avenida-chile-icono.svg' %}{% endif %}" alt="Logo {% if empresa_config %}{{ empresa_config.nombre_empresa }}{% else %}Centro Comercial Avenida de Chile{% endif %}">
                    </div>
```

Confirmar que `templates/base.html` ya tiene `{% load static %}` en la línea 1 (no se necesita agregarlo).

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `python manage.py test gestion.tests.tests_navbar_branding -v 2`
Expected: `OK` (1 test)

- [ ] **Step 6: Ejecutar toda la suite de tests de branding junta para confirmar que no hay regresiones**

Run: `python manage.py test gestion.tests.tests_configuracion_empresa_logo gestion.tests.tests_configuracion_empresa_vista_logo gestion.tests.tests_login_branding gestion.tests.tests_navbar_branding -v 2`
Expected: `OK` (8 tests en total)

- [ ] **Step 7: Commit**

```bash
git add templates/base.html gestion/tests/tests_navbar_branding.py
git commit -m "feat: usar el logo real de la empresa en el navbar"
```
