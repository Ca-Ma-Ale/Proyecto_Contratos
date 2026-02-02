"""
Script para verificar la asociación de pólizas con Otros Sí en la base de datos
Ejecutar con: python manage.py shell < verificar_polizas_db.py
O copiar y pegar el contenido en: python manage.py shell
"""
from gestion.models import Contrato, Poliza, OtroSi
from datetime import date

# Buscar el contrato 5412
contrato = Contrato.objects.filter(num_contrato='5412').first()

if not contrato:
    print("❌ No se encontró el contrato 5412")
else:
    print("=" * 80)
    print(f"CONTRATO: {contrato.num_contrato}")
    print(f"Tercero: {contrato.obtener_nombre_tercero()}")
    print("=" * 80)
    
    # Obtener documento vigente
    from gestion.utils_otrosi import get_otrosi_vigente
    documento_vigente = get_otrosi_vigente(contrato, date.today())
    
    if documento_vigente:
        print(f"\n📄 DOCUMENTO VIGENTE:")
        if hasattr(documento_vigente, 'numero_otrosi'):
            print(f"   Tipo: Otro Sí")
            print(f"   Número: {documento_vigente.numero_otrosi}")
            print(f"   ID: {documento_vigente.id}")
        elif hasattr(documento_vigente, 'numero_renovacion'):
            print(f"   Tipo: Renovación Automática")
            print(f"   Número: {documento_vigente.numero_renovacion}")
            print(f"   ID: {documento_vigente.id}")
    else:
        print(f"\n📄 DOCUMENTO VIGENTE: Contrato Base")
    
    # Obtener todos los Otros Sí del contrato
    print(f"\n📋 OTROS SÍ DEL CONTRATO:")
    otrosi_list = OtroSi.objects.filter(contrato=contrato).order_by('numero_otrosi')
    for otrosi in otrosi_list:
        print(f"   - {otrosi.numero_otrosi} (ID: {otrosi.id}, Estado: {otrosi.estado})")
    
    # Obtener todas las pólizas del contrato
    print(f"\n📑 PÓLIZAS REGISTRADAS:")
    polizas = contrato.polizas.all().order_by('tipo', 'numero_poliza')
    
    for poliza in polizas:
        print(f"\n   Póliza: {poliza.numero_poliza}")
        print(f"   Tipo: {poliza.tipo}")
        print(f"   Fecha vencimiento: {poliza.fecha_vencimiento}")
        
        # Verificar asociación con Otro Sí
        if poliza.otrosi:
            print(f"   ✅ Asociada a Otro Sí:")
            print(f"      - Número: {poliza.otrosi.numero_otrosi}")
            print(f"      - ID: {poliza.otrosi.id}")
            print(f"      - otrosi_id en BD: {poliza.otrosi_id}")
            
            # Verificar si coincide con documento vigente
            if documento_vigente and hasattr(documento_vigente, 'id'):
                if poliza.otrosi.id == documento_vigente.id:
                    print(f"      ✅ COINCIDE con documento vigente")
                else:
                    print(f"      ❌ NO coincide con documento vigente (vigente ID: {documento_vigente.id})")
        elif poliza.renovacion_automatica:
            print(f"   ✅ Asociada a Renovación Automática:")
            print(f"      - Número: {poliza.renovacion_automatica.numero_renovacion}")
            print(f"      - ID: {poliza.renovacion_automatica.id}")
        else:
            print(f"   ✅ Asociada a: Contrato Base")
            print(f"      - otrosi_id en BD: {poliza.otrosi_id}")
            print(f"      - renovacion_automatica_id en BD: {poliza.renovacion_automatica_id}")
        
        print(f"   documento_origen_tipo: {poliza.documento_origen_tipo}")
    
    # Verificar específicamente pólizas de Cumplimiento
    print(f"\n🔍 PÓLIZAS DE CUMPLIMIENTO:")
    polizas_cumplimiento = contrato.polizas.filter(tipo='Cumplimiento')
    
    if polizas_cumplimiento.exists():
        for poliza in polizas_cumplimiento:
            print(f"\n   {poliza.numero_poliza}:")
            print(f"      otrosi_id: {poliza.otrosi_id}")
            print(f"      renovacion_automatica_id: {poliza.renovacion_automatica_id}")
            print(f"      documento_origen_tipo: {poliza.documento_origen_tipo}")
            
            if poliza.otrosi:
                print(f"      Otro Sí asociado: {poliza.otrosi.numero_otrosi} (ID: {poliza.otrosi.id})")
                
                # Verificar si es el documento vigente
                if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
                    if poliza.otrosi.id == documento_vigente.id:
                        print(f"      ✅ ESTÁ ASOCIADA AL DOCUMENTO VIGENTE")
                    else:
                        print(f"      ❌ NO está asociada al documento vigente")
                        print(f"         Documento vigente: {documento_vigente.numero_otrosi} (ID: {documento_vigente.id})")
    else:
        print("   ❌ No hay pólizas de Cumplimiento registradas")
    
    # Verificar qué buscaría el código de alertas
    print(f"\n🔎 VERIFICACIÓN DE BÚSQUEDA (como lo hace el código de alertas):")
    if documento_vigente and hasattr(documento_vigente, 'numero_otrosi'):
        print(f"   Documento vigente ID: {documento_vigente.id}")
        print(f"   Buscaría pólizas con: otrosi_id={documento_vigente.id} AND tipo='Cumplimiento'")
        
        polizas_encontradas = contrato.polizas.filter(
            otrosi_id=documento_vigente.id,
            tipo='Cumplimiento'
        )
        
        print(f"   Resultado: {polizas_encontradas.count()} póliza(s) encontrada(s)")
        for poliza in polizas_encontradas:
            print(f"      - {poliza.numero_poliza} (Vence: {poliza.fecha_vencimiento})")
            
            # Verificar vigencia
            try:
                fecha_efectiva = poliza.obtener_fecha_vencimiento_efectiva(date.today())
                print(f"        Fecha efectiva: {fecha_efectiva}")
                print(f"        Vigente: {'✅ SÍ' if fecha_efectiva >= date.today() else '❌ NO'}")
            except Exception as e:
                print(f"        Error al obtener fecha efectiva: {e}")

print("\n" + "=" * 80)
