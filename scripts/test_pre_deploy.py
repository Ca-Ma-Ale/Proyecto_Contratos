#!/usr/bin/env python
"""
Script completo de test pre-deployment para producción
Verifica que todo esté configurado correctamente antes del despliegue
"""

import os
import sys
import re
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
        
        # Verificar que SECRET_KEY esté configurada antes de importar settings
        secret_key_temp = os.environ.get('SECRET_KEY')
        if not secret_key_temp:
            advertencias.append("SECRET_KEY no configurada en entorno - requerida en producción")
            print("[ADVERTENCIA] SECRET_KEY no configurada en entorno (requerida en producción)")
            # Usar una temporal solo para verificar la configuración
            os.environ['SECRET_KEY'] = 'temp-key-for-testing-only'
        
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings_production')
        
        from django.conf import settings
        
        if settings.DEBUG:
            advertencias.append("DEBUG está en True - debe ser False en producción")
            print("[ADVERTENCIA] DEBUG = True (debe ser False en producción)")
        else:
            print("[OK] DEBUG = False")
        
        if not secret_key_temp:
            print("[OK] SECRET_KEY será requerida en producción (correcto)")
        else:
            print("[OK] SECRET_KEY configurada")
        
        if not settings.ALLOWED_HOSTS:
            advertencias.append("ALLOWED_HOSTS está vacío")
            print("[ADVERTENCIA] ALLOWED_HOSTS está vacío")
        else:
            print(f"[OK] ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        
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
        
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            print(f"[OK] STATIC_ROOT configurado: {settings.STATIC_ROOT}")
        else:
            advertencias.append("STATIC_ROOT no configurado")
            print("[ADVERTENCIA] STATIC_ROOT no configurado")
        
        if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
            print(f"[OK] MEDIA_ROOT configurado: {settings.MEDIA_ROOT}")
        else:
            advertencias.append("MEDIA_ROOT no configurado")
            print("[ADVERTENCIA] MEDIA_ROOT no configurado")
        
        if not settings.DEBUG:
            if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
                advertencias.append("SECURE_SSL_REDIRECT no está habilitado")
                print("[ADVERTENCIA] SECURE_SSL_REDIRECT no está habilitado")
            else:
                print("[OK] SECURE_SSL_REDIRECT habilitado")
        
    except ImportError as e:
        advertencias.append("Django no está instalado - no se puede verificar settings")
        print(f"[ADVERTENCIA] Django no está instalado: {str(e)}")
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
        print(f"[ERROR] Error al leer requirements.txt: {str(e)}")
    
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
        print(f"[ERROR] Error al leer env_example.txt: {str(e)}")
    
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
                print(f"[ADVERTENCIA] {exclusion} debería estar en .gitignore")
    except Exception as e:
        errores.append(f"Error al leer .gitignore: {str(e)}")
        print(f"[ERROR] Error al leer .gitignore: {str(e)}")
    
    return errores

def verificar_wsgi():
    """Verifica que wsgi.py esté configurado correctamente"""
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
        
        if 'settings_production' in contenido:
            print("[OK] wsgi.py usa settings_production")
        elif 'DJANGO_SETTINGS_MODULE' in contenido:
            print("[ADVERTENCIA] wsgi.py puede no estar usando settings_production")
        else:
            errores.append("DJANGO_SETTINGS_MODULE no configurado")
            print("[ERROR] DJANGO_SETTINGS_MODULE NO configurado")
        
    except Exception as e:
        errores.append(f"Error al leer wsgi.py: {str(e)}")
        print(f"[ERROR] Error al leer wsgi.py: {str(e)}")
    
    return errores

def verificar_console_log():
    """Verifica que no haya console.log en templates críticos"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE CONSOLE.LOG EN TEMPLATES")
    print("=" * 60)
    
    errores = []
    advertencias = []
    
    templates_criticos = [
        'templates/gestion/clausulas/auditoria.html',
        'templates/gestion/contratos/form.html',
        'templates/gestion/polizas/form.html',
        'templates/gestion/otrosi/form.html',
    ]
    
    for template_path in templates_criticos:
        ruta = BASE_DIR / template_path
        if ruta.exists():
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                if 'console.log' in contenido:
                    advertencias.append(f"{template_path} contiene console.log")
                    print(f"[ADVERTENCIA] {template_path} contiene console.log")
                else:
                    print(f"[OK] {template_path} sin console.log")
            except Exception as e:
                print(f"[ADVERTENCIA] Error al leer {template_path}: {str(e)}")
        else:
            print(f"[ADVERTENCIA] {template_path} no encontrado")
    
    return errores, advertencias

def verificar_datos_sensibles():
    """Verifica que no haya datos sensibles hardcodeados"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE DATOS SENSIBLES HARDCODEADOS")
    print("=" * 60)
    
    errores = []
    advertencias = []
    
    patrones_sensibles = [
        (r'password\s*=\s*["\'][^"\']+["\']', 'Contraseña hardcodeada'),
        (r'api_key\s*=\s*["\'][^"\']+["\']', 'API key hardcodeada'),
    ]
    
    archivos_a_revisar = [
        'contratos/settings_production.py',
        'gestion/models.py',
    ]
    
    for patron, descripcion in patrones_sensibles:
        encontrado = False
        for archivo_patron in archivos_a_revisar:
            ruta = BASE_DIR / archivo_patron
            if ruta.exists() and ruta.is_file():
                try:
                    with open(ruta, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                    if re.search(patron, contenido, re.IGNORECASE):
                        encontrado = True
                        advertencias.append(f"{archivo_patron}: Posible {descripcion}")
                        print(f"[ADVERTENCIA] {archivo_patron}: Posible {descripcion}")
                except Exception:
                    pass
        
        if not encontrado:
            print(f"[OK] No se encontraron {descripcion.lower()}s en archivos críticos")
    
    return errores, advertencias

def verificar_migraciones():
    """Verifica que las migraciones estén presentes"""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE MIGRACIONES")
    print("=" * 60)
    
    errores = []
    
    migraciones_dir = BASE_DIR / 'gestion' / 'migrations'
    if migraciones_dir.exists():
        archivos_migracion = list(migraciones_dir.glob('*.py'))
        archivos_migracion = [f for f in archivos_migracion if f.name != '__init__.py']
        
        if archivos_migracion:
            print(f"[OK] {len(archivos_migracion)} archivos de migración encontrados")
        else:
            errores.append("No se encontraron archivos de migración")
            print("[ERROR] No se encontraron archivos de migración")
    else:
        errores.append("Directorio de migraciones no encontrado")
        print("[ERROR] Directorio de migraciones no encontrado")
    
    return errores

def main():
    """Ejecuta todas las verificaciones"""
    print("\n" + "=" * 60)
    print("TEST PRE-DEPLOYMENT PARA PRODUCCIÓN")
    print("=" * 60)
    print()
    
    todos_errores = []
    todas_advertencias = []
    
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
    
    errores, advertencias = verificar_console_log()
    todos_errores.extend(errores)
    todas_advertencias.extend(advertencias)
    
    errores, advertencias = verificar_datos_sensibles()
    todos_errores.extend(errores)
    todas_advertencias.extend(advertencias)
    
    errores = verificar_migraciones()
    todos_errores.extend(errores)
    
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
