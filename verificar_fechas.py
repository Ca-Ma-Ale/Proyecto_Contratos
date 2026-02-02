"""
Script para verificar fechas de pólizas
Ejecutar en: python3 manage.py shell
"""
from gestion.models import Contrato, Poliza
from datetime import date
from gestion.utils_otrosi import get_otrosi_vigente, get_polizas_requeridas_contrato

contrato = Contrato.objects.filter(num_contrato='65412').first()
fecha_base = date.today()

print("=" * 80)
print("VERIFICACION DE FECHAS Y VIGENCIA")
print("=" * 80)

documento_vigente = get_otrosi_vigente(contrato, fecha_base)
print(f"\nFecha base (hoy): {fecha_base}")
print(f"Documento vigente: {documento_vigente.numero_otrosi if documento_vigente else 'Contrato Base'}")

# Obtener requisitos
polizas_requeridas = get_polizas_requeridas_contrato(contrato, fecha_base)
if 'Cumplimiento' in polizas_requeridas:
    requisitos = polizas_requeridas['Cumplimiento']
    print(f"\nREQUISITOS DE CUMPLIMIENTO:")
    print(f"  otrosi_modificador: {requisitos.get('otrosi_modificador')}")
    print(f"  fecha_fin_requerida: {requisitos.get('fecha_fin_requerida')}")
    print(f"  valor_requerido: {requisitos.get('valor_requerido')}")

# Verificar póliza POL-25-0113
poliza = contrato.polizas.filter(numero_poliza='POL-25-0113').first()
if poliza:
    print(f"\nPOLIZA POL-25-0113:")
    print(f"  fecha_vencimiento: {poliza.fecha_vencimiento}")
    print(f"  tiene_colchon: {poliza.tiene_colchon}")
    print(f"  meses_colchon: {poliza.meses_colchon}")
    print(f"  fecha_vencimiento_real: {poliza.fecha_vencimiento_real}")
    
    try:
        fecha_efectiva = poliza.obtener_fecha_vencimiento_efectiva(fecha_base)
        print(f"  fecha_vencimiento_efectiva: {fecha_efectiva}")
        print(f"  Vigente: {'SI' if fecha_efectiva >= fecha_base else 'NO'}")
        
        if 'Cumplimiento' in polizas_requeridas:
            fecha_fin_requerida = polizas_requeridas['Cumplimiento'].get('fecha_fin_requerida')
            if fecha_fin_requerida:
                print(f"\n  COMPARACION CON FECHA FIN REQUERIDA:")
                print(f"    fecha_efectiva: {fecha_efectiva}")
                print(f"    fecha_fin_requerida: {fecha_fin_requerida}")
                print(f"    Cubre requisito: {'SI' if fecha_efectiva >= fecha_fin_requerida else 'NO'}")
    except Exception as e:
        print(f"  ERROR al obtener fecha efectiva: {e}")
        import traceback
        traceback.print_exc()

# Simular la búsqueda que hace el código de alertas
print(f"\n" + "=" * 80)
print("SIMULACION DE BUSQUEDA DEL CODIGO DE ALERTAS:")
print("=" * 80)

if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
    polizas_encontradas = contrato.polizas.filter(
        otrosi_id=documento_vigente.id,
        tipo='Cumplimiento'
    )
    
    print(f"Busca: otrosi_id={documento_vigente.id} AND tipo='Cumplimiento'")
    print(f"Encontradas: {polizas_encontradas.count()}")
    
    poliza_valida = None
    for poliza_candidata in polizas_encontradas:
        print(f"\n  Evaluando: {poliza_candidata.numero_poliza}")
        try:
            fecha_efectiva = poliza_candidata.obtener_fecha_vencimiento_efectiva(fecha_base)
            print(f"    fecha_efectiva: {fecha_efectiva}")
            print(f"    >= fecha_base ({fecha_base}): {fecha_efectiva >= fecha_base}")
            
            if fecha_efectiva >= fecha_base:
                if 'Cumplimiento' in polizas_requeridas:
                    fecha_fin_requerida = polizas_requeridas['Cumplimiento'].get('fecha_fin_requerida')
                    if fecha_fin_requerida:
                        print(f"    fecha_fin_requerida: {fecha_fin_requerida}")
                        print(f"    >= fecha_fin_requerida: {fecha_efectiva >= fecha_fin_requerida}")
                        if fecha_efectiva >= fecha_fin_requerida:
                            poliza_valida = poliza_candidata
                            print(f"    -> POLIZA VALIDA ENCONTRADA")
                            break
                    else:
                        poliza_valida = poliza_candidata
                        print(f"    -> POLIZA VALIDA (sin fecha fin requerida)")
                        break
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    if poliza_valida:
        print(f"\nRESULTADO: Se encontro poliza valida: {poliza_valida.numero_poliza}")
        print("NO deberia generar alerta")
    else:
        print(f"\nRESULTADO: NO se encontro poliza valida")
        print("SI deberia generar alerta")
