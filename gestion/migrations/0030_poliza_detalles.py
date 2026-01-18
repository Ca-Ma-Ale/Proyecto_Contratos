from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0029_alter_contrato_tipo_contrato_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='poliza',
            name='valor_contratistas_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Contratistas y Subcontratistas Asegurados'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_dano_moral_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Daño Moral Asegurado'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_gastos_medicos_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Gastos Médicos de Terceros Asegurados'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_iva_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='IVA Asegurado (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_iva_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='IVA Asegurado (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_lucro_cesante_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Lucro Cesante Asegurado'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_otros_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Cuota de Administración Asegurada (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_otros_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Cuota de Administración Asegurada (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_patronal_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Patronal Asegurado'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_perjuicios_extrapatrimoniales_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Perjuicios Extrapatrimoniales Asegurados'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_propietario_locatario_ocupante_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='PLO (Propietario, Locatario y Ocupante) Asegurado'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_remuneraciones_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Remuneraciones Mensuales Aseguradas (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_remuneraciones_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Remuneraciones Mensuales Aseguradas (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_servicios_publicos_arrendamiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Servicios Públicos Asegurados (Arrendamiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_servicios_publicos_cumplimiento',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Servicios Públicos Asegurados (Cumplimiento)'),
        ),
        migrations.AddField(
            model_name='poliza',
            name='valor_vehiculos_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Vehículos Propios y No Propios Asegurados'),
        ),
    ]

