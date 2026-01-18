from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import TipoContratoForm
from gestion.models import TipoContrato
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion


@login_required_custom
def nuevo_tipo_contrato(request):
    """Vista para crear un nuevo tipo de contrato"""
    if request.method == 'POST':
        form = TipoContratoForm(request.POST)
        if form.is_valid():
            tipo_contrato = form.save(commit=False)
            guardar_con_auditoria(tipo_contrato, request.user, es_nuevo=True)
            tipo_contrato.save()
            messages.success(request, f'Tipo de contrato {tipo_contrato.nombre} creado exitosamente!')
            next_url = request.GET.get('next', 'gestion:nuevo_contrato')
            return redirect(next_url)
    else:
        form = TipoContratoForm()

    context = {
        'form': form,
        'titulo': 'Nuevo Tipo de Contrato',
        'next_url': request.GET.get('next', 'gestion:nuevo_contrato')
    }
    return render(request, 'gestion/tipos_contrato/form.html', context)


@login_required_custom
def lista_tipos_contrato(request):
    """Vista para listar los tipos de contrato"""
    tipos_contrato = TipoContrato.objects.all()

    context = {
        'tipos_contrato': tipos_contrato
    }
    return render(request, 'gestion/tipos_contrato/lista.html', context)


@login_required_custom
def editar_tipo_contrato(request, tipo_id):
    """Vista para editar un tipo de contrato"""
    tipo_contrato = get_object_or_404(TipoContrato, id=tipo_id)

    if request.method == 'POST':
        form = TipoContratoForm(request.POST, instance=tipo_contrato)
        if form.is_valid():
            tipo_contrato = form.save(commit=False)
            guardar_con_auditoria(tipo_contrato, request.user, es_nuevo=False)
            tipo_contrato.save()
            messages.success(request, f'Tipo de contrato {tipo_contrato.nombre} actualizado exitosamente!')
            return redirect('gestion:lista_tipos_contrato')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = TipoContratoForm(instance=tipo_contrato)

    context = {
        'form': form,
        'titulo': f'Editar Tipo de Contrato: {tipo_contrato.nombre}',
        'tipo_contrato': tipo_contrato
    }
    return render(request, 'gestion/tipos_contrato/form.html', context)


@admin_required
def eliminar_tipo_contrato(request, tipo_id):
    """Vista para eliminar un tipo de contrato"""
    tipo_contrato = get_object_or_404(TipoContrato, id=tipo_id)

    if request.method == 'POST':
        if tipo_contrato.contratos.exists():
            messages.error(
                request,
                f'No se puede eliminar el tipo de contrato {tipo_contrato.nombre} porque tiene contratos asociados.'
            )
            return redirect('gestion:lista_tipos_contrato')

        registrar_eliminacion(tipo_contrato, request.user)
        nombre_tipo = tipo_contrato.nombre
        tipo_contrato.delete()
        messages.success(request, f'Tipo de contrato {nombre_tipo} eliminado exitosamente!')
        return redirect('gestion:lista_tipos_contrato')

    context = {
        'tipo_contrato': tipo_contrato,
        'titulo': 'Eliminar Tipo de Contrato'
    }
    return render(request, 'gestion/tipos_contrato/eliminar.html', context)

