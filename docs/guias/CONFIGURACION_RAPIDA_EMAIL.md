# Configuración Rápida de Alertas por Email

Guía rápida para configurar el sistema de alertas por email en 5 minutos.

## Paso 1: Verificar/Configurar Clave de Encriptación

La clave de encriptación se usa para proteger las contraseñas SMTP. Si no está configurada:

```bash
# Generar nueva clave
python -c "from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())"
```

Copiar la clave generada y agregarla al archivo `.env`:

```
ENCRYPTION_KEY=tu-clave-generada-aqui
```

## Paso 2: Configurar Email SMTP

### Opción A: Script Interactivo (Recomendado)

```bash
python scripts/configurar_email.py
```

Seleccionar opción 2 y seguir las instrucciones.

### Opción B: Manual desde Admin

1. Ir a: `/admin/gestion/configuracionemail/add/`
2. Completar los campos:
   - **Nombre**: Nombre descriptivo (ej: "Gmail Principal")
   - **Servidor SMTP**: `smtp.gmail.com` (o tu servidor)
   - **Puerto SMTP**: `587` (TLS) o `465` (SSL)
   - **Usar TLS**: ✓ (si puerto 587)
   - **Usar SSL**: ✓ (si puerto 465)
   - **Usuario/Email**: Tu email SMTP
   - **Contraseña**: Contraseña o token de aplicación
   - **Email Remitente**: Email que aparecerá como remitente
   - **Nombre del Remitente**: Nombre opcional
   - **Configuración Activa**: ✓

**Para Gmail:**
- Usar "Contraseña de aplicación" en lugar de contraseña normal
- Generar en: https://myaccount.google.com/apppasswords

## Paso 3: Configurar Alertas

### Opción A: Script Interactivo

```bash
python scripts/configurar_email.py
```

Seleccionar opción 3 y seguir las instrucciones.

### Opción B: Manual desde Admin

1. Ir a: `/admin/gestion/configuracionalerta/add/`
2. Para cada tipo de alerta que desees:
   - **Tipo de Alerta**: Seleccionar (ej: VENCIMIENTO_CONTRATOS)
   - **Alerta Activa**: ✓
   - **Frecuencia de Envío**: 
     - `SEMANAL` - En días específicos (recomendado)
     - `DIARIO` - Todos los días
     - `MENSUAL` - Día 1 de cada mes
     - `INMEDIATO` - Siempre que se ejecute
   - **Días de la Semana**: Para frecuencia semanal, formato JSON: `[0]` (Lunes), `[0,3]` (Lunes y Jueves)
   - **Hora de Envío**: Ej: `08:00`
   - **Solo Alertas Críticas**: Opcional

**Días de la semana:**
- 0 = Lunes
- 1 = Martes
- 2 = Miércoles
- 3 = Jueves
- 4 = Viernes
- 5 = Sábado
- 6 = Domingo

## Paso 4: Configurar Destinatarios

### Opción A: Script Interactivo

```bash
python scripts/configurar_email.py
```

Seleccionar opción 4 y seguir las instrucciones.

### Opción B: Manual desde Admin

1. Ir a: `/admin/gestion/destinatarioalerta/add/`
2. Para cada destinatario:
   - **Configuración de Alerta**: Seleccionar tipo de alerta
   - **Email Destinatario**: Email del destinatario
   - **Nombre**: Nombre opcional
   - **Activo**: ✓

## Paso 5: Probar Configuración

### Prueba Rápida

```bash
python scripts/prueba_email_rapida.py tu-email@ejemplo.com
```

### Prueba Interactiva

```bash
python scripts/prueba_envio_email.py
```

### Prueba de Alertas Reales

```bash
# Probar un tipo específico
python manage.py enviar_alertas_email --tipo VENCIMIENTO_CONTRATOS --forzar
```

## Verificación

1. Revisar historial de envíos: `/admin/gestion/historialenvioemail/`
2. Verificar que los correos llegaron (revisar spam si es necesario)

## Configuración Común: Gmail

```
Servidor SMTP: smtp.gmail.com
Puerto: 587
TLS: ✓
SSL: ✗
Usuario: tu-email@gmail.com
Contraseña: [Contraseña de aplicación de 16 caracteres]
```

## Solución de Problemas

### Error: "No hay configuración de email activa"
- Verificar que existe una configuración en `/admin/gestion/configuracionemail/`
- Activar una configuración

### Error: "No se pudo desencriptar la contraseña"
- Verificar que ENCRYPTION_KEY está configurada en `.env`
- Si cambiaste la clave, debes volver a ingresar las contraseñas

### Los correos no se envían
- Verificar credenciales SMTP
- Para Gmail, usar contraseña de aplicación
- Revisar firewall/antivirus
- Ver historial de envíos para errores específicos

## Checklist de Configuración

- [ ] ENCRYPTION_KEY configurada en `.env`
- [ ] Configuración de email SMTP creada y activa
- [ ] Al menos un tipo de alerta configurado
- [ ] Al menos un destinatario configurado por alerta
- [ ] Correo de prueba enviado exitosamente
- [ ] Historial de envíos funcionando

## Próximos Pasos

Una vez configurado y probado:

1. Configurar tarea programada (cron/tareas programadas)
2. Monitorear historial de envíos regularmente
3. Ajustar frecuencia y destinatarios según necesidades

Ver documentación completa:
- `docs/guias/GUIA_PRUEBAS_EMAIL.md` - Guía de pruebas
- `docs/sistemas/SISTEMA_ALERTAS_EMAIL.md` - Documentación completa

