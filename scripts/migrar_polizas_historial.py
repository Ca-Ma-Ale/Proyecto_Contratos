"""
Script para migrar pólizas existentes al nuevo sistema de historial.
Asigna las pólizas al documento origen apropiado basándose en su fecha de creación.
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from gestion.models import Poliza, OtroSi, RenovacionAutomatica
from datetime import date


def migrar_polizas():
    """
    Migra pólizas existentes asignándolas al documento origen apropiado.
    """
    polizas_sin_documento = Poliza.objects.filter(
        otrosi__isnull=True,
        renovacion_automatica__isnull=True
    )
    
    total = polizas_sin_documento.count()
    print(f"Migrando {total} pólizas...")
    
    migradas = 0
    sin_asignar = 0
    
    for poliza in polizas_sin_documento:
        contrato = poliza.contrato
        
        # Intentar encontrar el OtroSi o RenovacionAutomatica más reciente antes de la fecha de creación de la póliza
        fecha_referencia = poliza.fecha_creacion.date() if poliza.fecha_creacion else date.today()
        
        # Buscar OtroSi aprobado más reciente antes de la fecha de creación
        otrosi_vigente = OtroSi.objects.filter(
            contrato=contrato,
            estado='APROBADO',
            effective_from__lte=fecha_referencia
        ).order_by('-effective_from', '-version').first()
        
        # Buscar RenovacionAutomatica aprobada más reciente antes de la fecha de creación
        renovacion_vigente = RenovacionAutomatica.objects.filter(
            contrato=contrato,
            estado='APROBADO',
            effective_from__lte=fecha_referencia
        ).order_by('-effective_from', '-version').first()
        
        # Asignar al documento más reciente
        if otrosi_vigente and renovacion_vigente:
            # Si ambos existen, usar el más reciente
            if otrosi_vigente.effective_from >= renovacion_vigente.effective_from:
                poliza.otrosi = otrosi_vigente
                poliza.documento_origen_tipo = 'OTROSI'
            else:
                poliza.renovacion_automatica = renovacion_vigente
                poliza.documento_origen_tipo = 'RENOVACION'
        elif otrosi_vigente:
            poliza.otrosi = otrosi_vigente
            poliza.documento_origen_tipo = 'OTROSI'
        elif renovacion_vigente:
            poliza.renovacion_automatica = renovacion_vigente
            poliza.documento_origen_tipo = 'RENOVACION'
        else:
            # Sin documento específico, asignar al contrato base
            poliza.documento_origen_tipo = 'CONTRATO'
            sin_asignar += 1
        
        poliza.save()
        migradas += 1
        
        if migradas % 100 == 0:
            print(f"Procesadas {migradas}/{total} pólizas...")
    
    print(f"\nMigración completada:")
    print(f"  - Pólizas migradas: {migradas}")
    print(f"  - Asignadas a OtroSi: {Poliza.objects.filter(documento_origen_tipo='OTROSI').count()}")
    print(f"  - Asignadas a Renovación: {Poliza.objects.filter(documento_origen_tipo='RENOVACION').count()}")
    print(f"  - Asignadas a Contrato Base: {Poliza.objects.filter(documento_origen_tipo='CONTRATO').count()}")
    print(f"  - Sin asignar específicamente: {sin_asignar}")


if __name__ == '__main__':
    print("Iniciando migración de pólizas al nuevo sistema de historial...")
    migrar_polizas()
    print("Migración finalizada.")
