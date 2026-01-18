from django.contrib import messages
from django.shortcuts import redirect, render

from gestion.decorators import admin_required
from gestion.forms import ConfiguracionEmpresaForm
from gestion.models import ConfiguracionEmpresa
from gestion.utils_auditoria import guardar_con_auditoria
from .utils import obtener_configuracion_empresa


@admin_required
def configuracion_empresa(request):
    """Vista para gestionar la configuración de la empresa"""
    configuracion = ConfiguracionEmpresa.objects.filter(activo=True).order_by('-fecha_creacion').first()
    if configuracion is None:
        configuracion = ConfiguracionEmpresa.objects.order_by('-fecha_creacion').first()
    
    if request.method == 'POST':
        form = ConfiguracionEmpresaForm(request.POST, instance=configuracion)
        if form.is_valid():
            configuracion = form.save(commit=False)
            es_nuevo = configuracion.pk is None
            guardar_con_auditoria(configuracion, request.user, es_nuevo=es_nuevo)
            configuracion.save()
            messages.success(request, 'Configuración de empresa actualizada exitosamente!')
            return redirect('gestion:configuracion_empresa')
        else:
            from gestion.utils import agregar_errores_formulario_a_mensajes
            agregar_errores_formulario_a_mensajes(request, form)
    else:
        form = ConfiguracionEmpresaForm(instance=configuracion)
    
    context = {
        'form': form,
        'configuracion': configuracion,
        'titulo': 'Configuración de Empresa'
    }
    return render(request, 'gestion/configuracion/empresa.html', context)

