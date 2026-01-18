# Configuración de Email - Paso a Paso

## Estado Actual
✓ Clave de encriptación: Configurada
✗ Email SMTP: Pendiente
✗ Alertas: Pendientes

## Paso 1: Configurar Email SMTP

### Opción A: Desde el Admin de Django (Recomendado)

1. **Iniciar el servidor Django:**
   ```bash
   venv\Scripts\activate
   python manage.py runserver
   ```

2. **Abrir en el navegador:**
   ```
   http://localhost:8000/admin/
   ```

3. **Ir a:** `Gestion > Configuraciones de Email > Agregar configuración de email`

4. **Completar el formulario:**

   **Información General:**
   - Nombre: `Gmail Principal` (o el nombre que prefieras)
   - Configuración Activa: ✓ (marcar)

   **Configuración SMTP:**
   - Servidor SMTP: `smtp.gmail.com`
   - Puerto SMTP: `587`
   - Usar TLS: ✓ (marcar)
   - Usar SSL: ✗ (no marcar)

   **Credenciales:**
   - Usuario/Email: `tu-email@gmail.com`
   - Contraseña: `[Ver instrucciones para Gmail abajo]`
   
   **Remitente:**
   - Email Remitente: `tu-email@gmail.com` (igual al usuario)
   - Nombre del Remitente: `Sistema de Gestión de Contratos` (opcional)

5. **Guardar**

### Opción B: Usar Script Interactivo

```bash
venv\Scripts\activate
python scripts/configurar_email.py
```

Seleccionar opción 2 y seguir las instrucciones.

### ⚠️ IMPORTANTE: Para Gmail

Gmail requiere una "Contraseña de aplicación" en lugar de tu contraseña normal:

1. Ir a: https://myaccount.google.com/apppasswords
2. Seleccionar "Correo" y "Otro (nombre personalizado)"
3. Ingresar nombre: "Sistema Contratos"
4. Hacer clic en "Generar"
5. Copiar la contraseña de 16 caracteres generada
6. Usar esa contraseña en el campo "Contraseña" del formulario

## Paso 2: Configurar Alertas

### Desde el Admin:

1. **Ir a:** `Gestion > Configuraciones de Alertas > Agregar configuración de alerta`

2. **Configurar cada tipo de alerta que desees:**

   **Ejemplo: Vencimiento de Contratos**
   - Tipo de Alerta: `Vencimiento de Contratos`
   - Alerta Activa: ✓
   - Frecuencia de Envío: `SEMANAL`
   - Días de la Semana: `[0]` (para Lunes)
   - Hora de Envío: `08:00`
   - Solo Alertas Críticas: ✗
   - Asunto Personalizado: (dejar vacío para usar por defecto)

   **Guardar y repetir para otros tipos si lo deseas:**
   - Alertas IPC
   - Pólizas Críticas
   - Preaviso de Renovación
   - etc.

### Días de la Semana (formato JSON):
- `[0]` = Lunes
- `[0,3]` = Lunes y Jueves
- `[0,1,2,3,4]` = Lunes a Viernes
- `[5,6]` = Sábado y Domingo

## Paso 3: Configurar Destinatarios

1. **Ir a:** `Gestion > Destinatarios de Alertas > Agregar destinatario de alerta`

2. **Para cada destinatario:**
   - Configuración de Alerta: Seleccionar el tipo (ej: Vencimiento de Contratos)
   - Email Destinatario: `destinatario@ejemplo.com`
   - Nombre: `Juan Pérez` (opcional)
   - Activo: ✓

3. **Repetir** para cada tipo de alerta y cada destinatario

## Paso 4: Probar Configuración

### Verificar Estado:
```bash
venv\Scripts\activate
python scripts/verificar_configuracion_email.py
```

### Enviar Correo de Prueba:
```bash
python scripts/prueba_email_rapida.py tu-email@ejemplo.com
```

### Probar Envío de Alertas:
```bash
python manage.py enviar_alertas_email --tipo VENCIMIENTO_CONTRATOS --forzar
```

## Verificar Resultados

1. **Revisar historial:** `http://localhost:8000/admin/gestion/historialenvioemail/`
2. **Revisar bandeja de entrada** (y carpeta de spam)
3. **Verificar que los correos llegaron correctamente**

## Configuración de Otros Proveedores

### Outlook/Office365:
- Servidor SMTP: `smtp.office365.com`
- Puerto: `587`
- TLS: ✓
- SSL: ✗

### Otros:
Consultar la documentación de tu proveedor de email para los datos SMTP.

## Solución de Problemas

### Error: "No se pudo desencriptar la contraseña"
- Verificar que ENCRYPTION_KEY está en el archivo `.env`
- Si cambiaste la clave, volver a ingresar las contraseñas

### Los correos no se envían
- Verificar credenciales SMTP
- Para Gmail, usar contraseña de aplicación
- Revisar firewall/antivirus
- Ver historial de envíos para errores específicos

### Los correos llegan a spam
- Verificar que el email remitente es válido
- Configurar SPF/DKIM del dominio (si aplica)
- Pedir a destinatarios que marquen como "No es spam"

## Documentación Adicional

- `docs/guias/CONFIGURACION_RAPIDA_EMAIL.md` - Guía rápida
- `docs/guias/GUIA_PRUEBAS_EMAIL.md` - Guía de pruebas
- `docs/sistemas/SISTEMA_ALERTAS_EMAIL.md` - Documentación completa

