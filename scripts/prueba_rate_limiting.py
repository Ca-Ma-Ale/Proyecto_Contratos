"""
Script para probar el rate limiting (protección contra fuerza bruta)
Simula múltiples intentos de login fallidos para verificar el bloqueo
Ejecutar con: python scripts/prueba_rate_limiting.py
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
from axes.models import AccessAttempt
from django.conf import settings
import time

# Agregar testserver a ALLOWED_HOSTS para pruebas
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

print("=" * 70)
print("🔒 PRUEBA: Rate Limiting (Protección contra Fuerza Bruta)")
print("=" * 70)
print()

# Crear cliente de prueba
client = Client()

# Usuario de prueba (no debe existir)
username_test = "usuario_inexistente_test"
password_test = "contraseña_incorrecta"

print(f"🧪 Simulando intentos de login con usuario inexistente: {username_test}")
print(f"   Límite configurado: 5 intentos fallidos")
print()

intentos = 7  # Intentar más veces que el límite
bloqueado_en = None

for i in range(1, intentos + 1):
    print(f"Intento {i}/{intentos}... ", end="")
    
    # Intentar hacer login
    response = client.post('/login/', {
        'username': username_test,
        'password': password_test,
    }, follow=False)
    
    # Verificar si hay bloqueo de axes
    try:
        attempts = AccessAttempt.objects.filter(username=username_test)
        if attempts.exists():
            attempt = attempts.first()
            failures = attempt.failures_since_start
            
            if failures >= 5:
                if bloqueado_en is None:
                    bloqueado_en = i
                print(f"❌ BLOQUEADO (fallos: {failures})")
                
                # Verificar que la respuesta indica bloqueo
                if response.status_code == 403 or 'bloqueado' in response.content.decode('utf-8', errors='ignore').lower():
                    print("   ✅ El sistema está bloqueando correctamente")
                else:
                    print(f"   ⚠️  Código de respuesta: {response.status_code}")
            else:
                print(f"⚠️  Fallido (fallos acumulados: {failures})")
        else:
            print(f"⚠️  Fallido (intento registrado)")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Pequeña pausa entre intentos
    time.sleep(0.5)

print()
print("=" * 70)
print("📊 RESULTADO")
print("=" * 70)

if bloqueado_en:
    print(f"✅ Rate limiting funciona correctamente")
    print(f"   Usuario bloqueado después de {bloqueado_en} intentos")
    print(f"   El sistema está protegiendo contra ataques de fuerza bruta")
else:
    print(f"⚠️  No se detectó bloqueo después de {intentos} intentos")
    print(f"   Verificar configuración de django-axes")

print()
print("💡 Para limpiar los intentos de prueba, ejecuta:")
print("   python manage.py shell -c \"from axes.models import AccessAttempt; AccessAttempt.objects.filter(username='usuario_inexistente_test').delete()\"")
print()

