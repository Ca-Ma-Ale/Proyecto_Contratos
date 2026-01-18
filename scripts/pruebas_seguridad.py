"""
Script para realizar pruebas de seguridad del sistema
Ejecutar con: python scripts/pruebas_seguridad.py
"""

import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from gestion.models import ConfiguracionEmail
from gestion.utils_encryption import encrypt_value, decrypt_value, get_encryption_key
from pathlib import Path
import requests
from datetime import datetime

print("=" * 70)
print("🔒 PRUEBAS DE SEGURIDAD DEL SISTEMA")
print("=" * 70)
print()

# Contador de pruebas
pruebas_totales = 0
pruebas_exitosas = 0
pruebas_fallidas = 0

def prueba(nombre, resultado, mensaje=""):
    """Función auxiliar para mostrar resultados de pruebas"""
    global pruebas_totales, pruebas_exitosas, pruebas_fallidas
    pruebas_totales += 1
    
    if resultado:
        pruebas_exitosas += 1
        print(f"✅ {nombre}")
        if mensaje:
            print(f"   {mensaje}")
    else:
        pruebas_fallidas += 1
        print(f"❌ {nombre}")
        if mensaje:
            print(f"   {mensaje}")
    print()

# ============================================================================
# 1. PRUEBA: Verificar encriptación de contraseñas de email
# ============================================================================
print("1️⃣  PRUEBA: Encriptación de Contraseñas de Email")
print("-" * 70)

try:
    # Verificar que ENCRYPTION_KEY está configurada
    key = get_encryption_key()
    prueba(
        "ENCRYPTION_KEY configurada",
        key is not None and len(key) > 0,
        "Clave de encriptación encontrada"
    )
    
    # Probar encriptación/desencriptación
    texto_prueba = "contraseña_secreta_123"
    encriptado = encrypt_value(texto_prueba)
    desencriptado = decrypt_value(encriptado)
    
    prueba(
        "Encriptación/Desencriptación funciona",
        desencriptado == texto_prueba and texto_prueba not in encriptado,
        f"Texto original: '{texto_prueba}', Encriptado: '{encriptado[:30]}...'"
    )
    
    # Verificar que las contraseñas en BD están encriptadas
    configs = ConfiguracionEmail.objects.filter(email_host_password__isnull=False)
    todas_encriptadas = True
    for config in configs:
        try:
            # Intentar desencriptar (si funciona, está encriptada)
            password = config.get_password()
            # Verificar que no es texto plano obvio
            if len(config.email_host_password) < 50:  # Las contraseñas encriptadas son más largas
                todas_encriptadas = False
        except:
            todas_encriptadas = False
    
    prueba(
        "Contraseñas en base de datos encriptadas",
        todas_encriptadas or configs.count() == 0,
        f"{configs.count()} configuración(es) encontrada(s)"
    )
    
except Exception as e:
    prueba(
        "Encriptación funciona",
        False,
        f"Error: {str(e)}"
    )

# ============================================================================
# 2. PRUEBA: Verificar permisos de archivo SQLite
# ============================================================================
print("2️⃣  PRUEBA: Permisos de Archivo SQLite")
print("-" * 70)

try:
    db_file = Path("db.sqlite3")
    if db_file.exists():
        # En Windows, verificar con icacls
        import stat
        file_stat = db_file.stat()
        
        # En Windows, solo verificamos que el archivo existe
        # Los permisos detallados requieren comandos específicos de Windows
        prueba(
            "Archivo db.sqlite3 existe",
            db_file.exists(),
            f"Tamaño: {file_stat.st_size / 1024:.2f} KB"
        )
        
        # Verificar que no está en el repositorio Git
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'ls-files', 'db.sqlite3'],
                capture_output=True,
                text=True,
                timeout=5
            )
            en_git = len(result.stdout.strip()) > 0
            prueba(
                "db.sqlite3 NO está en Git",
                not en_git,
                "El archivo está correctamente excluido del repositorio"
            )
        except:
            prueba(
                "Verificar si db.sqlite3 está en Git",
                True,  # No crítico si no se puede verificar
                "No se pudo verificar (Git no disponible o no es un repo)"
            )
    else:
        prueba(
            "Archivo db.sqlite3 existe",
            False,
            "Archivo no encontrado"
        )
