import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

print("=" * 80)
print("CONSULTA: Buscando contrato 5412")
print("=" * 80)

# Buscar el contrato de diferentes formas
cursor.execute("SELECT id, num_contrato FROM gestion_contrato WHERE num_contrato LIKE '%5412%'")
contratos = cursor.fetchall()

if contratos:
    print(f"\nEncontrados {len(contratos)} contrato(s) con '5412':")
    for c in contratos:
        print(f"  - {c[1]} (ID: {c[0]})")
    
    # Usar el primero encontrado
    contrato_id = contratos[0][0]
    num_contrato = contratos[0][1]
else:
    # Buscar todos los contratos para ver el formato
    print("\nNo se encontro contrato con '5412'. Buscando algunos contratos para ver formato:")
    cursor.execute("SELECT id, num_contrato FROM gestion_contrato LIMIT 5")
    algunos = cursor.fetchall()
    for c in algunos:
        print(f"  - {c[1]} (ID: {c[0]})")
    conn.close()
    exit(0)

print(f"\nUsando contrato: {num_contrato} (ID: {contrato_id})")

# Obtener Otros Si del contrato
print("\n" + "-" * 80)
print("OTROS SI DEL CONTRATO:")
print("-" * 80)
cursor.execute("""
    SELECT id, numero_otrosi, estado, effective_from, effective_to 
    FROM gestion_otrosi 
    WHERE contrato_id = ? 
    ORDER BY numero_otrosi
""", (contrato_id,))
otrosi_list = cursor.fetchall()

if otrosi_list:
    for otrosi in otrosi_list:
        print(f"  - {otrosi[1]} (ID: {otrosi[0]}, Estado: {otrosi[2]})")
        print(f"    Vigencia: {otrosi[3]} hasta {otrosi[4] if otrosi[4] else 'Sin fin'}")
else:
    print("  No hay Otros Si registrados")

# Obtener todas las polizas de Cumplimiento
print("\n" + "-" * 80)
print("POLIZAS DE CUMPLIMIENTO:")
print("-" * 80)
cursor.execute("""
    SELECT id, numero_poliza, otrosi_id, renovacion_automatica_id, 
           documento_origen_tipo, fecha_vencimiento, tiene_colchon, meses_colchon
    FROM gestion_poliza 
    WHERE contrato_id = ? AND tipo = 'Cumplimiento'
    ORDER BY numero_poliza
""", (contrato_id,))
polizas = cursor.fetchall()

if not polizas:
    print("  No hay polizas de Cumplimiento registradas")
else:
    for poliza in polizas:
        print(f"\n  Poliza: {poliza[1]}")
        print(f"    ID: {poliza[0]}")
        print(f"    otrosi_id: {poliza[2]}")
        print(f"    renovacion_automatica_id: {poliza[3]}")
        print(f"    documento_origen_tipo: {poliza[4]}")
        print(f"    fecha_vencimiento: {poliza[5]}")
        print(f"    tiene_colchon: {poliza[6]}")
        print(f"    meses_colchon: {poliza[7]}")
        
        # Si tiene otrosi_id, obtener info del Otro Si
        if poliza[2]:
            cursor.execute("SELECT numero_otrosi FROM gestion_otrosi WHERE id = ?", (poliza[2],))
            otrosi_info = cursor.fetchone()
            if otrosi_info:
                print(f"    -> Asociada a Otro Si: {otrosi_info[0]} (ID: {poliza[2]})")
            else:
                print(f"    -> ERROR: Otro Si con ID {poliza[2]} no existe")
        elif poliza[3]:
            cursor.execute("SELECT numero_renovacion FROM gestion_renovacionautomatica WHERE id = ?", (poliza[3],))
            renov_info = cursor.fetchone()
            if renov_info:
                print(f"    -> Asociada a Renovacion: {renov_info[0]} (ID: {poliza[3]})")
        else:
            print(f"    -> Asociada a: Contrato Base")

# Verificar documento vigente
print("\n" + "-" * 80)
print("VERIFICACION DE BUSQUEDA:")
print("-" * 80)
from datetime import date
fecha_hoy = date.today().isoformat()

cursor.execute("""
    SELECT id, numero_otrosi 
    FROM gestion_otrosi 
    WHERE contrato_id = ? 
      AND estado = 'APROBADO'
      AND effective_from <= ?
      AND (effective_to IS NULL OR effective_to >= ?)
    ORDER BY effective_from DESC, version DESC
    LIMIT 1
""", (contrato_id, fecha_hoy, fecha_hoy))
documento_vigente = cursor.fetchone()

if documento_vigente:
    doc_vigente_id = documento_vigente[0]
    print(f"Documento vigente: {documento_vigente[1]} (ID: {doc_vigente_id})")
    print(f"\nBuscaría polizas con: otrosi_id={doc_vigente_id} AND tipo='Cumplimiento'")
    
    cursor.execute("""
        SELECT id, numero_poliza, fecha_vencimiento 
        FROM gestion_poliza 
        WHERE contrato_id = ? AND otrosi_id = ? AND tipo = 'Cumplimiento'
    """, (contrato_id, doc_vigente_id))
    polizas_encontradas = cursor.fetchall()
    
    print(f"Resultado: {len(polizas_encontradas)} poliza(s) encontrada(s)")
    if polizas_encontradas:
        for poliza in polizas_encontradas:
            print(f"  - {poliza[1]} (Vence: {poliza[2]})")
    else:
        print("  PROBLEMA: No se encontraron polizas aunque deberian existir")
        print("\n  Verificando todas las polizas de Cumplimiento del contrato:")
        cursor.execute("""
            SELECT id, numero_poliza, otrosi_id 
            FROM gestion_poliza 
            WHERE contrato_id = ? AND tipo = 'Cumplimiento'
        """, (contrato_id,))
        todas = cursor.fetchall()
        for p in todas:
            print(f"    - {p[1]}: otrosi_id={p[2]}")
else:
    print("No hay documento vigente (Otro Si o Renovacion)")

conn.close()
print("\n" + "=" * 80)
