from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from gestion.decorators import admin_required, login_required_custom
from gestion.forms import TerceroForm, ArrendatarioForm
from gestion.models import Tercero, Arrendatario, Contrato
from gestion.utils_auditoria import guardar_con_auditoria, registrar_eliminacion


@login_required_custom
def nuevo_arrendatario(request):
    """Vista para crear un nuevo tercero (arrendatario o proveedor)"""
    # Resolver next_url primero para usarlo en ambos casos
    next_param = request.GET.get('next', 'gestion:nuevo_contrato')
    if ':' in next_param and not next_param.startswith('http'):
        try:
            next_url = reverse(next_param)
        except:
            next_url = reverse('gestion:nuevo_contrato')
    else:
        next_url = next_param
    
    if request.method == 'POST':
        form = TerceroForm(request.POST)
        if form.is_valid():
            tercero = form.save(commit=False)
            # Asegurar que el tipo se guarde correctamente desde los datos del formulario
            # Si viene en POST, usar ese valor; si no, usar el valor por defecto del modelo
            tipo_value = request.POST.get('tipo') or form.cleaned_data.get('tipo') or 'ARRENDATARIO'
            if tipo_value in ['ARRENDATARIO', 'PROVEEDOR']:
                tercero.tipo = tipo_value
            guardar_con_auditoria(tercero, request.user, es_nuevo=True)
            tercero.save()
            tipo_display = tercero.get_tipo_display()
            messages.success(request, f'{tipo_display} {tercero.razon_social} creado exitosamente!')
            return redirect(next_url)
        else:
            # Manejar errores del formulario
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = TerceroForm()
        # Si viene un parámetro tipo, establecerlo por defecto
        tipo_param = request.GET.get('tipo', 'ARRENDATARIO')
        if tipo_param in ['ARRENDATARIO', 'PROVEEDOR']:
            form.fields['tipo'].initial = tipo_param
    
    context = {
        'form': form,
        'titulo': 'Nuevo Tercero',
        'next_url': next_url
    }
    return render(request, 'gestion/arrendatarios/form.html', context)


@login_required_custom
def lista_arrendatarios(request):
    """Vista para listar todos los terceros (arrendatarios y proveedores)"""
    tipo_filtro = request.GET.get('tipo', '')
    terceros = Tercero.objects.all().order_by('razon_social')
    
    if tipo_filtro in ['ARRENDATARIO', 'PROVEEDOR']:
        terceros = terceros.filter(tipo=tipo_filtro)
    
    context = {
        'terceros': terceros,
        'tipo_filtro': tipo_filtro
    }
    return render(request, 'gestion/arrendatarios/lista.html', context)


@login_required_custom
def editar_arrendatario(request, arrendatario_id):
    """Vista para editar un tercero existente"""
    tercero = get_object_or_404(Tercero, id=arrendatario_id)
    
    if request.method == 'POST':
        form = TerceroForm(request.POST, instance=tercero)
        if form.is_valid():
            tercero = form.save(commit=False)
            guardar_con_auditoria(tercero, request.user, es_nuevo=False)
            tercero.save()
            tipo_display = tercero.get_tipo_display()
            messages.success(request, f'{tipo_display} {tercero.razon_social} actualizado exitosamente!')
            return redirect('gestion:lista_arrendatarios')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = TerceroForm(instance=tercero)
    
    context = {
        'form': form,
        'titulo': f'Editar Tercero: {tercero.razon_social}',
        'tercero': tercero
    }
    return render(request, 'gestion/arrendatarios/form.html', context)


@admin_required
def eliminar_arrendatario(request, arrendatario_id):
    """Vista para eliminar un tercero"""
    tercero = get_object_or_404(Tercero, id=arrendatario_id)
    
    if request.method == 'POST':
        contratos_asociados = Contrato.objects.filter(
            models.Q(arrendatario=tercero) | models.Q(proveedor=tercero)
        )
        if contratos_asociados.exists():
            tipo_display = tercero.get_tipo_display()
            messages.error(request, f'No se puede eliminar el {tipo_display.lower()} {tercero.razon_social} porque tiene {contratos_asociados.count()} contrato(s) asociado(s).')
            return redirect('gestion:lista_arrendatarios')
        
        registrar_eliminacion(tercero, request.user)
        razon_social = tercero.razon_social
        tipo_display = tercero.get_tipo_display()
        tercero.delete()
        messages.success(request, f'{tipo_display} {razon_social} eliminado exitosamente!')
        return redirect('gestion:lista_arrendatarios')
    
    context = {
        'tercero': tercero,
        'titulo': 'Eliminar Tercero'
    }
    return render(request, 'gestion/arrendatarios/eliminar.html', context)

