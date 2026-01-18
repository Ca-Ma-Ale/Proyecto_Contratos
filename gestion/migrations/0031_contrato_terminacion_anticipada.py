from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('gestion', '0030_tipocontrato_catalogo'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='dias_terminacion_anticipada',
            field=models.IntegerField(
                default=60,
                validators=[MinValueValidator(0)],
                verbose_name='Terminación Anticipada (Días)',
            ),
        ),
    ]

