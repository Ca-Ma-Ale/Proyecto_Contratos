from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0024_local_ubicacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='SeguimientoContrato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detalle', models.TextField(verbose_name='Detalle del seguimiento')),
                ('registrado_por', models.CharField(blank=True, max_length=150, null=True, verbose_name='Registrado por')),
                ('fecha_registro', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha de registro')),
                ('contrato', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos', to='gestion.contrato', verbose_name='Contrato')),
            ],
            options={
                'verbose_name': 'Seguimiento de Contrato',
                'verbose_name_plural': 'Seguimientos de Contrato',
                'ordering': ['-fecha_registro'],
            },
        ),
        migrations.CreateModel(
            name='SeguimientoPoliza',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detalle', models.TextField(verbose_name='Detalle del seguimiento')),
                ('registrado_por', models.CharField(blank=True, max_length=150, null=True, verbose_name='Registrado por')),
                ('fecha_registro', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha de registro')),
                ('poliza', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos', to='gestion.poliza', verbose_name='Póliza')),
                ('poliza_aportada', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos', to='gestion.polizaaportada', verbose_name='Póliza Aportada')),
            ],
            options={
                'verbose_name': 'Seguimiento de Póliza',
                'verbose_name_plural': 'Seguimientos de Póliza',
                'ordering': ['-fecha_registro'],
            },
        ),
    ]

