"""
Servicio para envío de correos electrónicos.
"""

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from typing import List, Optional, Dict, Any
import logging

from gestion.models import ConfiguracionEmail, HistorialEnvioEmail

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de correos electrónicos"""
    
    def __init__(self, configuracion: Optional[ConfiguracionEmail] = None):
        """
        Inicializa el servicio de email.
        
        Args:
            configuracion: Configuración de email a usar. Si es None, usa la activa.
        """
        self.configuracion = configuracion or ConfiguracionEmail.get_activa()
        if not self.configuracion:
            raise ValueError("No hay configuración de email activa")
    
    def _configurar_django_email(self):
        """Configura Django para usar la configuración de email"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        settings.EMAIL_HOST = self.configuracion.email_host
        settings.EMAIL_PORT = self.configuracion.email_port
        settings.EMAIL_USE_TLS = self.configuracion.email_use_tls
        settings.EMAIL_USE_SSL = self.configuracion.email_use_ssl
        settings.EMAIL_HOST_USER = self.configuracion.email_host_user
        # Desencriptar contraseña antes de usar
        try:
            settings.EMAIL_HOST_PASSWORD = self.configuracion.get_password()
        except Exception as e:
            logger.error(f"Error desencriptando contraseña de email: {e}", exc_info=True)
            raise ValueError("No se pudo desencriptar la contraseña de email. Verifique la configuración de ENCRYPTION_KEY.")
        settings.DEFAULT_FROM_EMAIL = self.configuracion.email_from
    
    def enviar_email(
        self,
        destinatarios: List[str],
        asunto: str,
        contenido_html: str,
        contenido_texto: Optional[str] = None,
        adjuntos: Optional[List] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Envía un correo electrónico.
        
        Args:
            destinatarios: Lista de emails destinatarios
            asunto: Asunto del correo
            contenido_html: Contenido HTML del correo
            contenido_texto: Contenido en texto plano (opcional)
            adjuntos: Lista de archivos adjuntos (opcional)
            cc: Lista de emails en copia (opcional)
            bcc: Lista de emails en copia oculta (opcional)
        
        Returns:
            True si el envío fue exitoso, False en caso contrario
        """
        if not destinatarios:
            logger.warning("No hay destinatarios para enviar el correo")
            return False
        
        try:
            self._configurar_django_email()
            
            nombre_remitente = self.configuracion.nombre_remitente or "Sistema de Gestión de Contratos"
            from_email = f"{nombre_remitente} <{self.configuracion.email_from}>"
            
            email = EmailMultiAlternatives(
                subject=asunto,
                body=contenido_texto or contenido_html,
                from_email=from_email,
                to=destinatarios,
                cc=cc or [],
                bcc=bcc or [],
            )
            
            email.attach_alternative(contenido_html, "text/html")
            
            if adjuntos:
                for adjunto in adjuntos:
                    email.attach(*adjunto)
            
            email.send()
            logger.info(f"Correo enviado exitosamente a {', '.join(destinatarios)}")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
            return False
    
    def enviar_email_template(
        self,
        destinatarios: List[str],
        asunto: str,
        template_html: str,
        contexto: Dict[str, Any],
        template_texto: Optional[str] = None,
        adjuntos: Optional[List] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Envía un correo usando templates Django.
        
        Args:
            destinatarios: Lista de emails destinatarios
            asunto: Asunto del correo
            template_html: Ruta al template HTML
            contexto: Contexto para el template
            template_texto: Ruta al template de texto plano (opcional)
            adjuntos: Lista de archivos adjuntos (opcional)
            cc: Lista de emails en copia (opcional)
            bcc: Lista de emails en copia oculta (opcional)
        
        Returns:
            True si el envío fue exitoso, False en caso contrario
        """
        try:
            contenido_html = render_to_string(template_html, contexto)
            contenido_texto = None
            if template_texto:
                contenido_texto = render_to_string(template_texto, contexto)
            
            return self.enviar_email(
                destinatarios=destinatarios,
                asunto=asunto,
                contenido_html=contenido_html,
                contenido_texto=contenido_texto,
                adjuntos=adjuntos,
                cc=cc,
                bcc=bcc,
            )
        except Exception as e:
            logger.error(f"Error al renderizar template de email: {str(e)}", exc_info=True)
            return False

