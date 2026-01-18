from django.db import migrations, models
import django.db.models.deletion

TIPOS_CONTRATO_DEFAULTS = [
    'AIRE ACONDICIONADO',
    'ANTENAS',
    'BODEGAS',
    'ESTACIONAMIENTO',
    'PUBLICIDAD',
    'STAND PRIMER PISO',
    'STAND SEGUNDO PISO',
    'STAND TERCER PISO',
    'ARRIENDO PLAZOLETA',
    'STAND SÓTANO',
]


def crear_tipos_contrato(apps, schema_editor):
    TipoContrato = apps.get_model('gestion', 'TipoContrato')
    Contrato = apps.get_model('gestion', 'Contrato')

    tipos_cache = {}
    for nombre in TIPOS_CONTRATO_DEFAULTS:
        tipo, _ = TipoContrato.objects.get_or_create(nombre=nombre)
        tipos_cache[nombre] = tipo

    for contrato in Contrato.objects.all():
        valor = getattr(contrato, 'tipo_contrato', None)
        if not valor:
            continue

        nombre = valor.strip().upper()
        tipo = tipos_cache.get(nombre)
        if not tipo:
            tipo, _ = TipoContrato.objects.get_or_create(nombre=nombre)
            tipos_cache[nombre] = tipo

        setattr(contrato, 'tipo_contrato_rel', tipo)
        contrato.save(update_fields=['tipo_contrato_rel'])


def revertir_tipos_contrato(apps, schema_editor):
    Contrato = apps.get_model('gestion', 'Contrato')

    for contrato in Contrato.objects.select_related('tipo_contrato_rel'):
        tipo = getattr(contrato, 'tipo_contrato_rel', None)
        if tipo:
            contrato.tipo_contrato = tipo.nombre
            contrato.save(update_fields=['tipo_contrato'])


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0029_alter_contrato_tipo_contrato_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoContrato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre Tipo de Contrato')),
            ],
            options={
                'verbose_name': 'Tipo de Contrato',
                'verbose_name_plural': 'Tipos de Contrato',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddField(
            model_name='contrato',
            name='tipo_contrato_rel',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='contratos', to='gestion.tipocontrato', verbose_name='Tipo de Contrato'),
        ),
        migrations.RunPython(crear_tipos_contrato, revertir_tipos_contrato),
        migrations.RemoveField(
            model_name='contrato',
            name='tipo_contrato',
        ),
        migrations.RenameField(
            model_name='contrato',
            old_name='tipo_contrato_rel',
            new_name='tipo_contrato',
        ),
        migrations.AlterField(
            model_name='contrato',
            name='tipo_contrato',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contratos', to='gestion.tipocontrato', verbose_name='Tipo de Contrato'),
        ),
    ]

