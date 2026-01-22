# Guía para Actualizar el Repositorio de GitHub

Esta guía explica cómo actualizar el repositorio de GitHub con los cambios realizados localmente.

## Requisitos Previos

- Git instalado en tu sistema
- Acceso al repositorio de GitHub
- Credenciales configuradas (usuario y token/clave SSH)

## Proceso de Actualización

### 1. Verificar el Estado del Repositorio

Antes de hacer cambios, verifica qué archivos han sido modificados:

```bash
git status
```

Este comando mostrará:
- Archivos modificados (`modified`)
- Archivos nuevos sin rastrear (`untracked`)
- Archivos eliminados (`deleted`)

### 2. Agregar Archivos al Área de Preparación (Staging)

#### Agregar un archivo específico:

```bash
git add ruta/al/archivo.py
```

#### Agregar todos los archivos modificados:

```bash
git add .
```

#### Agregar solo archivos modificados (no nuevos):

```bash
git add -u
```

**Ejemplo práctico:**
```bash
# Agregar solo el archivo modificado
git add gestion/utils_otrosi.py

# O agregar todos los cambios
git add .
```

### 3. Crear un Commit

Un commit es un punto de guardado con un mensaje descriptivo:

```bash
git commit -m "Descripción clara de los cambios realizados"
```

**Buenas prácticas para mensajes de commit:**
- Usar español o inglés de forma consistente
- Ser descriptivo pero conciso
- Usar el modo imperativo (ej: "Corregir bug" en lugar de "Corregido bug")
- Incluir el número de issue/ticket si aplica

**Ejemplos de mensajes:**
```bash
# Corrección de bug
git commit -m "Corregir bug: considerar OtroSí aprobados con fechas futuras al filtrar pólizas requeridas"

# Nueva funcionalidad
git commit -m "Agregar validación de fechas en formulario de contratos"

# Mejora de código
git commit -m "Refactorizar función de cálculo de vigencias de pólizas"

# Actualización de documentación
git commit -m "Actualizar documentación de despliegue en PythonAnywhere"
```

### 4. Subir Cambios a GitHub

Una vez creado el commit, sube los cambios al repositorio remoto:

```bash
git push origin main
```

**Nota:** Si tu rama principal tiene otro nombre (como `master`), usa ese nombre:
```bash
git push origin master
```

### 5. Verificar que los Cambios se Subieron

Puedes verificar en GitHub.com que tus cambios están en el repositorio, o ejecutar:

```bash
git log --oneline -5
```

Esto mostrará los últimos 5 commits, incluyendo el que acabas de crear.

## Flujo Completo de Ejemplo

```bash
# 1. Verificar cambios
git status

# 2. Agregar archivos modificados
git add gestion/utils_otrosi.py

# 3. Crear commit
git commit -m "Corregir bug: considerar OtroSí aprobados con fechas futuras al filtrar pólizas requeridas"

# 4. Subir a GitHub
git push origin main

# 5. Verificar
git log --oneline -3
```

## Solución de Problemas Comunes

### Error: "Git no está reconocido"

**Problema:** El comando `git` no se encuentra en PowerShell.

**Solución 1:** Usar la ruta completa de Git:
```powershell
& "C:\Program Files\Git\bin\git.exe" status
```

**Solución 2:** Usar Git Bash en lugar de PowerShell.

**Solución 3:** Agregar Git al PATH del sistema.

### Error: "No se puede hacer push porque hay cambios remotos"

**Problema:** Otra persona o tú mismo desde otra máquina subió cambios.

**Solución:** Hacer pull primero, luego push:
```bash
git pull origin main
# Resolver conflictos si los hay
git push origin main
```

### Error: "Autenticación fallida"

**Problema:** Las credenciales de GitHub no están configuradas o expiraron.

**Solución 1:** Configurar credenciales:
```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-email@ejemplo.com"
```

**Solución 2:** Usar un token de acceso personal en lugar de contraseña:
1. Ir a GitHub → Settings → Developer settings → Personal access tokens
2. Generar un nuevo token
3. Usarlo como contraseña al hacer push

### Error: "Working tree is dirty"

**Problema:** Hay cambios sin guardar que entran en conflicto.

**Solución:** Hacer commit o descartar los cambios:
```bash
# Opción 1: Guardar cambios
git add .
git commit -m "Mensaje"

# Opción 2: Descartar cambios (¡CUIDADO!)
git restore archivo.py
```

## Comandos Útiles Adicionales

### Ver diferencias antes de hacer commit:

```bash
git diff
```

### Ver historial de commits:

```bash
git log --oneline --graph --all
```

### Deshacer el último commit (manteniendo cambios):

```bash
git reset --soft HEAD~1
```

### Ver qué archivos están en staging:

```bash
git status --short
```

### Agregar y hacer commit en un solo paso:

```bash
git commit -am "Mensaje del commit"
```

**Nota:** Esto solo funciona con archivos ya rastreados por Git.

## Buenas Prácticas

1. **Hacer commits frecuentes:** No esperes a tener muchos cambios. Haz commits pequeños y frecuentes.

2. **Mensajes descriptivos:** Un buen mensaje de commit ayuda a entender qué cambió y por qué.

3. **Revisar antes de hacer push:** Usa `git diff` para revisar los cambios antes de hacer commit.

4. **No hacer commit de archivos sensibles:** Nunca subas archivos `.env`, contraseñas, o información sensible.

5. **Usar `.gitignore`:** Asegúrate de que archivos temporales, logs, y archivos de entorno estén en `.gitignore`.

6. **Hacer pull antes de push:** Si trabajas en equipo, siempre haz `git pull` antes de `git push` para evitar conflictos.

## Archivos que NO deben subirse a GitHub

Asegúrate de que estos archivos estén en `.gitignore`:

- `.env` (variables de entorno)
- `db.sqlite3` (base de datos local)
- `__pycache__/` (archivos compilados de Python)
- `*.pyc` (archivos compilados)
- `venv/` o `env/` (entornos virtuales)
- `logs/` (archivos de log)
- `media/` (archivos subidos por usuarios)
- `staticfiles/` (archivos estáticos compilados)

## Siguiente Paso: Actualizar Despliegue

Después de actualizar GitHub, sigue la guía de despliegue:

1. En PythonAnywhere, ejecuta `git pull origin main`
2. Verifica que no haya errores con `python manage.py check`
3. Recarga la aplicación web desde el panel de PythonAnywhere

Ver: `docs/deployment/DEPLOYMENT_DESDE_GITHUB.md` para más detalles.