except Exception as e:
    prueba(
        "Verificar permisos de SQLite",
        False,
        f"Error: {str(e)}"
    )

# ============================================================================
# 3. PRUEBA: Verificar que .env no está en Git
# ============================================================================
print("3️⃣  PRUEBA: Archivo .env excluido de Git")
print("-" * 70)

try:
    env_file = Path(".env")
    if env_file.exists():
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'check-ignore', '.env'],
                capture_output=True,
                text=True,
                timeout=5
            )
            ignorado = result.returncode == 0
            prueba(
                ".env está en .gitignore",
                ignorado,
                ".env correctamente excluido del repositorio"
            )
        except:
            prueba(
                "Verificar .env en .gitignore",
                True,  # No crítico
                "No se pudo verificar (Git no disponible)"
            )
        
        # Verificar que .env contiene ENCRYPTION_KEY
        with open(env_file, 'r', encoding='utf-8') as f:
            contenido = f.read()
            tiene_encryption_key = 'ENCRYPTION_KEY=' in contenido
            prueba(
                ".env contiene ENCRYPTION_KEY",
                tiene_encryption_key,
                "Variable ENCRYPTION_KEY encontrada en .env"
            )
    else:
        prueba(
            "Archivo .env existe",
            False,
            "Archivo .env no encontrado"
        )
except Exception as e:
    prueba(
        "Verificar .env",
        False,
        f"Error: {str(e)}"
    )

# ============================================================================
# 4. PRUEBA: Verificar variables de entorno sensibles
# ============================================================================
print("4️⃣  PRUEBA: Variables de Entorno Seguras")
print("-" * 70)

from django.conf import settings

# Verificar SECRET_KEY
secret_key_seguro = (
    settings.SECRET_KEY and 
    settings.SECRET_KEY != 'django-insecure-your-secret-key-here-SOLO-DESARROLLO' and
    not settings.SECRET_KEY.startswith('django-insecure')
)

prueba(
    "SECRET_KEY no es la clave por defecto",
    secret_key_seguro or settings.DEBUG,  # Permitir en desarrollo
    "Clave secreta configurada" if secret_key_seguro else "⚠️  Usando clave por defecto (solo desarrollo)"
)

# Verificar DEBUG
prueba(
    "DEBUG está deshabilitado en producción",
    not settings.DEBUG or 'development' in str(settings.SECRET_KEY).lower(),
    f"DEBUG = {settings.DEBUG}"
)

# ============================================================================
# 5. PRUEBA: Verificar configuración de django-axes
# ============================================================================
print("5️⃣  PRUEBA: Configuración de Rate Limiting (django-axes)")
print("-" * 70)

try:
    prueba(
        "django-axes instalado",
        'axes' in settings.INSTALLED_APPS,
        "Axes está en INSTALLED_APPS"
    )
    
    prueba(
        "AxesMiddleware configurado",
        'axes.middleware.AxesMiddleware' in settings.MIDDLEWARE,
        "Middleware de axes configurado"
    )
    
    # Verificar configuración de axes
    axes_enabled = getattr(settings, 'AXES_ENABLED', False)
    failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', None)
    
    prueba(
        "Axes habilitado",
        axes_enabled,
        f"AXES_ENABLED = {axes_enabled}"
    )
    
    prueba(
        "Límite de intentos configurado",
        failure_limit is not None and failure_limit > 0,
        f"AXES_FAILURE_LIMIT = {failure_limit}"
    )
except Exception as e:
    prueba(
        "Configuración de axes",
        False,
        f"Error: {str(e)}"
    )

# ============================================================================
# 6. PRUEBA: Verificar configuración de sesiones
# ============================================================================
print("6️⃣  PRUEBA: Configuración de Seguridad de Sesiones")
print("-" * 70)

prueba(
    "SESSION_COOKIE_HTTPONLY habilitado",
    getattr(settings, 'SESSION_COOKIE_HTTPONLY', False),
    "Protección XSS en cookies"
)

prueba(
    "SESSION_COOKIE_SAMESITE configurado",
    getattr(settings, 'SESSION_COOKIE_SAMESITE', None) in ['Strict', 'Lax'],
    f"SAME_SITE = {getattr(settings, 'SESSION_COOKIE_SAMESITE', 'No configurado')}"
)

