"""
Script interactivo para configurar el sistema de alertas por email.
Guía paso a paso para configurar email SMTP, alertas y destinatarios.
"""

import os
import sys
import django
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from django.utils import timezone
from gestion.models import ConfiguracionEmail, ConfiguracionAlerta, DestinatarioAlerta
from gestion.utils_encryption import generate_encryption_key, get_encryption_key
from django.conf import settings


def verificar_encryption_key():
    """Verifica si existe ENCRYPTION_KEY configurada"""
    print("\n" + "="*60)
    print("VERIFICACIÓN DE CLAVE DE ENCRIPTACIÓN")
    print("="*60)
    
    try:
        key = get_encryption_key()
        print("✓ Clave de encriptación configurada correctamente")
        return True
    except ValueError as e:
        print("⚠ ADVERTENCIA: No hay clave de encriptación configurada")
        print(f"  Error: {str(e)}")
        print("\nPara configurar la clave de encriptación:")
        print("1. Generar una nueva clave ejecutando:")
        print("   python -c \"from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())\"")
        print("\n2. Agregar al archivo .env:")
        print("   ENCRYPTION_KEY=tu-clave-generada-aqui")
        print("\n3. O configurar como variable de entorno del sistema")
        return False


def configurar_email_interactivo():
    """Guía interactiva para configurar email SMTP"""
    print("\n" + "="*60)
    print("CONFIGURACIÓN DE EMAIL SMTP")
    print("="*60)
    
    config_existente = ConfiguracionEmail.get_activa()
    
    if config_existente:
        print(f"\n✓ Ya existe una configuración activa: {config_existente.nombre}")
        respuesta = input("¿Desea crear una nueva configuración? (s/n): ").strip().lower()
        if respuesta != 's':
            print("Configuración existente mantenida.")
            return config_existente
    
    print("\nVamos a configurar el servidor SMTP para envío de correos.")
    print("\nEjemplos comunes:")
    print("  Gmail: smtp.gmail.com, puerto 587 (TLS) o 465 (SSL)")
    print("  Outlook: smtp-mail.outlook.com, puerto 587 (TLS)")
    print("  Office365: smtp.office365.com, puerto 587 (TLS)")
    
    print("\n" + "-"*60)
    nombre = input("\nNombre descriptivo (ej: 'Gmail Principal'): ").strip()
    if not nombre:
        print("❌ El nombre es requerido")
        return None
    
    email_host = input("Servidor SMTP (ej: smtp.gmail.com): ").strip()
    if not email_host:
        print("❌ El servidor SMTP es requerido")
        return None
    
    try:
        email_port = int(input("Puerto SMTP (587 para TLS, 465 para SSL): ").strip() or "587")
    except ValueError:
        print("❌ Puerto inválido, usando 587 por defecto")
        email_port = 587
    
    usar_tls = input("¿Usar TLS? (s/n, por defecto s): ").strip().lower() != 'n'
    usar_ssl = input("¿Usar SSL? (s/n, por defecto n): ").strip().lower() == 's'
    
    email_host_user = input("Usuario/Email SMTP: ").strip()
    if not email_host_user:
        print("❌ El usuario/email es requerido")
        return None
    
    print("\n⚠ IMPORTANTE: Para Gmail, debes usar una 'Contraseña de aplicación'")
    print("  No uses tu contraseña normal. Genera una en:")
    print("  https://myaccount.google.com/apppasswords")
    
    password = input("Contraseña o token de aplicación: ").strip()
    if not password:
        print("❌ La contraseña es requerida")
        return None
    
    email_from = input("Email remitente (por defecto igual al usuario): ").strip() or email_host_user
    
    nombre_remitente = input("Nombre del remitente (opcional): ").strip()
    
    try:
        config = ConfiguracionEmail(
            nombre=nombre,
            email_host=email_host,
            email_port=email_port,
            email_use_tls=usar_tls,
            email_use_ssl=usar_ssl,
            email_host_user=email_host_user,
            email_from=email_from,
            nombre_remitente=nombre_remitente or None,
            activo=True
        )
        
        config.set_password(password)
        config.save()
        
        print(f"\n✓ Configuración creada exitosamente: {config.nombre}")
        return config
        
    except Exception as e:
        print(f"\n❌ Error al crear configuración: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def listar_tipos_alertas():
    """Lista los tipos de alertas disponibles"""
    tipos = [
        ('VENCIMIENTO_CONTRATOS', 'Vencimiento de Contratos'),
        ('ALERTAS_IPC', 'Alertas IPC'),
        ('POLIZAS_CRITICAS', 'Pólizas Críticas'),
        ('PREAVISO_RENOVACION', 'Preaviso de Renovación'),
        ('POLIZAS_REQUERIDAS', 'Pólizas Requeridas No Aportadas'),
        ('TERMINACION_ANTICIPADA', 'Terminación Anticipada'),
        ('RENOVACION_AUTOMATICA', 'Renovación Automática'),
    ]
    return tipos


def configurar_alertas_interactivo():
    """Guía interactiva para configurar alertas"""
    print("\n" + "="*60)
    print("CONFIGURACIÓN DE ALERTAS")
    print("="*60)
    
    tipos = listar_tipos_alertas()
    
    print("\nTipos de alerta disponibles:")
    for i, (codigo, nombre) in enumerate(tipos, 1):
        config_existente = ConfiguracionAlerta.objects.filter(tipo_alerta=codigo).first()
        estado = "✓ Configurada" if config_existente else "✗ No configurada"
        print(f"  {i}. {nombre} - {estado}")
    
    print("\n¿Qué tipo de alerta deseas configurar?")
    print("  (Ingresa el número o 'todos' para configurar todas)")
    
    seleccion = input("Selección: ").strip().lower()
    
    tipos_a_configurar = []
    
    if seleccion == 'todos':
        tipos_a_configurar = tipos
    else:
        try:
            indice = int(seleccion) - 1
            if 0 <= indice < len(tipos):
                tipos_a_configurar = [tipos[indice]]
            else:
                print("❌ Opción inválida")
                return
        except ValueError:
            print("❌ Debe ingresar un número o 'todos'")
            return
    
    for codigo, nombre in tipos_a_configurar:
        config_existente = ConfiguracionAlerta.objects.filter(tipo_alerta=codigo).first()
        
        if config_existente:
            print(f"\n⚠ Ya existe configuración para: {nombre}")
            respuesta = input("¿Desea modificarla? (s/n): ").strip().lower()
            if respuesta != 's':
                continue
            config = config_existente
        else:
            config = ConfiguracionAlerta(tipo_alerta=codigo)
        
        print(f"\n--- Configurando: {nombre} ---")
        
        activo = input("¿Activar esta alerta? (s/n, por defecto s): ").strip().lower() != 'n'
        config.activo = activo
        
        print("\nFrecuencia de envío:")
        print("  1. INMEDIATO - Se envía siempre que se ejecute el comando")
        print("  2. DIARIO - Se envía todos los días")
        print("  3. SEMANAL - Se envía en días específicos de la semana")
        print("  4. MENSUAL - Se envía el día 1 de cada mes")
        
        try:
            opcion_frecuencia = int(input("Seleccione frecuencia (1-4, por defecto 3): ").strip() or "3")
            frecuencias = ['INMEDIATO', 'DIARIO', 'SEMANAL', 'MENSUAL']
            if 1 <= opcion_frecuencia <= 4:
                config.frecuencia = frecuencias[opcion_frecuencia - 1]
            else:
                config.frecuencia = 'SEMANAL'
        except ValueError:
            config.frecuencia = 'SEMANAL'
        
        if config.frecuencia == 'SEMANAL':
            print("\nDías de la semana (separados por comas):")
            print("  0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves")
            print("  4=Viernes, 5=Sábado, 6=Domingo")
            print("  Ejemplo: 0,3 para Lunes y Jueves")
            
            dias_input = input("Días (por defecto 0=Lunes): ").strip() or "0"
            try:
                dias = [int(d.strip()) for d in dias_input.split(',')]
                config.dias_semana = dias
            except ValueError:
                config.dias_semana = [0]
        
        hora = input("Hora de envío (formato HH:MM, por defecto 08:00): ").strip() or "08:00"
        try:
            from datetime import time
            hora_parts = hora.split(':')
            config.hora_envio = time(int(hora_parts[0]), int(hora_parts[1]))
        except:
            from datetime import time
            config.hora_envio = time(8, 0)
        
        solo_criticas = input("¿Solo alertas críticas? (s/n, por defecto n): ").strip().lower() == 's'
        config.solo_criticas = solo_criticas
        
        asunto = input("Asunto personalizado (opcional, Enter para usar por defecto): ").strip()
        config.asunto = asunto if asunto else None
        
        try:
            config.save()
            print(f"✓ Configuración guardada para: {nombre}")
        except Exception as e:
            print(f"❌ Error al guardar: {str(e)}")


def configurar_destinatarios_interactivo():
    """Guía interactiva para configurar destinatarios"""
    print("\n" + "="*60)
    print("CONFIGURACIÓN DE DESTINATARIOS")
    print("="*60)
    
    configuraciones = ConfiguracionAlerta.objects.filter(activo=True).order_by('tipo_alerta')
    
    if not configuraciones:
        print("⚠ No hay configuraciones de alertas activas")
        print("  Primero debes configurar las alertas")
        return
    
    print("\nConfiguraciones de alertas activas:")
    for i, config in enumerate(configuraciones, 1):
        destinatarios_count = config.destinatarios.filter(activo=True).count()
        print(f"  {i}. {config.get_tipo_alerta_display()} ({destinatarios_count} destinatarios)")
    
    try:
        seleccion = int(input("\nSeleccione el número de la alerta: ").strip())
        if 1 <= seleccion <= len(configuraciones):
            config_alerta = configuraciones[seleccion - 1]
        else:
            print("❌ Opción inválida")
            return
    except ValueError:
        print("❌ Debe ingresar un número")
        return
    
    print(f"\n--- Agregando destinatarios para: {config_alerta.get_tipo_alerta_display()} ---")
    
    while True:
        email = input("\nEmail del destinatario (o Enter para terminar): ").strip()
        if not email:
            break
        
        nombre = input("Nombre del destinatario (opcional): ").strip()
        
        activo = input("¿Activar este destinatario? (s/n, por defecto s): ").strip().lower() != 'n'
        
        try:
            destinatario = DestinatarioAlerta(
                configuracion_alerta=config_alerta,
                email=email,
                nombre=nombre if nombre else None,
                activo=activo
            )
            destinatario.save()
            print(f"✓ Destinatario agregado: {email}")
        except Exception as e:
            print(f"❌ Error al agregar destinatario: {str(e)}")
        
        continuar = input("\n¿Agregar otro destinatario? (s/n): ").strip().lower()
        if continuar != 's':
            break


def mostrar_resumen():
    """Muestra un resumen de la configuración actual"""
    print("\n" + "="*60)
    print("RESUMEN DE CONFIGURACIÓN")
    print("="*60)
    
    config_email = ConfiguracionEmail.get_activa()
    
    if config_email:
        print(f"\n✓ Email SMTP: {config_email.nombre}")
        print(f"  Servidor: {config_email.email_host}:{config_email.email_port}")
        print(f"  Remitente: {config_email.email_from}")
    else:
        print("\n✗ No hay configuración de email activa")
    
    configuraciones = ConfiguracionAlerta.objects.filter(activo=True)
    
    if configuraciones:
        print(f"\n✓ Alertas configuradas: {configuraciones.count()}")
        for config in configuraciones:
            destinatarios_count = config.destinatarios.filter(activo=True).count()
            print(f"  - {config.get_tipo_alerta_display()}: {destinatarios_count} destinatario(s)")
    else:
        print("\n✗ No hay alertas configuradas")
    
    print("\n" + "-"*60)
    print("Próximos pasos:")
    print("1. Probar el envío: python scripts/prueba_email_rapida.py tu-email@ejemplo.com")
    print("2. O usar el script interactivo: python scripts/prueba_envio_email.py")
    print("3. Ver historial en: /admin/gestion/historialenvioemail/")


def menu_principal():
    """Menú principal del script de configuración"""
    while True:
        print("\n" + "="*60)
        print("CONFIGURACIÓN DE ALERTAS POR EMAIL")
        print("="*60)
        print("\nOpciones:")
        print("  1. Verificar clave de encriptación")
        print("  2. Configurar email SMTP")
        print("  3. Configurar alertas")
        print("  4. Configurar destinatarios")
        print("  5. Ver resumen de configuración")
        print("  6. Salir")
        
        try:
            opcion = input("\nSeleccione una opción: ").strip()
            
            if opcion == '1':
                verificar_encryption_key()
            elif opcion == '2':
                configurar_email_interactivo()
            elif opcion == '3':
                configurar_alertas_interactivo()
            elif opcion == '4':
                configurar_destinatarios_interactivo()
            elif opcion == '5':
                mostrar_resumen()
            elif opcion == '6':
                print("\n¡Hasta luego!")
                break
            else:
                print("❌ Opción inválida")
                
        except KeyboardInterrupt:
            print("\n\nOperación cancelada por el usuario")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    menu_principal()

