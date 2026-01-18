# 🔐 Sistema de Autenticación y Seguridad

## Descripción General

El sistema ahora incluye un sistema completo de autenticación basado en el sistema de usuarios de Django, con mejoras de seguridad para producción.

## 🎯 Características Implementadas

### 1. Login/Logout
- ✅ Página de login personalizada con branding corporativo
- ✅ Protección de todas las vistas con `@login_required`
- ✅ Redirección automática a login si no autenticado
- ✅ Mensajes amigables de error y confirmación

### 2. Decoradores Personalizados

Se crearon dos decoradores en `gestion/decorators.py`:

#### `@login_required_custom`
```python
from gestion.decorators import login_required_custom

@login_required_custom
def mi_vista(request):
    # Solo usuarios autenticados pueden acceder
    pass
```

#### `@admin_required`
```python
from gestion.decorators import admin_required

@admin_required
def configuracion_empresa(request):
    # Solo usuarios staff/admin pueden acceder
    pass
```

### 3. Niveles de Acceso

#### Usuario Normal (Empleado)
- Ver dashboard
- Ver lista de contratos
- Ver detalles de contratos
- Gestionar pólizas
- Crear/editar contratos, arrendatarios y locales

#### Usuario Admin (Staff)
- Todo lo anterior
- Acceso a configuración de empresa
- Acceso al panel de administración de Django
- Eliminar contratos

## 📋 Aplicar Protección a las Vistas

Necesitas agregar los decoradores a todas las vistas en `gestion/views.py`:

```python
from gestion.decorators import login_required_custom, admin_required

# Vistas para todos los usuarios autenticados
@login_required_custom
def dashboard(request):
    ...

@login_required_custom
def lista_contratos(request):
    ...

@login_required_custom
def detalle_contrato(request, contrato_id):
    ...

# Vistas solo para administradores
@admin_required
def configuracion_empresa(request):
    ...

@admin_required
def eliminar_contrato(request, contrato_id):
    ...
```

## 👥 Gestión de Usuarios

### Crear usuarios desde Django Admin

1. Accede a `/admin/`
2. Ve a "Usuarios" → "Añadir usuario"
3. Configura:
   - **Username**: nombre de usuario
   - **Password**: contraseña segura
   - **Permisos**:
     - `is_staff`: marcado para administradores
     - `is_active`: siempre marcado
     - Grupos (opcional): puedes crear grupos como "Empleados", "Administradores"

### Crear usuarios desde terminal

```bash
# Superusuario (acceso total)
python manage.py createsuperuser

# Usuario normal (desde Django shell)
python manage.py shell
```

```python
from django.contrib.auth.models import User

# Crear usuario empleado
user = User.objects.create_user(
    username='empleado1',
    email='empleado1@avenidachile.com',
    password='contraseña_segura',
    first_name='Juan',
    last_name='Pérez'
)
user.save()

# Crear usuario administrador
admin = User.objects.create_user(
    username='admin1',
    email='admin1@avenidachile.com',
    password='contraseña_segura',
    first_name='María',
    last_name='García',
    is_staff=True
)
admin.save()
```

## 🔒 Configuraciones de Seguridad

### En Desarrollo (`settings.py`)
```python
DEBUG = True
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

### En Producción (`settings_production.py`)
```python
DEBUG = False
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Seguridad adicional
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

## 🎨 Personalización del Template de Login

El template está en `templates/registration/login.html` y incluye:
- Logo y branding corporativo
- Colores de Avenida Chile
- Diseño responsive
- Mensajes de error amigables
- Iconos de Font Awesome

## 🔐 Mejores Prácticas

### 1. Contraseñas Seguras
Django incluye validadores de contraseñas por defecto:
- Mínimo 8 caracteres
- No puede ser demasiado similar al usuario
- No puede ser una contraseña común
- No puede ser completamente numérica

### 2. Sesiones
- Las sesiones expiran después de 2 semanas por defecto
- Se pueden configurar en settings:

```python
SESSION_COOKIE_AGE = 86400  # 24 horas en segundos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Cerrar sesión al cerrar navegador
```

### 3. Logout
Agregar botón de logout en `templates/base.html`:

```html
<div class="navbar-nav ms-auto">
    {% if user.is_authenticated %}
        <span class="nav-link">
            <i class="fas fa-user"></i> {{ user.username }}
        </span>
        <a class="nav-link" href="{% url 'logout' %}">
            <i class="fas fa-sign-out-alt"></i> Cerrar Sesión
        </a>
    {% endif %}
</div>
```

## 📊 Auditoría de Accesos (Opcional)

Para implementar auditoría:

```python
# En cada vista importante
import logging
logger = logging.getLogger('gestion')

@login_required_custom
def eliminar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)
    logger.info(f"Usuario {request.user.username} eliminó contrato {contrato.num_contrato}")
    ...
```

## 🚫 Protección contra Ataques

### CSRF Protection
Django incluye protección CSRF automáticamente. Asegúrate de incluir en todos los formularios:
```html
<form method="post">
    {% csrf_token %}
    ...
</form>
```

### Throttling de Login (Opcional)
Para prevenir ataques de fuerza bruta, considera instalar:
```bash
pip install django-axes
```

## 🔄 Recuperación de Contraseña (Opcional)

Para implementar recuperación de contraseña por email:

1. Configurar email en `settings_production.py`
2. Agregar URLs en `contratos/urls.py`:

```python
path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
```

3. Crear templates personalizados en `templates/registration/`

## ✅ Checklist de Implementación

- [ ] Decoradores creados en `gestion/decorators.py`
- [ ] Template de login creado en `templates/registration/login.html`
- [ ] URLs de login/logout agregadas a `contratos/urls.py`
- [ ] Decoradores aplicados a todas las vistas
- [ ] LOGIN_URL configurado en settings
- [ ] Botón de logout agregado al navbar
- [ ] Superusuario creado
- [ ] Usuarios de prueba creados
- [ ] Sistema probado en desarrollo
- [ ] Configuraciones de seguridad verificadas para producción

## 🎉 Resultado

Después de implementar todo:
1. Todas las páginas requieren login
2. Login con diseño corporativo
3. Mensajes de error amigables
4. Sesiones seguras
5. Protección CSRF automática
6. Diferentes niveles de acceso
7. Logs de auditoría (opcional)

---

**Última actualización:** Octubre 2025
**Compatible con:** Django 5.0+

