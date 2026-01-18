# 📋 Preguntas y Respuestas - Entrevista con Cliente

## Documento de Preparación para Reunión Técnica y Operativa

---

## 🏗️ ARQUITECTURA Y TECNOLOGÍAS

### P: ¿Qué tecnologías utiliza el sistema en el frontend y backend?

**R:** 
- **Backend:** Django 5.0+ (Python 3.10+)
- **Frontend:** Templates Django con Bootstrap 5.3 y Font Awesome 6.0
- **Base de Datos:** SQLite (desarrollo y producción inicial), compatible con MySQL/PostgreSQL
- **Servidor Web:** Gunicorn para producción
- **Librerías principales:**
  - Pillow (manejo de imágenes)
  - openpyxl (exportación a Excel)
  - reportlab (generación de PDFs)
  - python-dateutil (manejo de fechas)
  - python-decouple (variables de entorno)

### P: ¿Por qué Django y no otro framework?

**R:** 
- Django es robusto y maduro, ideal para aplicaciones empresariales
- Sistema de autenticación integrado y seguro
- ORM potente que facilita el mantenimiento
- Panel de administración incluido
- Excelente documentación y comunidad
- Seguridad por defecto (CSRF, XSS, SQL injection)
- Escalable y probado en producción

### P: ¿El sistema es monolítico o tiene arquitectura de microservicios?

**R:** 
- Arquitectura monolítica tradicional de Django, que es la más adecuada para este proyecto porque:
  - Proyecto de tamaño mediano (15 usuarios máximo)
  - Facilita el mantenimiento y despliegue
  - Menor complejidad operativa
  - Costos más bajos de infraestructura
  - Si en el futuro se requiere escalar, se puede modularizar sin problemas

---

## 🚀 DESPLIEGUE Y SERVIDOR

### P: ¿Dónde se desplegará el sistema y qué requisitos tiene el servidor?

**R:** 
- **Plataforma recomendada:** PythonAnywhere (inicialmente)
- **Requisitos mínimos:**
  - Python 3.10 o superior
  - 512 MB RAM (suficiente para hasta 15 usuarios)
  - 1 GB espacio en disco
  - Acceso a internet para validación de licencias
- **Alternativas:** Railway, Render, o VPS propio (DigitalOcean, AWS, etc.)

### P: ¿Cómo se accederá al sistema en producción?

**R:** 
- **URL de acceso:** `https://[dominio].pythonanywhere.com` (o dominio personalizado)
- **Protocolo:** HTTPS (SSL/TLS automático)
- **Acceso:** Navegador web (Chrome, Firefox, Edge, Safari)
- **No requiere instalación de software adicional** en los equipos de los usuarios

### P: ¿Cuánto tiempo toma el despliegue?

**R:** 
- **Despliegue inicial:** 2-3 horas
  - Configuración de servidor: 45 min
  - Configuración de aplicación: 30 min
  - Migración de datos: 30 min
  - Pruebas y verificación: 45 min
- **Actualizaciones futuras:** 15-30 minutos (dependiendo de la complejidad)

### P: ¿El sistema requiere algún servicio externo o API?

**R:** 
- **Sí, requiere:**
  - Conexión a internet para validación de licencias (Firebase Cloud Functions)
  - URL: `https://us-central1-app-contable-licencias.cloudfunctions.net/activateLicense`
- **No requiere:**
  - Servicios de email externos (puede configurarse opcionalmente)
  - APIs de terceros para funcionalidades core
  - Servicios de pago

### P: ¿Cómo se manejan las actualizaciones del sistema?

**R:** 
- **Proceso de actualización:**
  1. Desarrollo y pruebas en entorno local
  2. Commit a repositorio Git
  3. Pull en servidor de producción
  4. Aplicar migraciones de base de datos si hay cambios
  5. Recargar aplicación (botón Reload en PythonAnywhere)
- **Tiempo de inactividad:** Menos de 1 minuto por actualización
- **Backup automático:** Se recomienda hacer backup antes de cada actualización

---

## 🔐 SEGURIDAD

### P: ¿Qué medidas de seguridad tiene implementadas el sistema?

**R:** 
- **Autenticación:**
  - Sistema de login/logout con usuarios y contraseñas
  - Protección de todas las rutas con decoradores `@login_required`
  - Control de acceso por roles (usuario normal vs administrador)
  
