"""
Script de ayuda para aplicar decoradores a las vistas
Este script muestra qué decoradores agregar a cada vista

NOTA: Este es un script de referencia/ayuda, no modifica archivos automáticamente.
Ejecutar con: python scripts/aplicar_decoradores.py para ver la guía completa.

Ver también: docs/guias/GUIA_PRODUCCION.md
"""

# INSTRUCCIONES:
# 1. Abre gestion/views.py
# 2. Al inicio del archivo, después de los imports existentes, agrega:

"""
from gestion.decorators import login_required_custom, admin_required
"""

# 3. Luego, agrega el decorador correspondiente ANTES de cada función:

DECORADORES_POR_VISTA = {
    # Vistas para usuarios autenticados normales
    '@login_required_custom': [
        'dashboard',
        'nuevo_contrato',
        'editar_contrato',
        'lista_contratos',
        'detalle_contrato',
        'nuevo_arrendatario',
        'nuevo_local',
        'gestionar_polizas',
        'nueva_poliza',
        'editar_poliza',
        'validar_poliza',
        'eliminar_poliza',
    ],
    
    # Vistas solo para administradores
    '@admin_required': [
        'configuracion_empresa',
        'eliminar_contrato',
    ]
}

# EJEMPLO DE CÓMO SE VE:

"""
# ANTES:
def dashboard(request):
    ...

# DESPUÉS:
@login_required_custom
def dashboard(request):
    ...
"""

"""
# ANTES:
def configuracion_empresa(request):
    ...

# DESPUÉS:
@admin_required
def configuracion_empresa(request):
    ...
"""

# 4. Guarda el archivo
# 5. Prueba ejecutando: python manage.py runserver
# 6. Intenta acceder sin login - debería redirigir a /login/

if __name__ == '__main__':
    print("=" * 80)
    print("GUÍA RÁPIDA: Aplicar Decoradores a Vistas")
    print("=" * 80)
    print()
    print("1. Abre: gestion/views.py")
    print()
    print("2. Agrega al inicio (después de imports):")
    print("   from gestion.decorators import login_required_custom, admin_required")
    print()
    print("3. Para cada vista, agrega el decorador ANTES de la función:")
    print()
    print("   Vistas normales (12):")
    for vista in DECORADORES_POR_VISTA['@login_required_custom']:
        print(f"   - {vista}")
    print()
    print("   Vistas de admin (2):")
    for vista in DECORADORES_POR_VISTA['@admin_required']:
        print(f"   - {vista}")
    print()
    print("=" * 80)
    print("EJEMPLO:")
    print("=" * 80)
    print("""
@login_required_custom
def dashboard(request):
    \"\"\"
    Dashboard principal con alertas avanzadas para la gestión de contratos
    \"\"\"
    fecha_actual = timezone.now().date()
    ...
""")
    print("=" * 80)
    print()
    print("Para más detalles, consulta: docs/guias/GUIA_PRODUCCION.md")

