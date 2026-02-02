"""
Script rápido para ejecutar en PythonAnywhere
Copia y pega este código en: python manage.py shell
"""
from gestion.models import Contrato, Poliza, OtroSi
from datetime import date
from gestion.utils_otrosi import get_otrosi_vigente

contrato = Contrato.objects.filter(num_contrato__icontains='5412').first()

if not contrato:
    print("No se encontro el contrato")
else:
    print("=" * 80)
    print(f"CONTRATO: {contrato.num_contrato}")
    print(f"ID: {contrato.id}")
    
    documento_vigente = get_otrosi_vigente(contrato, date.today())
    if documento_vigente:
        print(f"\nDOCUMENTO VIGENTE: {documento_vigente.numero_otrosi} (ID: {documento_vigente.id})")
    else:
        print("\nDOCUMENTO VIGENTE: Contrato Base")
    
    print("\nPOLIZAS DE CUMPLIMIENTO:")
    polizas = contrato.polizas.filter(tipo='Cumplimiento')
    for p in polizas:
        print(f"  {p.numero_poliza}: otrosi_id={p.otrosi_id}, doc_tipo={p.documento_origen_tipo}")
        if p.otrosi:
            print(f"    -> Otro Si: {p.otrosi.numero_otrosi} (ID: {p.otrosi.id})")
    
    if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
        print(f"\nBUSQUEDA: otrosi_id={documento_vigente.id} AND tipo='Cumplimiento'")
        encontradas = contrato.polizas.filter(otrosi_id=documento_vigente.id, tipo='Cumplimiento')
        print(f"RESULTADO: {encontradas.count()} poliza(s)")
