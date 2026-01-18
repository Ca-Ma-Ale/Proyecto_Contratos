#!/usr/bin/env python
"""
Script de verificación pre-deployment para PythonAnywhere
Verifica que todo esté configurado correctamente antes del despliegue
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def verificar_archivos_requeridos():
    """Verifica que existan los archivos necesarios"""
    print("=" * 60)
    print("VERIFICACIÓN DE ARCHIVOS REQUERIDOS")
    print("=" * 60)
    
    archivos_requeridos = [
        'manage.py',
        'requirements.txt',
        'contratos/settings.py',
        'contratos/settings_production.py',
        'contratos/wsgi.py',
        'contratos/urls.py',
        'env_example.txt',
        '.gitignore',
    ]
    
    errores = []
    for archivo in archivos_requeridos:
        ruta = BASE_DIR / archivo
        if ruta.exists():
            print(f"[OK] {archivo}")
        else:
            print(f"[ERROR] {archivo} - NO ENCONTRADO")
            errores.append(archivo)
    
    return errores

def verificar_directorios():
    """Verifica que existan los directorios necesarios"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE DIRECTORIOS")
    print("=" * 60)
    
    directorios = [
        'logs',
        'static',
        'templates',
        'gestion',
    ]
    
    errores = []
    for directorio in directorios:
        ruta = BASE_DIR / directorio
        if ruta.exists() and ruta.is_dir():
            print(f"[OK] {directorio}/")
        else:
            print(f"[ERROR] {directorio}/ - NO ENCONTRADO")
            errores.append(directorio)
    
    return errores