- **Protección contra ataques:**
  - CSRF (Cross-Site Request Forgery) habilitado por defecto
  - XSS (Cross-Site Scripting) protegido con filtros automáticos
  - SQL Injection protegido por el ORM de Django
  - Clickjacking protegido con X-Frame-Options
  
- **Configuración de producción:**
  - HTTPS obligatorio (SECURE_SSL_REDIRECT)
  - Cookies seguras (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
  - SECRET_KEY en variables de entorno (no en código)
  - DEBUG deshabilitado en producción
  - Logging de errores configurado

### P: ¿Cómo se protegen los datos sensibles?

**R:** 
- **Variables de entorno:** SECRET_KEY, credenciales en archivo `.env` (no en código)
- **Base de datos:** SQLite con permisos de archivo del sistema operativo
- **Contraseñas:** Hasheadas con algoritmo PBKDF2 de Django (no se almacenan en texto plano)
- **Sesiones:** Cookies seguras con expiración automática
- **Backups:** Se recomienda encriptar backups si contienen información sensible

### P: ¿El sistema cumple con normativas de protección de datos?

**R:** 
- **Implementado:**
  - Control de acceso por usuarios
  - Auditoría de cambios (campos creado_por, modificado_por, fechas)
  - Logs de errores para trazabilidad
  
- **Recomendaciones adicionales:**
  - Política de privacidad y términos de uso
  - Backup encriptado de datos
  - Plan de respuesta a incidentes
  - Documentación de procedimientos de seguridad

### P: ¿Cómo se previenen ataques de fuerza bruta en el login?

**R:** 
- **Actual:** Django maneja sesiones y tiene protección básica
- **Recomendación futura:** Implementar rate limiting (límite de intentos de login por IP)
- **Medidas actuales:**
  - Contraseñas con validación de complejidad
  - Sesiones con expiración automática
  - Logs de intentos de acceso

---

## 👥 ACCESO Y USUARIOS

### P: ¿Cómo se gestionan los usuarios del sistema?

**R:** 
- **Creación de usuarios:**
  - Desde el panel de administración Django (`/admin/`)
  - Desde línea de comandos con `python manage.py createsuperuser`
  - Script personalizado para crear usuarios desarrolladores
  
- **Tipos de usuarios:**
  - **Usuario normal:** Acceso a funcionalidades operativas (contratos, pólizas, dashboard)
  - **Usuario administrador (staff):** Acceso completo incluyendo configuración y panel admin
  
- **Permisos:**
  - Control granular por vistas usando decoradores
  - Posibilidad de crear grupos de usuarios con permisos específicos

### P: ¿Cuántos usuarios simultáneos puede soportar el sistema?

**R:** 
- **Configuración actual:** Hasta 10 usuarios simultáneos cómodamente
- **Límite teórico:** 15 usuarios totales (según especificaciones del proyecto)
- **Base de datos SQLite:** Adecuada para esta carga
- **Si se requiere más:** Migración a MySQL/PostgreSQL y optimización de servidor

### P: ¿Cómo se recupera el acceso si se olvida la contraseña?

**R:** 
- **Opción 1:** Administrador puede resetear contraseña desde `/admin/`
- **Opción 2:** Implementar sistema de recuperación de contraseña por email (requiere configuración SMTP)
- **Opción 3:** Contactar al administrador del sistema para reset manual

### P: ¿Se puede integrar con Active Directory o LDAP?

**R:** 
- **No implementado actualmente**
- **Posible implementación futura:** Sí, usando librerías como `django-auth-ldap` o `django-python3-ldap`
- **Requisitos:** Servidor LDAP/Active Directory accesible desde el servidor de producción

---

## 📊 BASE DE DATOS

### P: ¿Qué base de datos utiliza el sistema?

**R:** 
- **Actual:** SQLite (archivo `db.sqlite3`)
- **Ventajas para este proyecto:**
  - No requiere servidor de base de datos separado
  - Configuración simple
  - Adecuada para hasta 15 usuarios y carga moderada
  - Backup simple (copiar archivo)
  
- **Migración futura:** Compatible con MySQL o PostgreSQL si se requiere

### P: ¿Cómo se realizan los backups de la base de datos?

**R:** 
- **Método 1 - Backup manual:**
  ```bash
  python manage.py dumpdata > backup_$(date +%Y%m%d).json
  ```
  
- **Método 2 - Backup del archivo SQLite:**
  ```bash
  cp db.sqlite3 backup_db_$(date +%Y%m%d).sqlite3
  ```
  
- **Automatización implementada:**
  - Comando Django: `python manage.py backup_database`
  - Scripts para Linux (`backup_daily.sh`) y Windows (`backup_daily.bat`)
  - Configuración de cron job o Tareas Programadas
  - Limpieza automática de backups antiguos (configurable, por defecto 30 días)
  - Soporte para backup JSON y SQLite simultáneamente
  
- **Almacenamiento:**
  - Directorio local: `backups/` (por defecto)
  - Opción de sincronización remota (rclone, rsync, S3, etc.)
  - Ver documentación completa: `docs/GUIA_BACKUPS_AUTOMATICOS.md`

### P: ¿Qué pasa si la base de datos se corrompe?

**R:** 
- **Prevención:**
  - Backups regulares
  - Transacciones atómicas en Django
  - Validación de datos en modelos
  
- **Recuperación:**
  1. Detener aplicación
  2. Restaurar backup más reciente
  3. Verificar integridad
  4. Reiniciar aplicación
  
- **Tiempo de recuperación estimado:** 15-30 minutos (dependiendo del tamaño de backup)

### P: ¿El sistema soporta migraciones de esquema de base de datos?

**R:** 
- **Sí, completamente:**
  - Django ORM genera migraciones automáticamente
  - Comando: `python manage.py makemigrations`
  - Aplicación: `python manage.py migrate`
  - Versionado de esquema en archivos de migración
  - Reversión posible si es necesario

---

## 🔑 LICENCIAS Y ACTIVACIÓN

### P: ¿Cómo funciona el sistema de licencias?

**R:** 
- **Validación:** Se conecta a Firebase Cloud Functions para verificar licencia
- **Proceso:**
  1. Usuario ingresa clave de licencia al iniciar sesión
  2. Sistema valida con servidor remoto
  3. Si es válida, permite acceso
  4. Verificación periódica durante uso
  
- **Datos validados:**
  - Clave de licencia
  - Fingerprint del servidor
  - Versión del software
  - Estado de la licencia (activa, expirada, revocada)

### P: ¿Qué pasa si no hay conexión a internet para validar la licencia?

**R:** 
- **Comportamiento actual:** El sistema requiere conexión para validar licencia inicial
- **Recomendación:** Implementar modo offline con validación local y sincronización periódica
- **Workaround temporal:** Modo de desarrollo para pruebas sin validación

### P: ¿Se puede usar el sistema sin licencia para desarrollo/pruebas?

**R:** 
- **Sí, hay modo de desarrollo:**
  - Configuración separada (`settings.py` vs `settings_production.py`)
  - Middleware de licencia puede deshabilitarse en desarrollo
  - Scripts de desarrollo disponibles

---

## ⚡ RENDIMIENTO Y ESCALABILIDAD

### P: ¿Cuál es el tiempo de respuesta del sistema?

**R:** 
- **Páginas estándar:** < 500ms (dashboard, listas)
- **Operaciones complejas:** < 2 segundos (cálculos IPC, exportaciones)
- **Factores que afectan:**
  - Carga del servidor
  - Tamaño de base de datos
  - Complejidad de consultas
  - Conexión a internet del usuario

### P: ¿El sistema puede escalar si crece el número de usuarios?

**R:** 
- **Escalabilidad horizontal:**
  - Migrar a MySQL/PostgreSQL para más usuarios concurrentes
  - Aumentar recursos del servidor (RAM, CPU)
  - Implementar caché (Redis/Memcached) si es necesario
  
- **Escalabilidad vertical:**
  - Optimizar consultas de base de datos
  - Implementar paginación en listas grandes
  - Comprimir respuestas HTTP
  
- **Límite actual:** 15 usuarios (según especificaciones)
- **Límite con optimizaciones:** 50-100 usuarios con MySQL y servidor adecuado

### P: ¿Hay algún sistema de caché implementado?

**R:** 
- **No implementado actualmente** (no es necesario para 15 usuarios)
- **Implementación futura posible:**
  - Redis para caché de sesiones
  - Caché de consultas frecuentes
  - Caché de archivos estáticos (CDN)

---

## 🛠️ MANTENIMIENTO Y SOPORTE

### P: ¿Qué mantenimiento requiere el sistema?

**R:** 
- **Mantenimiento regular:**
  - Backups diarios de base de datos
  - Actualizaciones de seguridad de Django (trimestrales)
  - Revisión de logs de errores (semanal)
  - Limpieza de archivos temporales (mensual)
  
- **Mantenimiento preventivo:**
  - Monitoreo de espacio en disco
  - Verificación de rendimiento
  - Actualización de dependencias (anual)

### P: ¿Cómo se monitorean los errores del sistema?

**R:** 
- **Logging configurado:**
  - Archivo de logs: `logs/django_errors.log`
  - Nivel de logging: ERROR e INFO
  - Formato: timestamp, nivel, módulo, mensaje
  
- **Monitoreo:**
  - Revisión manual de logs
  - Notificaciones por email (requiere configuración SMTP)
  - Dashboard de PythonAnywhere muestra errores del servidor

### P: ¿Qué soporte técnico se proporciona?

**R:** 
- **Soporte incluido:**
  - Documentación completa del sistema
  - Guías de instalación y despliegue
  - Scripts de mantenimiento
  - Código comentado y estructurado
  
- **Soporte adicional (consultar):**
  - Soporte técnico por horas
  - Actualizaciones y mejoras
  - Capacitación de usuarios
  - Mantenimiento preventivo

### P: ¿Cómo se documentan los cambios y actualizaciones?

**R:** 
- **Control de versiones:** Git con commits descriptivos
- **Documentación:** Carpeta `docs/` con guías técnicas
- **Changelog:** Se puede mantener archivo CHANGELOG.md
- **Código:** Comentarios en funciones complejas

---

## 📱 FUNCIONALIDADES OPERATIVAS

### P: ¿Qué funcionalidades principales tiene el sistema?

**R:** 
- **Gestión de Contratos:**
  - Crear, editar, eliminar contratos
  - Contratos simples (canon fijo) y complejos (híbridos, periodos de gracia)
  - Cálculo automático de cánones variables
  
- **Gestión de Pólizas:**
  - Seguimiento de pólizas de cumplimiento, RCE, arrendamiento
  - Alertas de vencimiento
  - Estados automáticos (vigente, por vencer, vencida)
  
- **Dashboard de Alertas:**
  - Vencimientos de contratos (60 días)
  - Pólizas vencidas o por vencer
  - Preavisos de renovación automática
  - Recordatorios de reporte de ventas
  
- **Cálculo IPC:**
  - Configuración de IPC histórico
  - Cálculo automático de ajustes por IPC
  - Diferentes modalidades (anual, mes específico)
  
- **Otro Sí:**
  - Modificaciones contractuales
  - Actualización automática de contratos
  
- **Exportaciones:**
  - Excel (openpyxl)
  - PDF (reportlab)

### P: ¿El sistema genera reportes automáticos?

**R:** 
- **Sí:**
  - Dashboard con alertas en tiempo real
  - Exportación a Excel de listados
  - Exportación a PDF de contratos
  
- **Futuro:**
  - Reportes programados por email
  - Reportes personalizados
  - Gráficos y estadísticas

### P: ¿Se puede integrar con otros sistemas?

**R:** 
- **APIs REST:** No implementado, pero posible con Django REST Framework
- **Exportación de datos:** Sí, formato Excel y JSON
- **Importación:** Posible implementar con scripts personalizados
- **Integración contable:** Posible mediante exportación de datos estructurados

---

## 💰 COSTOS Y RECURSOS

### P: ¿Cuáles son los costos de infraestructura?

**R:** 
- **PythonAnywhere:**
  - Plan gratuito: Para desarrollo/pruebas
  - Plan Hacker: $5/mes (producción pequeña)
  - Plan Web Developer: $12/mes (producción mediana)
  - Dominio propio: $5/mes adicional
  
- **Alternativas:**
  - Railway: $5 crédito mensual, luego pago por uso
  - Render: Gratis (con limitaciones) o $7/mes
  - VPS: $5-10/mes (DigitalOcean, Linode)

### P: ¿Qué recursos de servidor se necesitan?

**R:** 
- **Mínimo:**
  - 512 MB RAM
  - 1 GB espacio en disco
  - 1 CPU core
  
- **Recomendado:**
  - 1 GB RAM
  - 5 GB espacio en disco
  - 1-2 CPU cores

### P: ¿Hay costos de licencias de software?

**R:** 
- **No:**
  - Django: Open source (BSD license)
  - Python: Open source
  - Todas las dependencias: Open source
  - Solo requiere licencia del sistema (validación Firebase)

---

## 🔄 MIGRACIÓN Y ACTUALIZACIONES

### P: ¿Cómo se migran los datos existentes al sistema?

**R:** 
- **Métodos disponibles:**
  1. Importación manual desde Excel/CSV (requiere script)
  2. Carga directa en base de datos (para datos estructurados)
  3. Migración desde sistema anterior (requiere análisis previo)
  
- **Proceso recomendado:**
  1. Análisis de datos existentes
  2. Mapeo de campos
  3. Script de migración personalizado
  4. Validación y pruebas
  5. Migración en producción

### P: ¿Cómo se actualiza el sistema cuando hay nuevas versiones?

**R:** 
- **Proceso:**
  1. Desarrollo en entorno local
  2. Pruebas exhaustivas
  3. Commit a Git
  4. Pull en servidor
  5. Aplicar migraciones si hay cambios en modelos
  6. Recargar aplicación
  
- **Tiempo de inactividad:** < 1 minuto
- **Rollback:** Posible revertir a versión anterior desde Git

---

## 📞 CONTACTO Y COMUNICACIÓN

### P: ¿Cómo se reportan problemas o solicitudes de mejoras?

**R:** 
- **Canales:**
  - Email al equipo de desarrollo
  - Sistema de tickets (si se implementa)
  - Reuniones periódicas de seguimiento
  
- **Información requerida:**
  - Descripción del problema
  - Pasos para reproducir
  - Capturas de pantalla
  - Logs de error (si aplica)

### P: ¿Hay documentación para los usuarios finales?

**R:** 
- **Documentación técnica:** Completa en carpeta `docs/`
- **Manual de usuario:** Se puede desarrollar según necesidades
- **Videos tutoriales:** Opcional, consultar

---

## ✅ CHECKLIST PRE-ENTREVISTA

### Información a Confirmar con el Cliente:

- [ ] Número exacto de usuarios y usuarios simultáneos esperados
- [ ] Requisitos de dominio personalizado
- [ ] Necesidad de integración con otros sistemas
- [ ] Políticas de backup y retención de datos
- [ ] Requisitos de cumplimiento normativo específicos
- [ ] Presupuesto para infraestructura
- [ ] Horarios de disponibilidad requeridos (24/7 o horario laboral)
- [ ] Necesidad de reportes automáticos por email
- [ ] Proceso de migración de datos existentes
- [ ] Nivel de soporte técnico requerido

---

## 📝 NOTAS ADICIONALES

### Puntos Clave a Destacar:

1. **Sistema robusto y probado:** Django es utilizado por empresas como Instagram, Spotify, NASA
2. **Seguridad por defecto:** Django incluye protecciones contra vulnerabilidades comunes
3. **Escalable:** Puede crecer con las necesidades del negocio
4. **Mantenible:** Código limpio, documentado y siguiendo mejores prácticas
5. **Costo-efectivo:** Open source, sin costos de licencias de software
6. **Rápido despliegue:** 2-3 horas para tener el sistema en producción
7. **Soporte continuo:** Documentación completa y código mantenible

### Preguntas para Hacer al Cliente:

1. ¿Cuál es el volumen esperado de contratos a gestionar?
2. ¿Hay requisitos específicos de seguridad o cumplimiento normativo?
3. ¿Necesitan integración con sistemas contables o de facturación?
4. ¿Prefieren hosting en la nube o servidor propio?
5. ¿Cuál es el presupuesto mensual para infraestructura?
6. ¿Necesitan acceso móvil o solo desde computadoras?
7. ¿Hay personal técnico en la empresa para mantenimiento básico?
8. ¿Qué funcionalidades adicionales consideran prioritarias?

---

**Última actualización:** Diciembre 2024  
**Versión del Sistema:** Django 5.0+  
**Estado:** ✅ Listo para producción

