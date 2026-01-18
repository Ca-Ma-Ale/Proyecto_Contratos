"""
Script para crear usuario admin y un usuario estándar de pruebas
Ejecutar con: python crear_usuario_desarrollador.py
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from django.contrib.auth.models import User

# Datos del usuario admin (renombrado desde "desarrollador")
USERNAME = 'admin'
EMAIL = 'admin@avenidachile.com'
PASSWORD = 'Avenida2024!'  # Contraseña temporal - CAMBIAR después
FIRST_NAME = 'Usuario'
LAST_NAME = 'Admin'

try:
    # Intentar obtener el usuario si ya existe
    user = User.objects.get(username=USERNAME)
    print(f"⚠️  El usuario '{USERNAME}' ya existe.")
    print(f"   Email: {user.email}")
    print(f"   Es superusuario: {user.is_superuser}")
    print(f"   Es staff: {user.is_staff}")
    
    # Actualizar contraseña por si acaso
    user.set_password(PASSWORD)
    user.save()
    print(f"✅ Contraseña actualizada para '{USERNAME}'")
    
except User.DoesNotExist:
    # Crear nuevo usuario admin (superusuario)
    user = User.objects.create_superuser(
        username=USERNAME,
        email=EMAIL,
        password=PASSWORD,
        first_name=FIRST_NAME,
        last_name=LAST_NAME
    )
    print(f"✅ Usuario '{USERNAME}' creado exitosamente!")
    print(f"   Email: {EMAIL}")
    print(f"   Es superusuario: SÍ")
    print(f"   Es staff: SÍ")

print("\n" + "="*60)
print("CREDENCIALES DE ACCESO:")
print("="*60)
print(f"URL: http://localhost:8000/login/")
print(f"Usuario: {USERNAME}")
print(f"Contraseña: {PASSWORD}")
print("="*60)
print("\n⚠️  IMPORTANTE: Cambia esta contraseña después del primer login")
print("   Ve a: http://localhost:8000/admin/password_change/")
print("="*60)

# ==============================================
# Creación de usuario estándar (sin permisos admin)
# ==============================================

NORMAL_USERNAME = 'usuario_pruebas'
NORMAL_EMAIL = 'usuario.pruebas@avenidachile.com'
NORMAL_PASSWORD = 'Avenida2024!'  # Contraseña temporal - CAMBIAR después
NORMAL_FIRST_NAME = 'Usuario'
NORMAL_LAST_NAME = 'Pruebas'

try:
    normal_user = User.objects.get(username=NORMAL_USERNAME)
    print(f"\n⚠️  El usuario estándar '{NORMAL_USERNAME}' ya existe.")
    # Asegurar que no tenga permisos de admin
    normal_user.is_staff = False
    normal_user.is_superuser = False
    normal_user.set_password(NORMAL_PASSWORD)
    normal_user.save()
    print(f"✅ Usuario estándar '{NORMAL_USERNAME}' actualizado (sin permisos admin)")
except User.DoesNotExist:
    normal_user = User.objects.create_user(
        username=NORMAL_USERNAME,
        email=NORMAL_EMAIL,
        password=NORMAL_PASSWORD,
        first_name=NORMAL_FIRST_NAME,
        last_name=NORMAL_LAST_NAME
    )
    # Garantizar permisos básicos
    normal_user.is_active = True
    normal_user.is_staff = False
    normal_user.is_superuser = False
    normal_user.save()
    print(f"\n✅ Usuario estándar '{NORMAL_USERNAME}' creado (sin permisos admin)")

print("\n" + "-"*60)
print("CREDENCIALES USUARIO ESTÁNDAR:")
print("-"*60)
print("URL: http://localhost:8000/login/")
print(f"Usuario: {NORMAL_USERNAME}")
print(f"Contraseña: {NORMAL_PASSWORD}")
print("-"*60)

