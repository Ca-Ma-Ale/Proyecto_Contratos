"""
Resolucion de la IP real del cliente detras del proxy inverso (Caddy).

Caddy anade la IP del cliente al final de X-Forwarded-For; el primer valor de
esa cabecera lo puede fabricar el propio cliente, asi que solo se confia en el
ULTIMO (el que puso nuestro unico proxy). Sin la cabecera (desarrollo, tests)
se usa REMOTE_ADDR.
"""


def obtener_ip_cliente(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        partes = [p.strip() for p in xff.split(',') if p.strip()]
        if partes:
            return partes[-1]
    return request.META.get('REMOTE_ADDR')
