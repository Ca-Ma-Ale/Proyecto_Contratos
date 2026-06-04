from django.db import migrations, models


POLIZA_TIPO_CHOICES = [
    ('Cumplimiento', 'Cumplimiento'),
    ('Poliza de Arrendamiento', 'Póliza de Arrendamiento'),
    ('RCE - Responsabilidad Civil', 'RCE - Responsabilidad Civil'),
    ('Arrendamiento', 'Arrendamiento'),
    ('Todo Riesgo', 'Todo Riesgo'),
    ('Otra', 'Otra'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0074_cambiar_sanciones_penalidades_a_textfield'),
    ]

    operations = [
        # Renombrar los 9 campos de RCE proveedor con nombres semánticos correctos
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_danos_materiales',
            new_name='rce_amparo_plo',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_responsabilidad_patronal',
            new_name='rce_amparo_patronal',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_gastos_medicos',
            new_name='rce_amparo_gastos_medicos',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_danos_bienes_terceros',
            new_name='rce_amparo_vehiculos',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_danos_contratistas',
            new_name='rce_amparo_contratistas',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_perjuicios_patrimoniales',
            new_name='rce_amparo_perjuicios_extrapatrimoniales',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_danos_ejecucion_contrato',
            new_name='rce_amparo_dano_moral',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_danos_predios_vecinos',
            new_name='rce_amparo_lucro_cesante',
        ),
        migrations.RenameField(
            model_name='poliza',
            old_name='rce_cobertura_muerte_terceros',
            new_name='rce_amparo_estabilidad_obra',
        ),
        # Eliminar los 3 campos que no se usan (lesiones, responsabilidad cruzada, gastos defensa)
        migrations.RemoveField(
            model_name='poliza',
            name='rce_cobertura_lesiones_personales',
        ),
        migrations.RemoveField(
            model_name='poliza',
            name='rce_cobertura_responsabilidad_cruzada',
        ),
        migrations.RemoveField(
            model_name='poliza',
            name='rce_cobertura_gastos_defensa',
        ),
        # Actualizar choices del campo tipo (agrega 'Todo Riesgo')
        migrations.AlterField(
            model_name='poliza',
            name='tipo',
            field=models.CharField(
                choices=POLIZA_TIPO_CHOICES,
                max_length=30,
                verbose_name='Tipo de Póliza',
            ),
        ),
        migrations.AlterField(
            model_name='requerimientopoliza',
            name='tipo',
            field=models.CharField(
                choices=POLIZA_TIPO_CHOICES,
                max_length=30,
                verbose_name='Tipo de Póliza Requerida',
            ),
        ),
        migrations.AlterField(
            model_name='seguimientopoliza',
            name='poliza_tipo',
            field=models.CharField(
                blank=True,
                choices=POLIZA_TIPO_CHOICES,
                max_length=30,
                null=True,
                verbose_name='Tipo de Póliza',
            ),
        ),
    ]
