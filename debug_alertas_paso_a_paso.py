"""
Debug paso a paso de la lógica de alertas
Ejecutar en: python3 manage.py shell
"""
from gestion.models import Contrato
from datetime import date
from gestion.utils_otrosi import get_otrosi_vigente, get_polizas_requeridas_contrato

contrato = Contrato.objects.filter(num_contrato='65412').first()
fecha_base = date.today()

print("=" * 80)
print("DEBUG PASO A PASO DE ALERTAS")
print("=" * 80)

# Paso 1: Obtener documento vigente
documento_vigente = get_otrosi_vigente(contrato, fecha_base)
print(f"\n1. Documento vigente: {documento_vigente}")
if documento_vigente:
    print(f"   ID: {documento_vigente.id}")
    if hasattr(documento_vigente, 'numero_otrosi'):
        identificador_documento_vigente = str(documento_vigente.numero_otrosi)
        print(f"   Identificador: {identificador_documento_vigente}")

# Paso 2: Obtener requisitos
polizas_requeridas = get_polizas_requeridas_contrato(contrato, fecha_base)
print(f"\n2. Requisitos obtenidos: {list(polizas_requeridas.keys())}")

# Paso 3: Separar requisitos del documento vigente vs contrato base
requisitos_del_documento_vigente = {}
requisitos_del_contrato_base = {}

for tipo_poliza, requisitos in polizas_requeridas.items():
    otrosi_modificador = requisitos.get('otrosi_modificador')
    print(f"\n   Tipo: {tipo_poliza}")
    print(f"   otrosi_modificador: {otrosi_modificador}")
    
    if documento_vigente and otrosi_modificador is not None:
        from gestion.models import OtroSi
        otrosi_modificador_str = str(otrosi_modificador).strip()
        
        otrosi_modificador_obj = OtroSi.objects.filter(
            contrato=contrato,
            numero_otrosi__iexact=otrosi_modificador_str
        ).first()
        
        print(f"   otrosi_modificador_obj encontrado: {otrosi_modificador_obj}")
        if otrosi_modificador_obj:
            print(f"   otrosi_modificador_obj.id: {otrosi_modificador_obj.id}")
            print(f"   documento_vigente.id: {documento_vigente.id}")
            print(f"   IDs coinciden: {otrosi_modificador_obj.id == documento_vigente.id}")
        
        if otrosi_modificador_obj and hasattr(documento_vigente, 'id'):
            if otrosi_modificador_obj.id == documento_vigente.id:
                requisitos_del_documento_vigente[tipo_poliza] = requisitos
                print(f"   ✅ Requisito asignado a documento vigente")
            else:
                requisitos_del_contrato_base[tipo_poliza] = requisitos
                print(f"   ❌ Requisito asignado a contrato base (IDs no coinciden)")
        else:
            identificador_str = str(identificador_documento_vigente).strip() if identificador_documento_vigente else None
            if identificador_str and otrosi_modificador_str.upper() == identificador_str.upper():
                requisitos_del_documento_vigente[tipo_poliza] = requisitos
                print(f"   ✅ Requisito asignado a documento vigente (comparación por string)")
            else:
                requisitos_del_contrato_base[tipo_poliza] = requisitos
                print(f"   ❌ Requisito asignado a contrato base (no coincide)")
    else:
        requisitos_del_contrato_base[tipo_poliza] = requisitos
        print(f"   ❌ Requisito asignado a contrato base (sin modificador)")

print(f"\n3. Requisitos del documento vigente: {list(requisitos_del_documento_vigente.keys())}")
print(f"   Requisitos del contrato base: {list(requisitos_del_contrato_base.keys())}")

# Paso 4: Verificar requisitos del documento vigente
if requisitos_del_documento_vigente:
    print(f"\n4. Verificando requisitos del documento vigente...")
    
    if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
        polizas_contrato = contrato.polizas.filter(otrosi_id=documento_vigente.id)
        print(f"   Pólizas asociadas al documento vigente (otrosi_id={documento_vigente.id}): {polizas_contrato.count()}")
        
        for tipo_poliza, requisitos in requisitos_del_documento_vigente.items():
            print(f"\n   Verificando tipo: {tipo_poliza}")
            fecha_fin_requerida = requisitos.get('fecha_fin_requerida')
            print(f"   fecha_fin_requerida: {fecha_fin_requerida}")
            
            polizas_tipo = polizas_contrato.filter(tipo__iexact=tipo_poliza)
            print(f"   Pólizas del tipo '{tipo_poliza}': {polizas_tipo.count()}")
            
            poliza_vigente = None
            for poliza_candidata in polizas_tipo:
                print(f"\n     Evaluando póliza: {poliza_candidata.numero_poliza}")
                fecha_vencimiento_efectiva = poliza_candidata.obtener_fecha_vencimiento_efectiva(fecha_base)
                print(f"     fecha_vencimiento_efectiva: {fecha_vencimiento_efectiva}")
                print(f"     fecha_base: {fecha_base}")
                print(f"     Vigente (efectiva >= base): {fecha_vencimiento_efectiva >= fecha_base}")
                
                if fecha_vencimiento_efectiva >= fecha_base:
                    if fecha_fin_requerida:
                        print(f"     Verificando fecha efectiva >= fecha_fin_requerida: {fecha_vencimiento_efectiva >= fecha_fin_requerida}")
                        if fecha_vencimiento_efectiva >= fecha_fin_requerida:
                            poliza_vigente = poliza_candidata
                            print(f"     ✅ Póliza válida encontrada (fecha efectiva)")
                            break
                        elif poliza_candidata.tiene_colchon and poliza_candidata.fecha_vencimiento:
                            print(f"     Verificando colchón:")
                            print(f"       fecha_vencimiento (con colchón): {poliza_candidata.fecha_vencimiento}")
                            print(f"       fecha_vencimiento >= fecha_fin_requerida: {poliza_candidata.fecha_vencimiento >= fecha_fin_requerida}")
                            if poliza_candidata.fecha_vencimiento >= fecha_fin_requerida:
                                poliza_vigente = poliza_candidata
                                print(f"       ✅ Póliza válida encontrada (colchón)")
                                break
                    else:
                        poliza_vigente = poliza_candidata
                        print(f"     ✅ Póliza válida encontrada (sin fecha fin requerida)")
                        break
            
            print(f"\n   Resultado: poliza_vigente = {poliza_vigente}")
            if not poliza_vigente:
                print(f"   ❌ NO se encontró póliza válida - SE GENERARÁ ALERTA")
            else:
                print(f"   ✅ Póliza válida encontrada - NO SE GENERARÁ ALERTA")
