from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0025_seguimientos'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='exige_poliza_arrendamiento',
            field=models.BooleanField(default=False, verbose_name='¿Exige Póliza de Arrendamiento?'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='fecha_fin_vigencia_arrendamiento',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha Fin Vigencia Póliza de Arrendamiento'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='fecha_inicio_vigencia_arrendamiento',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha Inicio Vigencia Póliza de Arrendamiento'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='meses_vigencia_arrendamiento',
            field=models.IntegerField(blank=True, null=True, verbose_name='Meses de Vigencia Póliza de Arrendamiento'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_asegurado_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Valor Asegurado Póliza de Arrendamiento'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_iva_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='IVA Asegurado (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_iva_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='IVA Asegurado (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_otros_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Otros Conceptos Asegurados (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_otros_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Otros Conceptos Asegurados (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_remuneraciones_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Remuneraciones Mensuales Aseguradas (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_remuneraciones_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Remuneraciones Mensuales Aseguradas (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_servicios_publicos_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Servicios Públicos Asegurados (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_servicios_publicos_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Servicios Públicos Asegurados (Cumplimiento)'),
        ),
        migrations.AlterField(
            model_name='poliza',
            name='tipo',
            field=models.CharField(choices=[('Cumplimiento', 'Cumplimiento'), ('Poliza de Arrendamiento', 'Póliza de Arrendamiento'), ('RCE - Responsabilidad Civil', 'RCE - Responsabilidad Civil'), ('Arrendamiento', 'Arrendamiento'), ('Otra', 'Otra')], max_length=30, verbose_name='Tipo de Póliza'),
        ),
        migrations.AlterField(
            model_name='polizaaportada',
            name='tipo',
            field=models.CharField(choices=[('Cumplimiento', 'Cumplimiento'), ('Poliza de Arrendamiento', 'Póliza de Arrendamiento'), ('RCE - Responsabilidad Civil', 'RCE - Responsabilidad Civil'), ('Arrendamiento', 'Arrendamiento'), ('Otra', 'Otra')], max_length=30, verbose_name='Tipo de Póliza'),
        ),
        migrations.AlterField(
            model_name='requerimientopoliza',
            name='tipo',
            field=models.CharField(choices=[('Cumplimiento', 'Cumplimiento'), ('Poliza de Arrendamiento', 'Póliza de Arrendamiento'), ('RCE - Responsabilidad Civil', 'RCE - Responsabilidad Civil'), ('Arrendamiento', 'Arrendamiento'), ('Otra', 'Otra')], max_length=30, verbose_name='Tipo de Póliza Requerida'),
        ),
    ]

