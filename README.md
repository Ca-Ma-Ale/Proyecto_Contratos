# Sistema de Gestión de Contratos de Arrendamiento

Sistema web robusto y flexible para la gestión de contratos de arrendamiento comercial, desarrollado con Django 5.0+.

## 🚀 Estado del Proyecto

**✅ COMPLETO Y FUNCIONANDO**
- ✅ Sistema de autenticación implementado
- ✅ Módulo Otro Sí con lógica compleja
- ✅ Formateo automático en todos los módulos
- ✅ Dashboard con alertas avanzadas
- ✅ Listo para producción

## 📚 Documentación

**Para empezar:**
- **[Guía de Instalación](docs/guias/GUIA_INSTALACION.md)** - Configuración inicial
- **[Guía de Producción](docs/guias/GUIA_PRODUCCION.md)** - Deployment y configuración
- **[Documentación Completa](docs/README.md)** - Todas las guías disponibles

## Características Principales

- **Gestión Completa de Contratos**: Manejo de contratos simples (canon fijo) y complejos (cánones híbridos, periodos de gracia)
- **Dashboard de Alertas Avanzado**: Monitoreo en tiempo real de vencimientos, pólizas y reportes
- **Sistema de Autenticación**: Login/logout con control de acceso por roles
- **Administración Organizada**: Panel de administración con fieldsets y inlines intuitivos
- **Flexibilidad de Modalidades**: Soporte para contratos fijos, variables y híbridos
- **Seguridad Lista para Producción**: Configuraciones HTTPS, CSRF, y mejores prácticas

## Modelos Implementados

### Arrendatario
- Información básica (NIT, razón social, representante legal)
- Contacto operativo (supervisor y email para alertas)

### Local
- Información del espacio comercial (nombre, área)

### Contrato
- **Vigencia**: Fechas iniciales, actualizadas, prórroga automática
- **Financiero**: Modalidades de pago flexibles, cánones fijos/variables/híbridos
- **Operativo**: Reporte de ventas, periodos de gracia, penalidades

### Poliza
- Gestión detallada de seguros (cumplimiento, RCE, arrendamiento)
- Estados calculados automáticamente (vigente, por vencer, vencida)

### OtroSi
- Modificaciones contractuales con actualización automática

## Dashboard de Alertas

El sistema incluye un dashboard completo con:

1. **Alertas de Vencimiento**: Contratos que vencen en 60 días
2. **Alertas de Pólizas**: Seguros vencidos, por vencer o no aportados
3. **Alertas de Preaviso**: Notificaciones de renovación automática
4. **Alertas de Reporte**: Recordatorios de reporte de ventas

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar base de datos:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Crear superusuario:
```bash
python manage.py createsuperuser
```

5. Ejecutar servidor:
```bash
python manage.py runserver
```

## Acceso

### Desarrollo
- **Login**: http://localhost:8000/login/
- **Dashboard**: http://localhost:8000/
- **Administración**: http://localhost:8000/admin/

### Usuarios por Defecto
Después de crear el superusuario:
- **Username**: (el que configures)
- **Password**: (la que configures)

## 🔐 Autenticación y Seguridad

- Sistema de login/logout implementado
- Control de acceso por roles (usuario normal vs admin)
- Protección CSRF automática
- Configuraciones de seguridad para HTTPS
- Variables de entorno para secrets
- Logging de errores configurado

Ver documentación completa en: `docs/sistemas/SISTEMA_AUTENTICACION.md`

## 💾 Backups Automáticos

- Sistema de backups automatizado implementado
- Comando Django: `python manage.py backup_database`
- Scripts para Linux y Windows
- Limpieza automática de backups antiguos
- Soporte para backup JSON y SQLite

Ver documentación completa en: `docs/guias/GUIA_BACKUPS_AUTOMATICOS.md`

## 🚀 Deployment en Producción

Para llevar este proyecto a producción:

1. **[Lee la Guía de Producción](docs/guias/GUIA_PRODUCCION.md)** - Tareas críticas antes de producción
2. **[Sigue el Deployment en PythonAnywhere](docs/deployment/DEPLOYMENT_PYTHONANYWHERE.md)** - Guía paso a paso
3. **[Verifica con el Checklist](docs/deployment/CHECKLIST_PRODUCCION.md)** - Lista de verificación completa

**Tiempo estimado:** ~1 hora para deployment completo

## Tecnologías

- Python 3.10+
- Django 5.0+
- Bootstrap 5.3
- Font Awesome 6.0
- SQLite (desarrollo) / MySQL (producción opcional)

## 📞 Soporte

Para problemas o dudas:
- **[Documentación Completa](docs/README.md)** - Todas las guías disponibles
- **[Problemas Comunes](docs/soluciones/PROBLEMAS_CRITICOS_RESUELTOS.md)** - Soluciones técnicas
- **Documentación Django:** https://docs.djangoproject.com/
- **PythonAnywhere Help:** https://help.pythonanywhere.com/
# Proyecto_Contratos
