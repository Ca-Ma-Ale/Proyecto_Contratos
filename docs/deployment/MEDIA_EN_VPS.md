# Archivos subidos (`/media/`) en el VPS

Configurado el 2026-08-10 en el VPS Hostinger, junto con la entrega del logo
real de la empresa. Sin esta configuración el logo se sube bien y se guarda
bien, pero se ve roto en el sitio.

## Por qué hizo falta

`ConfiguracionEmpresa.logo` es el **primer y único campo de archivo del
proyecto**. Hasta agosto de 2026 nada se subía, así que `/media/` nunca se
había necesitado y nadie lo había configurado — no era un descuido, era que no
existía el caso de uso.

Dos cosas que se confunden con facilidad:

- **`/static/` lo sirve WhiteNoise**, dentro del propio contenedor de Django.
  Por eso funciona sin tocar el proxy, y por eso el logo *por defecto* (el SVG
  de `static/gestion/img/`) se ve aunque nada de este documento esté aplicado.
- **`/media/` WhiteNoise no lo sirve.** Django lo sirve él mismo solo cuando
  `DEBUG=True` (ver el `if settings.DEBUG:` al final de `contratos/urls.py`), y
  en producción `DEBUG=False`. Sin el proxy configurado, cualquier archivo
  subido responde 404.

**El síntoma cuando falta:** el administrador sube el logo, el panel dice que
guardó correctamente, el archivo aparece en el disco del servidor — y en el
login se ve el ícono de imagen rota. Nada en los logs de Django lo delata,
porque Django nunca llegó a ver esa petición.

## Dónde vive la configuración

**No está en este repositorio.** El proxy es un Caddy compartido que vive en el
proyecto vecino:

| | Ruta en el VPS |
|---|---|
| Compose del proxy | `/opt/cm-pagina-web/cm-pagina-web/docker-compose.prod.yml` |
| Caddyfile | `/opt/cm-pagina-web/cm-pagina-web/Caddyfile` |

Un solo contenedor (`cm-pagina-web-caddy-1`) atiende los dos sitios, cada uno en
su propio bloque de dominio: `{$SITE_DOMAIN}` para la página web y
`{$CONTRATOS_SITE_DOMAIN}` para este proyecto. **Editar esos archivos afecta a
los dos sitios** — respaldar antes de tocarlos.

## Las dos piezas

**1. Montar el `media` de contratos dentro del contenedor de Caddy**, en el
servicio `caddy` del compose:

```yaml
      - /opt/proyecto-contratos/deploy_data/media:/srv/media-contratos:ro
```

**2. Servirlo en el bloque del dominio de contratos** del `Caddyfile`, antes del
`reverse_proxy`:

```
{$CONTRATOS_SITE_DOMAIN} {
    encode gzip zstd

    handle_path /media/* {
        root * /srv/media-contratos
        file_server
    }

    reverse_proxy proyecto-contratos-web:8000 {
        ...
    }
}
```

Es el mismo patrón que la página web ya usaba para sus propios `/static/` y
`/media/`; lo nuevo es replicarlo en el bloque de contratos.

## Detalles que no son opcionales

- **`/srv/media-contratos`, no `/srv/media`.** Ese último ya está tomado por
  cm-pagina-web dentro del mismo contenedor. Reutilizar el nombre haría que un
  sitio sirviera los archivos del otro — una fuga de archivos entre clientes,
  no solo un logo mal puesto.
- **`handle_path` recorta el prefijo `/media`** antes de buscar el archivo. Por
  eso `root` apunta a la raíz del directorio y no lleva `/media` en la ruta. Con
  `handle` (sin `_path`) habría que incluirlo, y la ruta quedaría duplicada.
- **`:ro`** — Caddy solo lee. Quien escribe es Django, por su propio montaje
  (`./deploy_data/media:/app/media`, en el compose de *este* proyecto).
- **Agregar un volumen exige recrear el contenedor.** Un `caddy reload` no
  basta, porque el montaje se resuelve al crear el contenedor:
  `docker compose -f docker-compose.prod.yml up -d --no-deps caddy`. El
  `--no-deps` evita arrastrar `web` y `mysql` en el reinicio. Los certificados
  sobreviven porque viven en el volumen `caddy_data`.
- El contenedor de Django **corre como root**, así que escribe sin problema en
  el directorio del host (propiedad de root, `755`). Si algún día se cambia el
  contenedor a un usuario sin privilegios, habrá que ajustar el dueño de
  `deploy_data/media` o las subidas fallarán con permiso denegado.

## El recorrido completo de un archivo

| Capa | Ruta |
|---|---|
| `MEDIA_ROOT` en Django | `/app/media` |
| Disco del host | `/opt/proyecto-contratos/deploy_data/media` |
| Contenedor de Caddy | `/srv/media-contratos` (solo lectura) |
| URL pública | `https://<dominio>/media/...` |

Un logo subido queda en `empresa/logos/<archivo>` dentro de esa cadena
(`upload_to='empresa/logos/'` en el modelo).

## Cómo comprobar que sigue funcionando

Sin depender de subir nada por la interfaz:

```bash
echo prueba > /opt/proyecto-contratos/deploy_data/media/prueba.txt
curl -s https://sisgestioncontratosavchile.cloud/media/prueba.txt
rm /opt/proyecto-contratos/deploy_data/media/prueba.txt
```

Debe imprimir `prueba`. Un 404 significa que se perdió alguna de las dos piezas
— casi siempre porque se recreó el proxy desde una copia del compose que no las
tenía.
