from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0026_poliza_arrendamiento_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='seguimientopoliza',
            name='contrato',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos_poliza', to='gestion.contrato', verbose_name='Contrato'),
        ),
        migrations.AddField(
            model_name='seguimientopoliza',
            name='poliza_tipo',
            field=models.CharField(blank=True, choices=[('Cumplimiento', 'Cumplimiento'), ('RCE - Responsabilidad Civil', 'RCE - Responsabilidad Civil'), ('Arrendamiento', 'Arrendamiento'), ('Otra', 'Otra')], max_length=30, null=True, verbose_name='Tipo de Póliza'),
        ),
    ]

