from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0070_recobro_polizas'),
    ]

    operations = [
        migrations.AddField(
            model_name='otrosi',
            name='nueva_prorroga_automatica',
            field=models.BooleanField(
                blank=True,
                null=True,
                verbose_name='Modificar Prórroga Automática',
                help_text='True activa la prórroga, False la desactiva, None = sin cambio en este OtroSí',
            ),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nueva_duracion_renovacion_meses',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='Nueva Duración de Renovación (Meses)',
                help_text='Duración de cada ciclo de renovación automática a partir de este OtroSí.',
            ),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='fecha_inicio_prorroga_automatica',
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name='Fecha de Inicio de Prórroga Automática',
                help_text='Se auto-llena desde effective_from al guardar.',
            ),
        ),
    ]
