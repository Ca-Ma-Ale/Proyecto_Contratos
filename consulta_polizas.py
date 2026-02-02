import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from gestion.models import Contrato, Poliza, OtroSi
from datetime import date
from gestion.utils_otrosi import get_otrosi_vigente

contrato = Contrato.objects.filter(num_contrato='5412').first()

if not contrato:
    print("No se encontro el contrato 5412")
    sys.exit(1)

print("=" * 80)
print(f"CONTRATO: {contrato.num_contrato}")
print(f"Tercero: {contrato.obtener_nombre_tercero()}")
print("=" * 80)

documento_vigente = get_otrosi_vigente(contrato, date.today())

if documento_vigente:
    print(f"\nDOCUMENTO VIGENTE:")
    if hasattr(documento_vigente, 'numero_otrosi'):
        print(f"   Tipo: Otro Si")
        print(f"   Numero: {documento_vigente.numero_otrosi}")
        print(f"   ID: {documento_vigente.id}")
    elif hasattr(documento_vigente, 'numero_renovacion'):
        print(f"   Tipo: Renovacion Automatica")
        print(f"   Numero: {documento_vigente.numero_renovacion}")
        print(f"   ID: {documento_vigente.id}")
else:
    print(f"\nDOCUMENTO VIGENTE: Contrato Base")

print(f"\nOTROS SI DEL CONTRATO:")
otrosi_list = OtroSi.objects.filter(contrato=contrato).order_by('numero_otrosi')
for otrosi in otrosi_list:
    print(f"   - {otrosi.numero_otrosi} (ID: {otrosi.id}, Estado: {otrosi.estado})")

print(f"\nPOLIZAS DE CUMPLIMIENTO:")
polizas_cumplimiento = contrato.polizas.filter(tipo='Cumplimiento')

if polizas_cumplimiento.exists():
    for poliza in polizas_cumplimiento:
        print(f"\n   Poliza: {poliza.numero_poliza}")
        print(f"   otrosi_id en BD: {poliza.otrosi_id}")
        print(f"   renovacion_automatica_id en BD: {poliza.renovacion_automatica_id}")
        print(f"   documento_origen_tipo: {poliza.documento_origen_tipo}")
        print(f"   Fecha vencimiento: {poliza.fecha_vencimiento}")
        
        if poliza.otrosi:
            print(f"   Otro Si asociado: {poliza.otrosi.numero_otrosi} (ID: {poliza.otrosi.id})")
            
            if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
                if poliza.otrosi.id == documento_vigente.id:
                    print(f"   ESTA ASOCIADA AL DOCUMENTO VIGENTE")
                else:
                    print(f"   NO esta asociada al documento vigente")
                    print(f"      Documento vigente: {documento_vigente.numero_otrosi} (ID: {documento_vigente.id})")
        elif poliza.renovacion_automatica:
            print(f"   Renovacion Automatica asociada: {poliza.renovacion_automatica.numero_renovacion} (ID: {poliza.renovacion_automatica.id})")
        else:
            print(f"   Asociada a: Contrato Base")
else:
    print("   No hay polizas de Cumplimiento registradas")

print(f"\nVERIFICACION DE BUSQUEDA:")
if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
    print(f"   Documento vigente ID: {documento_vigente.id}")
    print(f"   Buscaria polizas con: otrosi_id={documento_vigente.id} AND tipo='Cumplimiento'")
    
    polizas_encontradas = contrato.polizas.filter(
        otrosi_id=documento_vigente.id,
        tipo='Cumplimiento'
    )
    
    print(f"   Resultado: {polizas_encontradas.count()} poliza(s) encontrada(s)")
    for poliza in polizas_encontradas:
        print(f"      - {poliza.numero_poliza} (Vence: {poliza.fecha_vencimiento})")
        try:
            fecha_efectiva = poliza.obtener_fecha_vencimiento_efectiva(date.today())
            print(f"        Fecha efectiva: {fecha_efectiva}")
            print(f"        Vigente: {'SI' if fecha_efectiva >= date.today() else 'NO'}")
        except Exception as e:
            print(f"        Error: {e}")

print("\n" + "=" * 80)
