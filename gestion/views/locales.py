from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import LocalForm
from gestion.models import Contrato, Local
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion


@login_required_custom
def nuevo_local(request):
    """Vista para crear un nuevo local"""
    if request.method == 'POST':
        form = LocalForm(request.POST)
        if form.is_valid():
            local = form.save(commit=False)
            guardar_con_auditoria(local, request.user, es_nuevo=True)
            local.save()
            messages.success(request, f'Local {local.nombre_comercial_stand} creado exitosamente!')
            next_url = request.GET.get('next', 'gestion:nuevo_contrato')
            return redirect(next_url)
    else:
        form = LocalForm()
    
    # Resolver next_url: si es un nombre de URL (contiene ':'), resolverlo; si es una URL completa, usarla tal cual
    next_param = request.GET.get('next', 'gestion:nuevo_contrato')
    if ':' in next_param and not next_param.startswith('http'):
        # Es un nombre de URL de Django, resolverlo
        try:
            next_url = reverse(next_param)
        except:
            next_url = reverse('gestion:nuevo_contrato')
    else:
        # Es una URL completa o relativa, usarla tal cual
        next_url = next_param
    
    context = {
        'form': form,
        'titulo': 'Nuevo Local',
        'next_url': next_url
    }
    return render(request, 'gestion/locales/form.html', context)


@login_required_custom
def lista_locales(request):
    """Vista para listar todos los locales"""
    locales = Local.objects.all().order_by('nombre_comercial_stand')
    
    context = {
        'locales': locales
    }
    return render(request, 'gestion/locales/lista.html', context)


@login_required_custom
def editar_local(request, local_id):
    """Vista para editar un local existente"""
    local = get_object_or_404(Local, id=local_id)
    
    if request.method == 'POST':
        form = LocalForm(request.POST, instance=local)
        if form.is_valid():
            local = form.save(commit=False)
            guardar_con_auditoria(local, request.user, es_nuevo=False)
            local.save()
            messages.success(request, f'Local {local.nombre_comercial_stand} actualizado exitosamente!')
            return redirect('gestion:lista_locales')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = LocalForm(instance=local)
    
    context = {
        'form': form,
        'titulo': f'Editar Local: {local.nombre_comercial_stand}',
        'local': local
    }
    return render(request, 'gestion/locales/form.html', context)


@admin_required
def eliminar_local(request, local_id):
    """Vista para eliminar un local"""
    local = get_object_or_404(Local, id=local_id)
    
    if request.method == 'POST':
        contratos_asociados = Contrato.objects.filter(local=local)
        if contratos_asociados.exists():
            messages.error(request, f'No se puede eliminar el local {local.nombre_comercial_stand} porque tiene {contratos_asociados.count()} contrato(s) asociado(s).')
            return redirect('gestion:lista_locales')
        
        registrar_eliminacion(local, request.user)
        nombre_local = local.nombre_comercial_stand
        local.delete()
        messages.success(request, f'Local {nombre_local} eliminado exitosamente!')
        return redirect('gestion:lista_locales')
    
    context = {
        'local': local,
        'titulo': 'Eliminar Local'
    }
    return render(request, 'gestion/locales/eliminar.html', context)

