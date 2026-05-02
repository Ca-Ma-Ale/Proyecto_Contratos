from django import forms

from gestion.models import POLIZA_TIPO_CHOICES, POLIZA_ESTADO_CHOICES


class FiltroExportacionPolizasForm(forms.Form):
    TIPO_CHOICES = [('', 'Todos los tipos')] + list(POLIZA_TIPO_CHOICES)
    ESTADO_CHOICES = [('', 'Todos los estados')] + list(POLIZA_ESTADO_CHOICES)

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES, required=False, label='Tipo de Póliza',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    estado_aportado = forms.ChoiceField(
        choices=ESTADO_CHOICES, required=False, label='Estado Aportado',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fecha_vencimiento_desde = forms.DateField(
        required=False, label='Vence Desde',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_vencimiento_hasta = forms.DateField(
        required=False, label='Vence Hasta',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )


class FiltroExportacionSeguimientosForm(forms.Form):
    TIPO_CHOICES = [
        ('', 'Todos'),
        ('contrato', 'Solo Seguimientos de Contrato'),
        ('poliza', 'Solo Seguimientos de Póliza'),
    ]

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES, required=False, label='Tipo de Seguimiento',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fecha_desde = forms.DateField(
        required=False, label='Fecha Registro Desde',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_hasta = forms.DateField(
        required=False, label='Fecha Registro Hasta',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )


class FiltroExportacionVencimientosForm(forms.Form):
    ESTADO_CHOICES = [
        ('', 'Todos'),
        ('vigente', 'Solo Vigentes'),
        ('vencido', 'Solo Vencidos'),
    ]

    fecha_final_desde = forms.DateField(
        required=False, label='Fecha Final Desde',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_final_hasta = forms.DateField(
        required=False, label='Fecha Final Hasta',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES, required=False, label='Estado',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class FiltroExportacionHistorialAjustesForm(forms.Form):
    TIPO_CHOICES = [
        ('', 'Todos (IPC y SMLV)'),
        ('ipc', 'Solo IPC'),
        ('smlv', 'Solo Salario Mínimo'),
    ]
    ESTADO_CHOICES = [
        ('', 'Todos los estados'),
        ('PENDIENTE', 'Pendiente'),
        ('APLICADO', 'Aplicado'),
        ('ANULADO', 'Anulado'),
    ]

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES, required=False, label='Tipo de Ajuste',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES, required=False, label='Estado',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    año = forms.IntegerField(
        required=False, label='Año',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2025'}),
    )
    fecha_desde = forms.DateField(
        required=False, label='Fecha Aplicación Desde',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_hasta = forms.DateField(
        required=False, label='Fecha Aplicación Hasta',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
