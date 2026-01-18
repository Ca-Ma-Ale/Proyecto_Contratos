# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0033_agregar_campos_detalles_poliza_aportada'),
    ]

    operations = [
        # Póliza RCE
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_exige_poliza_rce',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Exige Póliza RCE?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_asegurado_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Valor Asegurado RCE'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_propietario_locatario_ocupante_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo PLO (Propietario, Locatario y Ocupante) Asegurado'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_patronal_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Patronal Asegurado'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_gastos_medicos_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Gastos Médicos de Terceros Asegurados'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_vehiculos_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Vehículos Propios y No Propios Asegurados'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_contratistas_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Contratistas y Subcontratistas Asegurados'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_perjuicios_extrapatrimoniales_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Perjuicios Extrapatrimoniales Asegurados'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_dano_moral_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Daño Moral Asegurado'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_lucro_cesante_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Lucro Cesante Asegurado'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_meses_vigencia_rce',
            field=models.IntegerField(blank=True, null=True, verbose_name='Nuevos Meses de Vigencia RCE'),
        ),
        
        # Póliza Cumplimiento
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_exige_poliza_cumplimiento',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Exige Póliza de Cumplimiento?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_asegurado_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Valor Asegurado Cumplimiento'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_remuneraciones_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Remuneraciones Mensuales Aseguradas (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_servicios_publicos_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Servicios Públicos Asegurados (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_iva_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo IVA Asegurado (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_otros_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Cuota de Administración Asegurada (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_meses_vigencia_cumplimiento',
            field=models.IntegerField(blank=True, null=True, verbose_name='Nuevos Meses de Vigencia Cumplimiento'),
        ),
        
        # Póliza de Arrendamiento
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_exige_poliza_arrendamiento',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Exige Póliza de Arrendamiento?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_asegurado_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Valor Asegurado Póliza de Arrendamiento'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_remuneraciones_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Remuneraciones Mensuales Aseguradas (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_servicios_publicos_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Servicios Públicos Asegurados (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_iva_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo IVA Asegurado (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_otros_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Cuota de Administración Asegurada (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_meses_vigencia_arrendamiento',
            field=models.IntegerField(blank=True, null=True, verbose_name='Nuevos Meses de Vigencia Póliza de Arrendamiento'),
        ),
        
        # Póliza Todo Riesgo
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_exige_poliza_todo_riesgo',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Exige Póliza Todo Riesgo para Equipos?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_asegurado_todo_riesgo',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Valor Asegurado Todo Riesgo'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_meses_vigencia_todo_riesgo',
            field=models.IntegerField(blank=True, null=True, verbose_name='Nuevos Meses de Vigencia Todo Riesgo'),
        ),
        
        # Otras Pólizas
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_exige_poliza_otra_1',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Exige Otras Pólizas?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_nombre_poliza_otra_1',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Nuevo Nombre Otras Pólizas'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_valor_asegurado_otra_1',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Nuevo Valor Asegurado Otras Pólizas'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_meses_vigencia_otra_1',
            field=models.IntegerField(blank=True, null=True, verbose_name='Nuevos Meses de Vigencia Otras Pólizas'),
        ),
    ]

