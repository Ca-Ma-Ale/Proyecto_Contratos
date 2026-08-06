# Alertas por correo programadas en el VPS

Configurado el 2026-08-06 en el VPS Hostinger (`/opt/proyecto-contratos`).

En PythonAnywhere el envío semanal lo disparaba una **Scheduled Task** de la
plataforma. Al migrar al VPS esa función desapareció y las alertas quedaron
inactivas: el código nunca dejó de funcionar, simplemente no había quién
ejecutara el comando. En el VPS el disparador es `cron` en el host.

## La tarea

```cron
0 13 * * 6 cd /opt/proyecto-contratos && /usr/bin/docker compose -f docker-compose.prod.yml exec -T web python manage.py enviar_alertas_email >> /var/log/alertas-contratos.log 2>&1
```

Instalada en el crontab de `root`. Tres detalles que no son opcionales:

- **`-T`**: sin él, `docker compose exec` pide un TTY y bajo cron falla siempre.
- **Ruta absoluta `/usr/bin/docker`**: cron corre con un `PATH` mínimo y no
  encuentra `docker` por su cuenta. Si algún día cambia la ruta, la tarea falla
  en silencio. Se comprueba con `command -v docker`.
- **El `cd` primero**: `docker compose -f docker-compose.prod.yml` es relativo al
  directorio del proyecto.

Para instalarla sin pelear con `crontab -e` (que la primera vez interrumpe con el
menú de selección de editor y se come la línea pegada):

```bash
crontab -l 2>/dev/null | { cat; echo '0 13 * * 6 cd /opt/proyecto-contratos && /usr/bin/docker compose -f docker-compose.prod.yml exec -T web python manage.py enviar_alertas_email >> /var/log/alertas-contratos.log 2>&1'; } | crontab -
```

## Las dos compuertas

El envío depende de **dos condiciones independientes** que tienen que coincidir:

1. **El cron** decide cuándo se ejecuta el comando.
2. **`ConfiguracionAlerta.debe_enviar_hoy()`** decide si hoy toca enviar, según
   `frecuencia` y `dias_semana` guardados en la base de datos.

Si el cron corre un sábado pero la configuración dice lunes, no sale nada y no
hay ningún error visible: el comando responde `No hay alertas programadas para
hoy` y termina con éxito.

**Y cada compuerta numera los días de forma distinta:**

| | Lunes | Sábado | Domingo |
|---|---|---|---|
| `cron` (5.º campo) | 1 | **6** | 0 |
| `weekday()` de Python, que usa `debe_enviar_hoy` | 0 | **5** | 6 |

Por eso la tarea dice `* * 6` y la configuración en base de datos dice `[5]`.
Ambas son sábado.

## Zona horaria

El VPS está en **UTC** (`timedatectl`) y Django en **`America/Bogota`**
(UTC−5) con `USE_TZ=True`. `debe_enviar_hoy()` evalúa la fecha en la zona de
Django, no en la del host.

Las 13:00 UTC del sábado son las 8:00 a. m. del sábado en Bogotá: ambas fechas
caen en sábado y el envío procede.

**Franja peligrosa:** entre las 00:00 y las 05:00 UTC del sábado, en Bogotá
todavía es viernes. Un cron a esas horas ejecutaría el comando y
`debe_enviar_hoy()` respondería que no toca. Por eso no sirve un `0 8 * * 6`
puesto sin pensar.

## De dónde salen las credenciales de correo

**No del `.env`.** Aunque el `.env` tenga `EMAIL_HOST`, `EMAIL_HOST_USER` y
`EMAIL_HOST_PASSWORD`, el sistema de alertas no los usa.

La cadena real es `AlertaEmailService` → `EmailService` →
`ConfiguracionEmail.get_activa()`, es decir **una fila en la base de datos**.
`EmailService._configurar_django_email()` sobrescribe `settings.EMAIL_*` en
tiempo de ejecución con lo que traiga esa fila, y descifra la contraseña con
`get_password()`.

Se puede reutilizar la misma cuenta de Gmail y la misma contraseña de
aplicación, pero hay que cargarla en `ConfiguracionEmail` (admin de Django o
`scripts/configurar_email.py`). Ponerla solo en el `.env` no activa nada.

### Trampa: `ENCRYPTION_KEY`

`get_password()` descifra con Fernet usando `ENCRYPTION_KEY`. Si esa variable no
está definida, `gestion/utils_encryption.py` deriva la clave del `SECRET_KEY`
por PBKDF2 y deja un aviso en los logs. Hoy en el VPS funciona por ese camino de
respaldo.

La consecuencia: **si algún día se rota el `SECRET_KEY`, la contraseña guardada
deja de descifrarse y las alertas mueren en silencio** — el síntoma es que el
cliente deja de recibir correos.

Al configurar `ENCRYPTION_KEY` hay que tener cuidado con el orden, porque la
contraseña actual está cifrada con la clave derivada del `SECRET_KEY` y tampoco
se podrá descifrar con la nueva:

1. Definir `ENCRYPTION_KEY` en el `.env`.
2. Recrear el contenedor (`up -d web`; un `restart` no relee el `.env`).
3. **Volver a guardar la contraseña** para que se cifre con la clave nueva.

## Cómo probar sin molestar al cliente

Los destinatarios que hay en `DestinatarioAlerta` son correos **del cliente**
(hoy `gestiondocumental@avenidachilecentrocomercial.com`). Un
`enviar_alertas_email --forzar` le manda una alerta real, en un día cualquiera.

Para probar solo la conexión SMTP, usando exactamente la misma ruta de código
(configuración desde la base, descifrado de la contraseña, conexión a Gmail)
pero con un destinatario propio:

```bash
docker compose -f docker-compose.prod.yml exec -T web python manage.py shell -c "
from gestion.services.email_service import EmailService
print('Enviado:', EmailService().enviar_email(
    destinatarios=['TU_CORREO@ejemplo.com'],
    asunto='Prueba SMTP alertas contratos',
    contenido_html='<p>Prueba de conexion SMTP desde el VPS.</p>',
))
"
```

Y para comprobar que el comando arranca bien sin enviar nada, basta ejecutarlo
**sin `--forzar`** cualquier día que no sea sábado: debe responder `No hay
alertas programadas para hoy`.

## Diagnóstico

Estado de la configuración de correo y de las alertas activas:

```bash
docker compose -f docker-compose.prod.yml exec -T web python manage.py shell -c "
from gestion.models import ConfiguracionEmail, ConfiguracionAlerta
c = ConfiguracionEmail.get_activa()
print('SMTP:', c.email_host, c.email_port, c.email_host_user)
try:
    c.get_password(); print('Password: descifra OK')
except Exception as e:
    print('Password: FALLA ->', e)
for a in ConfiguracionAlerta.objects.filter(activo=True):
    print(a.tipo_alerta, a.frecuencia, a.dias_semana)
"
```

Resultado del último envío:

```bash
cat /var/log/alertas-contratos.log
```

## Notas

- **`hora_envio` no hace nada.** `debe_enviar_hoy()` solo compara la fecha, nunca
  la hora. La hora real de envío la define el cron; lo que se vea en el admin es
  informativo.
- El comando `configurar_alertas_default --frecuencia SEMANAL --dias 5` cambia
  **todas** las configuraciones a la vez. Para días distintos por tipo, usar el
  admin.
- Los 8 tipos de alerta quedaron en `SEMANAL` con `dias_semana [5]`.
