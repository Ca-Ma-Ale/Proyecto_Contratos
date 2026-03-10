from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0069_calculo_ipc_smlv_otrosi_referencia'),
    ]

    operations = [
        # Contrato
        migrations.AddField(
            model_name='contrato',
            name='recobro_poliza_rce',
            field=models.BooleanField(default=False, verbose_name='¿Aplica Recobro Póliza RCE?'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='recobro_poliza_cumplimiento',
            field=models.BooleanField(default=False, verbose_name='¿Aplica Recobro Póliza de Cumplimiento?'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='recobro_poliza_arrendamiento',
            field=models.BooleanField(default=False, verbose_name='¿Aplica Recobro Póliza de Arrendamiento?'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='recobro_poliza_todo_riesgo',
            field=models.BooleanField(default=False, verbose_name='¿Aplica Recobro Póliza Todo Riesgo?'),
        ),
        migrations.AddField(
            model_name='contrato',
            name='recobro_poliza_otra_1',
            field=models.BooleanField(default=False, verbose_name='¿Aplica Recobro Otras Pólizas?'),
        ),
        # RenovacionAutomatica
        migrations.AddField(
            model_name='renovacionautomatica',
            name='nuevo_recobro_poliza_rce',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza RCE?'),
        ),
        migrations.AddField(
            model_name='renovacionautomatica',
            name='nuevo_recobro_poliza_cumplimiento',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza de Cumplimiento?'),
        ),
        migrations.AddField(
            model_name='renovacionautomatica',
            name='nuevo_recobro_poliza_arrendamiento',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza de Arrendamiento?'),
        ),
        migrations.AddField(
            model_name='renovacionautomatica',
            name='nuevo_recobro_poliza_todo_riesgo',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza Todo Riesgo?'),
        ),
        migrations.AddField(
            model_name='renovacionautomatica',
            name='nuevo_recobro_poliza_otra_1',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Otras Pólizas?'),
        ),
        # OtroSi
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_recobro_poliza_rce',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza RCE?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_recobro_poliza_cumplimiento',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza de Cumplimiento?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_recobro_poliza_arrendamiento',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza de Arrendamiento?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_recobro_poliza_todo_riesgo',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Póliza Todo Riesgo?'),
        ),
        migrations.AddField(
            model_name='otrosi',
            name='nuevo_recobro_poliza_otra_1',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿Aplica Recobro Otras Pólizas?'),
        ),
    ]
