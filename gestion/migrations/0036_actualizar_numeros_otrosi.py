# Generated migration to update existing OtroSi numbers to new format

from django.db import migrations


def actualizar_numeros_otrosi(apps, schema_editor):
    """
    Actualiza los números de Otro Sí existentes al nuevo formato OS-1, OS-2, etc.
    agrupados por contrato y ordenados por fecha de creación.
    """
    OtroSi = apps.get_model('gestion', 'OtroSi')
    
    # Obtener todos los contratos que tienen Otro Sí
    contratos_con_otrosi = OtroSi.objects.values_list('contrato_id', flat=True).distinct()
    
    for contrato_id in contratos_con_otrosi:
        # Obtener todos los Otro Sí de este contrato ordenados por fecha de creación
        otrosi_del_contrato = OtroSi.objects.filter(
            contrato_id=contrato_id
        ).order_by('fecha_creacion', 'version')
        
        # Asignar números secuenciales
        for index, otrosi in enumerate(otrosi_del_contrato, start=1):
            otrosi.numero_otrosi = f"OS-{index}"
            otrosi.save(update_fields=['numero_otrosi'])


def revertir_numeros_otrosi(apps, schema_editor):
    """
    Función de reversión (opcional) - no hace nada ya que no podemos saber
    el formato original de los números.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0035_agregar_fechas_polizas_otrosi'),
    ]

    operations = [
        migrations.RunPython(actualizar_numeros_otrosi, revertir_numeros_otrosi),
    ]

