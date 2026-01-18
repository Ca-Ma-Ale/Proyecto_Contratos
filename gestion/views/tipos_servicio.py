from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import TipoServicioForm
from gestion.models import TipoServicio
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion


@login_required_custom
def nuevo_tipo_servicio(request):
    """Vista para crear un nuevo tipo de servicio"""
    if request.method == 'POST':
        form = TipoServicioForm(request.POST)
        if form.is_valid():
            tipo_servicio = form.save(commit=False)
            guardar_con_auditoria(tipo_servicio, request.user, es_nuevo=True)
            tipo_servicio.save()
            messages.success(request, f'Tipo de servicio {tipo_servicio.nombre} creado exitosamente!')
            next_url = request.GET.get('next', 'gestion:nuevo_contrato')
            return redirect(next_url)
    else:
        form = TipoServicioForm()

    context = {
        'form': form,
        'titulo': 'Nuevo Tipo de Servicio',
        'next_url': request.GET.get('next', 'gestion:nuevo_contrato')
    }
    return render(request, 'gestion/tipos_servicio/form.html', context)


@login_required_custom
def lista_tipos_servicio(request):
    """Vista para listar los tipos de servicio"""
    tipos_servicio = TipoServicio.objects.all()

    context = {
        'tipos_servicio': tipos_servicio
    }
    return render(request, 'gestion/tipos_servicio/lista.html', context)


@login_required_custom
def editar_tipo_servicio(request, tipo_id):
    """Vista para editar un tipo de servicio"""
    tipo_servicio = get_object_or_404(TipoServicio, id=tipo_id)

    if request.method == 'POST':
        form = TipoServicioForm(request.POST, instance=tipo_servicio)
        if form.is_valid():
            tipo_servicio = form.save(commit=False)
            guardar_con_auditoria(tipo_servicio, request.user, es_nuevo=False)
            tipo_servicio.save()
            messages.success(request, f'Tipo de servicio {tipo_servicio.nombre} actualizado exitosamente!')
            return redirect('gestion:lista_tipos_servicio')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = TipoServicioForm(instance=tipo_servicio)

    context = {
        'form': form,
        'titulo': f'Editar Tipo de Servicio: {tipo_servicio.nombre}',
        'tipo_servicio': tipo_servicio
    }
    return render(request, 'gestion/tipos_servicio/form.html', context)


@admin_required
def eliminar_tipo_servicio(request, tipo_id):
    """Vista para eliminar un tipo de servicio"""
    tipo_servicio = get_object_or_404(TipoServicio, id=tipo_id)

    if request.method == 'POST':
        if tipo_servicio.contratos.exists():
            messages.error(
                request,
                f'No se puede eliminar el tipo de servicio {tipo_servicio.nombre} porque tiene contratos asociados.'
            )
            return redirect('gestion:lista_tipos_servicio')

        registrar_eliminacion(tipo_servicio, request.user)
        nombre_tipo = tipo_servicio.nombre
        tipo_servicio.delete()
        messages.success(request, f'Tipo de servicio {nombre_tipo} eliminado exitosamente!')
        return redirect('gestion:lista_tipos_servicio')

    context = {
        'tipo_servicio': tipo_servicio,
        'titulo': 'Eliminar Tipo de Servicio'
    }
    return render(request, 'gestion/tipos_servicio/eliminar.html', context)

