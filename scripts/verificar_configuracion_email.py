"""
Script para verificar el estado actual de la configuración de email.
No requiere interacción, solo muestra información.
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from gestion.models import ConfiguracionEmail, ConfiguracionAlerta, DestinatarioAlerta
from gestion.utils_encryption import get_encryption_key
from django.conf import settings


def main():
    print("\n" + "="*60)
    print("ESTADO DE CONFIGURACION DE EMAIL")
    print("="*60)
    
    # Verificar clave de encriptación
    print("\n1. CLAVE DE ENCRIPTACION:")
    try:
        key = get_encryption_key()
        print("   [OK] Clave de encriptacion configurada")
    except ValueError as e:
        print("   [ERROR] No hay clave de encriptacion configurada")
        print(f"   Mensaje: {str(e)}")
        print("\n   Para configurar:")
        print("   1. Ejecutar: python -c \"from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())\"")
        print("   2. Agregar al archivo .env: ENCRYPTION_KEY=clave-generada")
    
    # Verificar configuración de email
    print("\n2. CONFIGURACION DE EMAIL SMTP:")
    config_email = ConfiguracionEmail.get_activa()
    
    if config_email:
        print(f"   [OK] Configuracion activa: {config_email.nombre}")
        print(f"   Servidor: {config_email.email_host}:{config_email.email_port}")
        print(f"   Usuario: {config_email.email_host_user}")
        print(f"   Remitente: {config_email.email_from}")
        
        try:
            password = config_email.get_password()
            if password:
                print("   Contrasena: [CONFIGURADA]")
            else:
                print("   Contrasena: [NO CONFIGURADA]")
        except Exception as e:
            print(f"   Contrasena: [ERROR] {str(e)}")
    else:
        print("   [ERROR] No hay configuracion de email activa")
        print("\n   Para configurar:")
        print("   Opcion 1: Usar script interactivo: python scripts/configurar_email.py")
        print("   Opcion 2: Ir al admin: /admin/gestion/configuracionemail/add/")
    
    # Verificar configuraciones de alertas
    print("\n3. CONFIGURACIONES DE ALERTAS:")
    configuraciones = ConfiguracionAlerta.objects.all()
    
    if configuraciones:
        activas = configuraciones.filter(activo=True)
        print(f"   Total configuraciones: {configuraciones.count()}")
        print(f"   Activas: {activas.count()}")
        
        for config in activas:
            destinatarios_count = config.destinatarios.filter(activo=True).count()
            print(f"\n   - {config.get_tipo_alerta_display()}:")
            print(f"     Frecuencia: {config.get_frecuencia_display()}")
            print(f"     Destinatarios: {destinatarios_count}")
            
            if destinatarios_count == 0:
                print("     [ADVERTENCIA] No hay destinatarios configurados")
    else:
        print("   [ERROR] No hay configuraciones de alertas")
        print("\n   Para configurar:")
        print("   Opcion 1: Usar script interactivo: python scripts/configurar_email.py")
        print("   Opcion 2: Ir al admin: /admin/gestion/configuracionalerta/add/")
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    
    tiene_encryption_key = False
    try:
        get_encryption_key()
        tiene_encryption_key = True
    except:
        pass
    
    tiene_email = config_email is not None
    tiene_alertas = ConfiguracionAlerta.objects.filter(activo=True).exists()
    
    if tiene_encryption_key and tiene_email and tiene_alertas:
        print("\n[OK] Configuracion completa")
        print("\nPuedes probar el envio con:")
        print("  python scripts/prueba_email_rapida.py tu-email@ejemplo.com")
    else:
        print("\n[PENDIENTE] Configuracion incompleta")
        print("\nPasos pendientes:")
        if not tiene_encryption_key:
            print("  - Configurar ENCRYPTION_KEY")
        if not tiene_email:
            print("  - Configurar email SMTP")
        if not tiene_alertas:
            print("  - Configurar alertas")
        
        print("\nUsa el script interactivo para completar:")
        print("  python scripts/configurar_email.py")


if __name__ == '__main__':
    main()

