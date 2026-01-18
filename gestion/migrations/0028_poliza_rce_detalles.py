from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0027_seguimientos_poliza_contrato'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='valor_contratistas_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Contratistas y Subcontratistas Asegurados'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_dano_moral_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Daño Moral Asegurado'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_gastos_medicos_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Gastos Médicos de Terceros Asegurados'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_lucro_cesante_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Lucro Cesante Asegurado'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_patronal_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Patronal Asegurado'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_perjuicios_extrapatrimoniales_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Perjuicios Extrapatrimoniales Asegurados'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_propietario_locatario_ocupante_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='PLO (Propietario, Locatario y Ocupante) Asegurado'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='valor_vehiculos_rce',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Vehículos Propios y No Propios Asegurados'),
        ),
    ]

