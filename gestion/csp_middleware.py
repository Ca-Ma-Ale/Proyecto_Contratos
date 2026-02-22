"""
Middleware de Content Security Policy (CSP).

Agrega la cabecera HTTP Content-Security-Policy a todas las respuestas
para mitigar ataques XSS y de inyección de contenido.

Notas sobre la política actual:
- 'unsafe-inline' está permitido en script-src y style-src porque el proyecto
  usa Bootstrap y JS/CSS inline en templates. Para endurecer en el futuro,
  migrar a nonces ({% csp_nonce %}) o hashes por recurso.
- frame-ancestors 'none' equivale a X-Frame-Options: DENY.
"""


class ContentSecurityPolicyMiddleware:
    """Agrega la cabecera Content-Security-Policy a todas las respuestas HTTP."""

    # Bootstrap JS/CSS: cdn.jsdelivr.net
    # Font Awesome CSS + webfonts: cdnjs.cloudflare.com
    POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "font-src 'self' cdnjs.cloudflare.com data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # No sobreescribir si ya viene definida (p.ej. en vistas específicas)
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = self.POLICY
        return response