def verificar_settings_production():
    """Verifica la configuración de settings_production.py"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE SETTINGS_PRODUCTION.PY")
    print("=" * 60)
    
    errores = []
    advertencias = []
    
    try:
        sys.path.insert(0, str(BASE_DIR))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings_production')
        
        # Intentar importar settings
        from django.conf import settings
        
        # Verificar DEBUG
        if settings.DEBUG:
            advertencias.append("DEBUG está en True - debe ser False en producción")
            print("[ADVERTENCIA] DEBUG = True (debe ser False en producción)")
        else:
            print("[OK] DEBUG = False")
        
        # Verificar SECRET_KEY
        if not settings.SECRET_KEY or settings.SECRET_KEY == 'django-insecure-your-secret-key-here-SOLO-DESARROLLO':
            errores.append("SECRET_KEY no configurada o insegura")
            print("[ERROR] SECRET_KEY no configurada o insegura")
        else:
            print("[OK] SECRET_KEY configurada")
        
        # Verificar ALLOWED_HOSTS
        if not settings.ALLOWED_HOSTS:
            advertencias.append("ALLOWED_HOSTS está vacío")
            print("[ADVERTENCIA] ALLOWED_HOSTS está vacío")
        else:
            print(f"[OK] ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        
        # Verificar INSTALLED_APPS
        apps_requeridos = [
            'django.contrib.humanize',
            'axes',
            'gestion',
        ]
        for app in apps_requeridos:
            if app in settings.INSTALLED_APPS:
                print(f"[OK] {app} en INSTALLED_APPS")
            else:
                errores.append(f"{app} no está en INSTALLED_APPS")
                print(f"[ERROR] {app} NO está en INSTALLED_APPS")
        
        # Verificar STATIC_ROOT
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            print(f"[OK] STATIC_ROOT configurado: {settings.STATIC_ROOT}")
        else:
            advertencias.append("STATIC_ROOT no configurado")
            print("[ADVERTENCIA] STATIC_ROOT no configurado")
        
        # Verificar MEDIA_ROOT
        if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
            print(f"[OK] MEDIA_ROOT configurado: {settings.MEDIA_ROOT}")
        else:
            advertencias.append("MEDIA_ROOT no configurado")
            print("[ADVERTENCIA] MEDIA_ROOT no configurado")
        
    except ImportError as e:
        advertencias.append("Django no está instalado - no se puede verificar settings")
        print("[ADVERTENCIA] Django no está instalado - no se puede verificar settings")
    except Exception as e:
        errores.append(f"Error al verificar settings: {str(e)}")
        print(f"[ERROR] Error al verificar settings: {str(e)}")
    
    return errores, advertencias

def verificar_requirements():
    """Verifica que requirements.txt tenga las dependencias necesarias"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE REQUIREMENTS.TXT")
    print("=" * 60)
    
    errores = []
    requerimientos = [
        'Django',
        'gunicorn',
        'python-decouple',
        'django-axes',
        'cryptography',
    ]
    
    try:
        with open(BASE_DIR / 'requirements.txt', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        for req in requerimientos:
            if req.lower() in contenido.lower():
                print(f"[OK] {req}")
            else:
                errores.append(f"{req} no encontrado en requirements.txt")
                print(f"[ERROR] {req} NO encontrado en requirements.txt")
    except Exception as e:
        errores.append(f"Error al leer requirements.txt: {str(e)}")
        print(f"❌ Error al leer requirements.txt: {str(e)}")
    
    return errores

def verificar_env_example():
    """Verifica que env_example.txt tenga las variables necesarias"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE ENV_EXAMPLE.TXT")
    print("=" * 60)
    
    errores = []
    variables = [
        'SECRET_KEY',
        'DEBUG',
        'ALLOWED_HOSTS',
        'CSRF_TRUSTED_ORIGINS',
    ]
    
    try:
        with open(BASE_DIR / 'env_example.txt', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        for var in variables:
            if var in contenido:
                print(f"[OK] {var}")
            else:
                errores.append(f"{var} no encontrado en env_example.txt")
                print(f"[ERROR] {var} NO encontrado en env_example.txt")
    except Exception as e:
        errores.append(f"Error al leer env_example.txt: {str(e)}")
        print(f"❌ Error al leer env_example.txt: {str(e)}")
    
    return errores

def verificar_gitignore():
    """Verifica que .gitignore excluya archivos sensibles"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE .GITIGNORE")
    print("=" * 60)
    
    errores = []
    exclusiones = [
        '.env',
        'db.sqlite3',
        '__pycache__',
        '*.log',
        'venv',
    ]
    
    try:
        with open(BASE_DIR / '.gitignore', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        for exclusion in exclusiones:
            if exclusion in contenido:
                print(f"[OK] {exclusion} está en .gitignore")
            else:
                advertencia = f"{exclusion} debería estar en .gitignore"
                print(f"[ADVERTENCIA] {advertencia}")
    except Exception as e:
        errores.append(f"Error al leer .gitignore: {str(e)}")
        print(f"❌ Error al leer .gitignore: {str(e)}")
    
    return errores

def verificar_wsgi():
    """Verifica que wsgi.py esté configurado"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE WSGI.PY")
    print("=" * 60)
    
    errores = []
    
    try:
        with open(BASE_DIR / 'contratos' / 'wsgi.py', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        if 'get_wsgi_application' in contenido:
            print("[OK] get_wsgi_application importado")
        else:
            errores.append("get_wsgi_application no encontrado en wsgi.py")
            print("[ERROR] get_wsgi_application NO encontrado")
        
        if 'DJANGO_SETTINGS_MODULE' in contenido:
            print("[OK] DJANGO_SETTINGS_MODULE configurado")
        else:
            errores.append("DJANGO_SETTINGS_MODULE no configurado")
            print("[ERROR] DJANGO_SETTINGS_MODULE NO configurado")
        
    except Exception as e:
        errores.append(f"Error al leer wsgi.py: {str(e)}")
        print(f"❌ Error al leer wsgi.py: {str(e)}")
    
    return errores

def main():
    """Ejecuta todas las verificaciones"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN PRE-DEPLOYMENT PARA PYTHONANYWHERE")
    print("=" * 60)
    print()
    
    todos_errores = []
    todas_advertencias = []
    
    # Verificaciones
    errores = verificar_archivos_requeridos()
    todos_errores.extend(errores)
    
    errores = verificar_directorios()
    todos_errores.extend(errores)
    
    errores, advertencias = verificar_settings_production()
    todos_errores.extend(errores)
    todas_advertencias.extend(advertencias)
    
    errores = verificar_requirements()
    todos_errores.extend(errores)
    
    errores = verificar_env_example()
    todos_errores.extend(errores)
    
    errores = verificar_gitignore()
    todos_errores.extend(errores)
    
    errores = verificar_wsgi()
    todos_errores.extend(errores)
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    if todos_errores:
        print(f"\n[ERROR] ERRORES ENCONTRADOS: {len(todos_errores)}")
        for error in todos_errores:
            print(f"  - {error}")
    else:
        print("\n[OK] No se encontraron errores críticos")
    
    if todas_advertencias:
        print(f"\n[ADVERTENCIA] ADVERTENCIAS: {len(todas_advertencias)}")
        for advertencia in todas_advertencias:
            print(f"  - {advertencia}")
    else:
        print("\n[OK] No se encontraron advertencias")
    
    print("\n" + "=" * 60)
    if todos_errores:
        print("[ERROR] EL PROYECTO NO ESTÁ LISTO PARA DESPLIEGUE")
        print("Corrige los errores antes de continuar")
        sys.exit(1)
    else:
        print("[OK] EL PROYECTO ESTÁ LISTO PARA DESPLIEGUE")
        if todas_advertencias:
            print("Revisa las advertencias antes de desplegar")
        sys.exit(0)

if __name__ == '__main__':
    main()

