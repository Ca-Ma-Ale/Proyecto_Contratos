"""
Script para probar headers de seguridad HTTP
Solo funciona cuando el servidor está corriendo
Ejecutar con: python scripts/prueba_headers_seguridad.py
"""

import requests
import sys

print("=" * 70)
print("🔒 PRUEBA: Headers de Seguridad HTTP")
print("=" * 70)
print()

url = "http://localhost:8000/"
print(f"📡 Probando URL: {url}")
print("⚠️  Asegúrate de que el servidor Django esté corriendo")
print()

try:
    response = requests.get(url, timeout=5, allow_redirects=True)
    
    headers = response.headers
    
    print("=" * 70)
    print("📋 HEADERS ENCONTRADOS:")
    print("=" * 70)
    
    headers_seguridad = {
        'Strict-Transport-Security': 'HSTS',
        'X-Content-Type-Options': 'Prevención de MIME sniffing',
        'X-Frame-Options': 'Protección Clickjacking',
        'X-XSS-Protection': 'Protección XSS',
        'Content-Security-Policy': 'CSP',
        'Referrer-Policy': 'Política de Referrer',
    }
    
    encontrados = []
    no_encontrados = []
    
    for header, descripcion in headers_seguridad.items():
        if header in headers:
            print(f"✅ {header}: {headers[header]}")
            print(f"   {descripcion}")
            encontrados.append(header)
        else:
            print(f"❌ {header}: No configurado")
            no_encontrados.append(header)
        print()
    
    # Verificar otros headers importantes
    if 'Set-Cookie' in headers:
        cookie_header = headers['Set-Cookie']
        print("🍪 Cookies:")
        if 'HttpOnly' in cookie_header:
            print("   ✅ HttpOnly presente")
        else:
            print("   ❌ HttpOnly NO presente")
        
        if 'SameSite' in cookie_header:
            print(f"   ✅ SameSite presente: {cookie_header}")
        else:
            print("   ⚠️  SameSite no visible en header (puede estar configurado)")
        print()
    
    print("=" * 70)
    print("📊 RESUMEN")
    print("=" * 70)
    print(f"Headers de seguridad encontrados: {len(encontrados)}/{len(headers_seguridad)}")
    print(f"✅ Configurados: {', '.join(encontrados) if encontrados else 'Ninguno'}")
    if no_encontrados:
        print(f"❌ Faltantes: {', '.join(no_encontrados)}")
    print()
    
    if len(encontrados) == len(headers_seguridad):
        print("🎉 ¡Todos los headers de seguridad están configurados!")
    elif len(encontrados) >= len(headers_seguridad) // 2:
        print("⚠️  Algunos headers de seguridad faltan. Revisa la configuración.")
    else:
        print("❌ La mayoría de headers de seguridad faltan. Revisa settings_production.py")
    
except requests.exceptions.ConnectionError:
    print("❌ Error: No se pudo conectar al servidor")
    print("   Asegúrate de que Django esté corriendo:")
    print("   python manage.py runserver")
except Exception as e:
    print(f"❌ Error: {str(e)}")

print()