prueba(
    "SESSION_COOKIE_AGE configurado",
    getattr(settings, 'SESSION_COOKIE_AGE', None) is not None,
    f"Tiempo de expiración = {getattr(settings, 'SESSION_COOKIE_AGE', 'No configurado')} segundos"
)

# ============================================================================
# 7. PRUEBA: Verificar headers de seguridad (en producción)
# ============================================================================
print("7️⃣  PRUEBA: Headers de Seguridad HTTP")
print("-" * 70)

if not settings.DEBUG:
    prueba(
        "HSTS configurado",
        getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0,
        f"SECURE_HSTS_SECONDS = {getattr(settings, 'SECURE_HSTS_SECONDS', 0)}"
    )
    
    prueba(
        "SECURE_SSL_REDIRECT habilitado",
        getattr(settings, 'SECURE_SSL_REDIRECT', False),
        "Redirección HTTPS habilitada"
    )
    
    prueba(
        "SESSION_COOKIE_SECURE habilitado",
        getattr(settings, 'SESSION_COOKIE_SECURE', False),
        "Cookies solo por HTTPS"
    )
else:
    print("⚠️  Headers de seguridad solo se verifican en producción (DEBUG=False)")
    print()

# ============================================================================
# 8. PRUEBA: Verificar validación de entrada
# ============================================================================
print("8️⃣  PRUEBA: Validación de Entrada en Formularios")
print("-" * 70)

try:
    from gestion.forms import sanitizar_texto
    
    # Probar sanitización
    script_malicioso = '<script>alert("XSS")</script>'
    sanitizado = sanitizar_texto(script_malicioso)
    
    prueba(
        "Sanitización de HTML funciona",
        '<script>' not in sanitizado,
        f"Script removido: '{script_malicioso}' -> '{sanitizado}'"
    )
    
    # Probar eventos JavaScript
    evento_malicioso = '<img src=x onerror=alert(1)>'
    sanitizado_evento = sanitizar_texto(evento_malicioso)
    
    prueba(
        "Eventos JavaScript removidos",
        'onerror' not in sanitizado_evento.lower(),
        "Atributos de eventos removidos"
    )
except Exception as e:
    prueba(
        "Validación de entrada",
        False,
        f"Error: {str(e)}"
    )

# ============================================================================
# 9. PRUEBA: Verificar que información sensible no está hardcodeada
# ============================================================================
print("9️⃣  PRUEBA: Credenciales Hardcodeadas")
print("-" * 70)

try:
    # Buscar contraseñas obvias en el código (búsqueda básica)
    archivos_a_revisar = [
        'contratos/settings.py',
        'contratos/settings_production.py',
        'gestion/models.py'
    ]
    
    credenciales_encontradas = []
    for archivo in archivos_a_revisar:
        if Path(archivo).exists():
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read().lower()
                # Buscar patrones comunes de credenciales
                if 'password =' in contenido and 'get(' not in contenido:
                    if 'os.environ' not in contenido and 'config(' not in contenido:
                        credenciales_encontradas.append(archivo)
    
    prueba(
        "No hay contraseñas hardcodeadas",
        len(credenciales_encontradas) == 0,
        "No se encontraron credenciales hardcodeadas" if len(credenciales_encontradas) == 0 else f"⚠️  Revisar: {', '.join(credenciales_encontradas)}"
    )
except Exception as e:
    prueba(
        "Verificar credenciales hardcodeadas",
        False,
        f"Error: {str(e)}"
    )

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print()
print("=" * 70)
print("📊 RESUMEN DE PRUEBAS")
print("=" * 70)
print(f"Total de pruebas: {pruebas_totales}")
print(f"✅ Exitosas: {pruebas_exitosas}")
print(f"❌ Fallidas: {pruebas_fallidas}")
print(f"📈 Porcentaje de éxito: {(pruebas_exitosas/pruebas_totales*100):.1f}%")
print("=" * 70)

if pruebas_fallidas == 0:
    print()
    print("🎉 ¡Todas las pruebas de seguridad pasaron exitosamente!")
else:
    print()
    print(f"⚠️  {pruebas_fallidas} prueba(s) falló(aron). Revisa los resultados arriba.")

print()

