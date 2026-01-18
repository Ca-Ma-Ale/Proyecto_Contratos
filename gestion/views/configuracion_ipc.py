"""
Vistas para el módulo de configuración de IPC (Tipos y Periodicidades)
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import TipoCondicionIPCForm, PeriodicidadIPCForm
from gestion.models import TipoCondicionIPC, PeriodicidadIPC


# ==================== TIPOS DE CONDICIÓN IPC ====================

@login_required_custom
def lista_tipos_condicion_ipc(request):
    """Lista todos los tipos de condición IPC"""
    tipos = TipoCondicionIPC.objects.all().order_by('orden', 'nombre')
    
    context = {
        'tipos': tipos,
        'titulo': 'Tipos de Condición IPC',
    }
    return render(request, 'gestion/ipc/configuracion/tipos_condicion_lista.html', context)


@admin_required
def nuevo_tipo_condicion_ipc(request):
    """Vista para agregar un nuevo tipo de condición IPC"""
    if request.method == 'POST':
        form = TipoCondicionIPCForm(request.POST)
        
        if form.is_valid():
            tipo = form.save()
            messages.success(request, f'Tipo de condición IPC "{tipo.nombre}" agregado exitosamente!')
            return redirect('gestion:lista_tipos_condicion_ipc')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = TipoCondicionIPCForm()
    
    context = {
        'form': form,
        'titulo': 'Nuevo Tipo de Condición IPC',
    }
    return render(request, 'gestion/ipc/configuracion/tipo_condicion_form.html', context)


@admin_required
def editar_tipo_condicion_ipc(request, tipo_id):
    """Vista para editar un tipo de condición IPC"""
    tipo = get_object_or_404(TipoCondicionIPC, id=tipo_id)
    
    if request.method == 'POST':
        form = TipoCondicionIPCForm(request.POST, instance=tipo)
        
        if form.is_valid():
            tipo = form.save()
            messages.success(request, f'Tipo de condición IPC "{tipo.nombre}" actualizado exitosamente!')
            return redirect('gestion:lista_tipos_condicion_ipc')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = TipoCondicionIPCForm(instance=tipo)
    
    context = {
        'form': form,
        'tipo': tipo,
        'titulo': f'Editar Tipo de Condición IPC: {tipo.nombre}',
    }
    return render(request, 'gestion/ipc/configuracion/tipo_condicion_form.html', context)


@admin_required
@require_http_methods(["POST"])
def eliminar_tipo_condicion_ipc(request, tipo_id):
    """Vista para eliminar un tipo de condición IPC"""
    tipo = get_object_or_404(TipoCondicionIPC, id=tipo_id)
    nombre = tipo.nombre
    
    # Verificar si está en uso
    from gestion.models import Contrato, OtroSi
    contratos = Contrato.objects.filter(tipo_condicion_ipc=tipo.codigo)
    otrosis = OtroSi.objects.filter(nuevo_tipo_condicion_ipc=tipo.codigo)
    
    if contratos.exists() or otrosis.exists():
        messages.error(
            request,
            f'No se puede eliminar el tipo "{nombre}" porque está en uso en {contratos.count()} contrato(s) y/o {otrosis.count()} otrosí.'
        )
        return redirect('gestion:lista_tipos_condicion_ipc')
    
    tipo.delete()
    messages.success(request, f'Tipo de condición IPC "{nombre}" eliminado exitosamente!')
    return redirect('gestion:lista_tipos_condicion_ipc')


# ==================== PERIODICIDADES IPC ====================

@login_required_custom
def lista_periodicidades_ipc(request):
    """Lista todas las periodicidades IPC"""
    periodicidades = PeriodicidadIPC.objects.all().order_by('orden', 'nombre')
    
    context = {
        'periodicidades': periodicidades,
        'titulo': 'Periodicidades IPC',
    }
    return render(request, 'gestion/ipc/configuracion/periodicidades_lista.html', context)


@admin_required
def nueva_periodicidad_ipc(request):
    """Vista para agregar una nueva periodicidad IPC"""
    if request.method == 'POST':
        form = PeriodicidadIPCForm(request.POST)
        
        if form.is_valid():
            periodicidad = form.save()
            messages.success(request, f'Periodicidad IPC "{periodicidad.nombre}" agregada exitosamente!')
            return redirect('gestion:lista_periodicidades_ipc')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = PeriodicidadIPCForm()
    
    context = {
        'form': form,
        'titulo': 'Nueva Periodicidad IPC',
    }
    return render(request, 'gestion/ipc/configuracion/periodicidad_form.html', context)


@admin_required
def editar_periodicidad_ipc(request, periodicidad_id):
    """Vista para editar una periodicidad IPC"""
    periodicidad = get_object_or_404(PeriodicidadIPC, id=periodicidad_id)
    
    if request.method == 'POST':
        form = PeriodicidadIPCForm(request.POST, instance=periodicidad)
        
        if form.is_valid():
            periodicidad = form.save()
            messages.success(request, f'Periodicidad IPC "{periodicidad.nombre}" actualizada exitosamente!')
            return redirect('gestion:lista_periodicidades_ipc')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = PeriodicidadIPCForm(instance=periodicidad)
    
    context = {
        'form': form,
        'periodicidad': periodicidad,
        'titulo': f'Editar Periodicidad IPC: {periodicidad.nombre}',
    }
    return render(request, 'gestion/ipc/configuracion/periodicidad_form.html', context)


@admin_required
@require_http_methods(["POST"])
def eliminar_periodicidad_ipc(request, periodicidad_id):
    """Vista para eliminar una periodicidad IPC"""
    periodicidad = get_object_or_404(PeriodicidadIPC, id=periodicidad_id)
    nombre = periodicidad.nombre
    
    # Verificar si está en uso
    from gestion.models import Contrato, OtroSi
    contratos = Contrato.objects.filter(periodicidad_ipc=periodicidad.codigo)
    otrosis = OtroSi.objects.filter(nueva_periodicidad_ipc=periodicidad.codigo)
    
    if contratos.exists() or otrosis.exists():
        messages.error(
            request,
            f'No se puede eliminar la periodicidad "{nombre}" porque está en uso en {contratos.count()} contrato(s) y/o {otrosis.count()} otrosí.'
        )
        return redirect('gestion:lista_periodicidades_ipc')
    
    periodicidad.delete()
    messages.success(request, f'Periodicidad IPC "{nombre}" eliminada exitosamente!')
    return redirect('gestion:lista_periodicidades_ipc')

