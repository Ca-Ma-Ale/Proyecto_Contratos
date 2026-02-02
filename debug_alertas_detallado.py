"""
Debug detallado de la lógica de alertas
Ejecutar en: python3 manage.py shell
"""
from gestion.models import Contrato, Poliza
from datetime import date

contrato = Contrato.objects.filter(num_contrato='65412').first()
fecha_base = date.today()

print("=" * 80)
print("DEBUG DETALLADO DE ALERTAS")
print("=" * 80)

# Obtener documento vigente (igual que en alertas.py)
from gestion.utils_otrosi import get_otrosi_vigente
documento_vigente = get_otrosi_vigente(contrato, fecha_base)

print(f"\nContrato: {contrato.num_contrato} (ID: {contrato.id})")
print(f"Documento vigente: {documento_vigente}")
if documento_vigente:
    print(f"  Tipo: {'OtroSi' if hasattr(documento_vigente, 'numero_otrosi') else 'Renovacion'}")
    print(f"  ID: {documento_vigente.id}")
    if hasattr(documento_vigente, 'numero_otrosi'):
        print(f"  Numero: {documento_vigente.numero_otrosi}")

# Obtener pólizas asociadas al documento vigente
if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
    polizas_doc = contrato.polizas.filter(otrosi_id=documento_vigente.id)
    print(f"\nPólizas asociadas al documento vigente (otrosi_id={documento_vigente.id}): {polizas_doc.count()}")
    
    for poliza in polizas_doc:
        print(f"\n  Póliza: {poliza.numero_poliza}")
        print(f"    Tipo: {poliza.tipo}")
        print(f"    otrosi_id: {poliza.otrosi_id}")
        print(f"    fecha_vencimiento: {poliza.fecha_vencimiento}")
        print(f"    tiene_colchon: {poliza.tiene_colchon}")
        if poliza.tiene_colchon:
            print(f"    meses_colchon: {poliza.meses_colchon}")
            print(f"    fecha_vencimiento_real: {poliza.fecha_vencimiento_real}")
        
        fecha_efectiva = poliza.obtener_fecha_vencimiento_efectiva(fecha_base)
        print(f"    fecha_vencimiento_efectiva: {fecha_efectiva}")
        print(f"    Vigente (efectiva >= hoy): {fecha_efectiva >= fecha_base}")

# Obtener requisitos del documento vigente
from gestion.utils_otrosi import get_polizas_requeridas_contrato
polizas_requeridas = get_polizas_requeridas_contrato(contrato, fecha_base)

print(f"\n\nRequisitos de pólizas:")
for tipo, req in polizas_requeridas.items():
    print(f"\n  {tipo}:")
    print(f"    valor_requerido: {req.get('valor_requerido')}")
    print(f"    fecha_fin_requerida: {req.get('fecha_fin_requerida')}")
    print(f"    otrosi_modificador: {req.get('otrosi_modificador')}")
    print(f"    meses_vigencia: {req.get('meses_vigencia')}")

# Simular la lógica de validación
print(f"\n\n{'='*80}")
print("SIMULACION DE VALIDACION")
print("="*80)

if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
    requisitos_cumplimiento = polizas_requeridas.get('cumplimiento', {})
    fecha_fin_requerida = requisitos_cumplimiento.get('fecha_fin')
    otrosi_modificador = requisitos_cumplimiento.get('otrosi_modificador')
    identificador_doc = requisitos_cumplimiento.get('identificador_documento_vigente')
    
    print(f"\nRequisito Cumplimiento:")
    print(f"  fecha_fin_requerida: {fecha_fin_requerida}")
    print(f"  otrosi_modificador: {otrosi_modificador}")
    print(f"  identificador_documento_vigente: {identificador_doc}")
    
    # Verificar si este requisito pertenece al documento vigente
    if otrosi_modificador is not None:
        otrosi_mod_str = str(otrosi_modificador).strip().upper()
        doc_id_str = str(identificador_doc).strip().upper() if identificador_doc else None
        
        print(f"\nComparacion:")
        print(f"  otrosi_modificador (normalizado): '{otrosi_mod_str}'")
        print(f"  identificador_doc (normalizado): '{doc_id_str}'")
        
        if doc_id_str and otrosi_mod_str == doc_id_str:
            print(f"  ✅ El requisito pertenece al documento vigente")
            
            # Buscar pólizas
            polizas_tipo = polizas_doc.filter(tipo='cumplimiento')
            print(f"\n  Pólizas de tipo 'cumplimiento': {polizas_tipo.count()}")
            
            poliza_encontrada = None
            for poliza_candidata in polizas_tipo:
                fecha_efectiva = poliza_candidata.obtener_fecha_vencimiento_efectiva(fecha_base)
                print(f"\n    Póliza {poliza_candidata.numero_poliza}:")
                print(f"      fecha_efectiva: {fecha_efectiva}")
                print(f"      fecha_fin_requerida: {fecha_fin_requerida}")
                print(f"      fecha_efectiva >= fecha_base: {fecha_efectiva >= fecha_base}")
                
                if fecha_efectiva >= fecha_base:
                    print(f"      fecha_efectiva >= fecha_fin_requerida: {fecha_efectiva >= fecha_fin_requerida}")
                    
                    if fecha_efectiva >= fecha_fin_requerida:
                        print(f"      ✅ CUMPLE con fecha efectiva")
                        poliza_encontrada = poliza_candidata
                        break
                    elif poliza_candidata.tiene_colchon and poliza_candidata.fecha_vencimiento:
                        print(f"      Verificando colchón:")
                        print(f"        fecha_vencimiento (con colchón): {poliza_candidata.fecha_vencimiento}")
                        print(f"        fecha_vencimiento >= fecha_fin_requerida: {poliza_candidata.fecha_vencimiento >= fecha_fin_requerida}")
                        if poliza_candidata.fecha_vencimiento >= fecha_fin_requerida:
                            print(f"        ✅ CUMPLE con colchón")
                            poliza_encontrada = poliza_candidata
                            break
                        else:
                            print(f"        ❌ NO cumple con colchón")
                    else:
                        print(f"      ❌ NO cumple (sin colchón o sin fecha_vencimiento)")
                else:
                    print(f"      ❌ Póliza vencida")
            
            if poliza_encontrada:
                print(f"\n  ✅ RESULTADO: Póliza válida encontrada: {poliza_encontrada.numero_poliza}")
            else:
                print(f"\n  ❌ RESULTADO: NO se encontró póliza válida")
        else:
            print(f"  ❌ El requisito NO pertenece al documento vigente")
    else:
        print(f"  otrosi_modificador es None - requisito del contrato base")
