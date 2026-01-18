# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0038_calculofacturacionventas'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='cobro_administracion',
            field=models.BooleanField(default=False, verbose_name='Cobro Administración'),
        ),
    ]

