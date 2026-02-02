"""
Test directo de la lógica de alertas
Ejecutar en: python3 manage.py shell
"""
from gestion.models import Contrato
from datetime import date
from gestion.services.alertas import obtener_alertas_polizas_requeridas_no_aportadas

contrato = Contrato.objects.filter(num_contrato='65412').first()
fecha_base = date.today()

print("=" * 80)
print("TEST DIRECTO DE ALERTAS")
print("=" * 80)

alertas = obtener_alertas_polizas_requeridas_no_aportadas(fecha_base)
alertas_contrato = [a for a in alertas if a.contrato.id == contrato.id]

print(f"\nAlertas generadas para contrato {contrato.num_contrato}: {len(alertas_contrato)}")

if alertas_contrato:
    print("\nALERTAS ENCONTRADAS:")
    for alerta in alertas_contrato:
        print(f"  - {alerta.tipo_poliza}")
        print(f"    Nombre: {alerta.nombre_poliza}")
        print(f"    Otro Si modificador: {alerta.otrosi_modificador}")
        print(f"    Tiene poliza: {alerta.tiene_poliza}")
        print(f"    Fecha fin requerida: {alerta.fecha_fin_requerida}")
else:
    print("\n✅ NO HAY ALERTAS - El sistema reconoce correctamente las polizas")
