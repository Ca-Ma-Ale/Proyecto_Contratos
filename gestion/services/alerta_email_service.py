"""
Servicio para envío de alertas por correo electrónico.
"""

from datetime import date, datetime, time
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.template.loader import render_to_string
import logging

from gestion.models import (
    ConfiguracionAlerta,
    DestinatarioAlerta,
    HistorialEnvioEmail,
    TIPO_ALERTA_CHOICES,
)
from gestion.services.email_service import EmailService
from gestion.services.alertas import (
    obtener_alertas_expiracion_contratos,
    obtener_alertas_ipc,
    obtener_alertas_salario_minimo,
    obtener_polizas_criticas,
    obtener_alertas_preaviso,
    obtener_alertas_polizas_requeridas_no_aportadas,
    obtener_alertas_terminacion_anticipada,
    obtener_alertas_renovacion_automatica,
)

logger = logging.getLogger(__name__)


class AlertaEmailService:
    """Servicio para envío de alertas por correo electrónico"""
    
    MAPEO_FUNCIONES_ALERTA = {
        'VENCIMIENTO_CONTRATOS': obtener_alertas_expiracion_contratos,
        'ALERTAS_IPC': obtener_alertas_ipc,
        'ALERTAS_SALARIO_MINIMO': obtener_alertas_salario_minimo,
        'POLIZAS_CRITICAS': obtener_polizas_criticas,
        'PREAVISO_RENOVACION': obtener_alertas_preaviso,
        'POLIZAS_REQUERIDAS': obtener_alertas_polizas_requeridas_no_aportadas,
        'TERMINACION_ANTICIPADA': obtener_alertas_terminacion_anticipada,
        'RENOVACION_AUTOMATICA': obtener_alertas_renovacion_automatica,
    }
    
    MAPEO_NOMBRES_ALERTA = {
        'VENCIMIENTO_CONTRATOS': 'Vencimiento de Contratos',
        'ALERTAS_IPC': 'Alertas IPC',
        'ALERTAS_SALARIO_MINIMO': 'Alertas de Ajuste de Salario Mínimo',
        'POLIZAS_CRITICAS': 'Pólizas Críticas',
        'PREAVISO_RENOVACION': 'Preaviso de Renovación',
        'POLIZAS_REQUERIDAS': 'Pólizas Requeridas No Aportadas',
        'TERMINACION_ANTICIPADA': 'Terminación Anticipada',
        'RENOVACION_AUTOMATICA': 'Renovación Automática',
    }
    
    def __init__(self):
        self.email_service = EmailService()
    
    def obtener_alertas_por_tipo(
        self,
        tipo_alerta: str,
        fecha_referencia: Optional[date] = None,
        solo_criticas: bool = False
    ) -> List:
        """
        Obtiene las alertas según el tipo especificado.
        
        Args:
            tipo_alerta: Tipo de alerta a obtener
            fecha_referencia: Fecha de referencia para calcular alertas
            solo_criticas: Si es True, solo retorna alertas críticas
        
        Returns:
            Lista de alertas
        """
        funcion = self.MAPEO_FUNCIONES_ALERTA.get(tipo_alerta)
        if not funcion:
            logger.warning(f"Tipo de alerta no reconocido: {tipo_alerta}")
            return []
        
        try:
            alertas = funcion(fecha_referencia=fecha_referencia)
            
            if solo_criticas:
                alertas = self._filtrar_solo_criticas(alertas, tipo_alerta)
            
            return alertas
        except Exception as e:
            logger.error(f"Error al obtener alertas de tipo {tipo_alerta}: {str(e)}", exc_info=True)
            return []
    
    def _filtrar_solo_criticas(self, alertas: List, tipo_alerta: str) -> List:
        """Filtra solo las alertas críticas"""
        if tipo_alerta == 'ALERTAS_IPC':
            return [a for a in alertas if a.color_alerta == 'danger']
        elif tipo_alerta == 'ALERTAS_SALARIO_MINIMO':
            return [a for a in alertas if a.color_alerta == 'danger']
        elif tipo_alerta == 'POLIZAS_CRITICAS':
            return alertas
        elif tipo_alerta in ['VENCIMIENTO_CONTRATOS', 'PREAVISO_RENOVACION']:
            return alertas
        else:
            return alertas
    
    def obtener_destinatarios(self, tipo_alerta: str) -> List[DestinatarioAlerta]:
        """Obtiene los destinatarios activos para un tipo de alerta"""
        try:
            config = ConfiguracionAlerta.objects.get(tipo_alerta=tipo_alerta, activo=True)
            return list(config.destinatarios.filter(activo=True))
        except ConfiguracionAlerta.DoesNotExist:
            logger.warning(f"No hay configuración activa para el tipo de alerta: {tipo_alerta}")
            return []
    
    def generar_contenido_email(
        self,
        tipo_alerta: str,
        alertas: List,
        fecha_referencia: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Genera el contenido del email para las alertas.
        
        Returns:
            Diccionario con 'asunto' y 'contenido_html'
        """
        nombre_alerta = self.MAPEO_NOMBRES_ALERTA.get(tipo_alerta, tipo_alerta)
        cantidad = len(alertas)
        
        if cantidad == 0:
            asunto = f"No hay {nombre_alerta.lower()}"
        else:
            asunto = f"{nombre_alerta} - {cantidad} alerta(s) encontrada(s)"
        
        contexto = {
            'tipo_alerta': tipo_alerta,
            'nombre_alerta': nombre_alerta,
            'alertas': alertas,
            'cantidad': cantidad,
            'fecha_referencia': fecha_referencia or timezone.now().date(),
            'fecha_actual': timezone.now(),
        }
        
        template_html = f'gestion/emails/alerta_{tipo_alerta.lower()}.html'
        if tipo_alerta == 'ALERTAS_SALARIO_MINIMO':
            template_html = 'gestion/emails/alerta_alertas_salario_minimo.html'
        
        try:
            contenido_html = render_to_string(template_html, contexto)
        except Exception:
            contenido_html = render_to_string('gestion/emails/alerta_generica.html', contexto)
        
        return {
            'asunto': asunto,
            'contenido_html': contenido_html,
            'contexto': contexto,
        }
    
    def enviar_alertas_tipo(
        self,
        tipo_alerta: str,
        fecha_referencia: Optional[date] = None,
        forzar_envio: bool = False
    ) -> Dict[str, Any]:
        """
        Envía las alertas de un tipo específico por correo.
        
        Args:
            tipo_alerta: Tipo de alerta a enviar
            fecha_referencia: Fecha de referencia para calcular alertas
            forzar_envio: Si es True, envía aunque no sea el día programado
        
        Returns:
            Diccionario con el resultado del envío
        """
        resultado = {
            'tipo_alerta': tipo_alerta,
            'enviado': False,
            'destinatarios': 0,
            'alertas_enviadas': 0,
            'errores': [],
        }
        
        try:
            config = ConfiguracionAlerta.objects.get(tipo_alerta=tipo_alerta)
            
            if not config.activo:
                resultado['errores'].append("Configuración de alerta inactiva")
                return resultado
            
            if not forzar_envio and not config.debe_enviar_hoy(fecha_referencia):
                resultado['errores'].append("No es el día programado para este tipo de alerta")
                return resultado
            
            fecha_ref = fecha_referencia or timezone.now().date()
            alertas = self.obtener_alertas_por_tipo(
                tipo_alerta=tipo_alerta,
                fecha_referencia=fecha_ref,
                solo_criticas=config.solo_criticas
            )
            
            destinatarios = self.obtener_destinatarios(tipo_alerta)
            if not destinatarios:
                resultado['errores'].append("No hay destinatarios configurados")
                return resultado
            
            if not alertas:
                logger.info(f"No hay alertas de tipo {tipo_alerta} para enviar")
                resultado['errores'].append("No hay alertas para enviar")
                return resultado
            
            contenido = self.generar_contenido_email(tipo_alerta, alertas, fecha_ref)
            asunto = config.asunto or contenido['asunto']
            
            emails_destinatarios = [d.email for d in destinatarios]
            
            for destinatario in destinatarios:
                historial = HistorialEnvioEmail.objects.create(
                    tipo_alerta=tipo_alerta,
                    destinatario=destinatario.email,
                    asunto=asunto,
                    estado='PENDIENTE',
                    cantidad_alertas=len(alertas),
                )
                
                try:
                    exito = self.email_service.enviar_email(
                        destinatarios=[destinatario.email],
                        asunto=asunto,
                        contenido_html=contenido['contenido_html'],
                    )
                    
                    if exito:
                        historial.estado = 'ENVIADO'
                        historial.fecha_envio = timezone.now()
                        historial.save()
                        resultado['destinatarios'] += 1
                    else:
                        historial.estado = 'ERROR'
                        historial.error_mensaje = "Error al enviar el correo"
                        historial.save()
                        resultado['errores'].append(f"Error al enviar a {destinatario.email}")
                        
                except Exception as e:
                    historial.estado = 'ERROR'
                    historial.error_mensaje = str(e)
                    historial.save()
                    resultado['errores'].append(f"Error al enviar a {destinatario.email}: {str(e)}")
                    logger.error(f"Error al enviar alerta a {destinatario.email}: {str(e)}", exc_info=True)
            
            if resultado['destinatarios'] > 0:
                resultado['enviado'] = True
                resultado['alertas_enviadas'] = len(alertas)
            
        except ConfiguracionAlerta.DoesNotExist:
            resultado['errores'].append(f"No existe configuración para el tipo de alerta: {tipo_alerta}")
        except Exception as e:
            resultado['errores'].append(f"Error general: {str(e)}")
            logger.error(f"Error al enviar alertas de tipo {tipo_alerta}: {str(e)}", exc_info=True)
        
        return resultado
    
    def enviar_todas_alertas_programadas(
        self,
        fecha_referencia: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Envía todas las alertas programadas para la fecha indicada.
        
        Args:
            fecha_referencia: Fecha de referencia (por defecto hoy)
        
        Returns:
            Lista de resultados por tipo de alerta
        """
        fecha_ref = fecha_referencia or timezone.now().date()
        resultados = []
        
        configuraciones = ConfiguracionAlerta.objects.filter(activo=True)
        
        for config in configuraciones:
            if config.debe_enviar_hoy(fecha_ref):
                resultado = self.enviar_alertas_tipo(
                    tipo_alerta=config.tipo_alerta,
                    fecha_referencia=fecha_ref,
                    forzar_envio=False
                )
                resultados.append(resultado)
        
        return resultados

