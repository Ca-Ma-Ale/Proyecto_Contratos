from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from gestion.decorators import admin_required, login_required_custom
from gestion.models import (
    Clausula, ClausulaObligatoria, ClausulaContrato,
    TipoContrato, TipoServicio, Contrato
)


@login_required_custom
@admin_required
def parametrizar_clausulas(request):
    """Vista para parametrizar cláusulas obligatorias por tipo de contrato"""
    tipo_seleccionado = request.GET.get('tipo_contrato', 'CLIENTE')
    tipo_contrato_id = request.GET.get('tipo_contrato_id', None)
    tipo_servicio_id = request.GET.get('tipo_servicio_id', None)
    
    tipos_contrato = TipoContrato.objects.all().order_by('nombre')
    tipos_servicio = TipoServicio.objects.all().order_by('nombre')
    clausulas_disponibles = Clausula.objects.filter(activa=True).order_by('orden', 'titulo')
    
    clausulas_obligatorias = []
    if tipo_seleccionado == 'CLIENTE':
        if tipo_contrato_id:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                tipo_contrato_cliente_proveedor='CLIENTE',
                tipo_contrato_id=tipo_contrato_id,
                activa=True
            ).select_related('clausula', 'tipo_contrato')
        else:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                tipo_contrato_cliente_proveedor='CLIENTE',
                tipo_contrato__isnull=True,
                activa=True
            ).select_related('clausula')
    else:
        if tipo_servicio_id:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                tipo_contrato_cliente_proveedor='PROVEEDOR',
                tipo_servicio_id=tipo_servicio_id,
                activa=True
            ).select_related('clausula', 'tipo_servicio')
        else:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                tipo_contrato_cliente_proveedor='PROVEEDOR',
                tipo_servicio__isnull=True,
                activa=True
            ).select_related('clausula')
    
    clausulas_obligatorias_ids = [co.clausula_id for co in clausulas_obligatorias]
    
    context = {
        'tipo_seleccionado': tipo_seleccionado,
        'tipo_contrato_id': tipo_contrato_id,
        'tipo_servicio_id': tipo_servicio_id,
        'tipos_contrato': tipos_contrato,
        'tipos_servicio': tipos_servicio,
        'clausulas_disponibles': clausulas_disponibles,
        'clausulas_obligatorias': clausulas_obligatorias,
        'clausulas_obligatorias_ids': clausulas_obligatorias_ids,
    }
    
    return render(request, 'gestion/clausulas/parametrizar.html', context)


@login_required_custom
@admin_required
@require_http_methods(["POST"])
def guardar_parametrizacion_clausulas(request):
    """Guarda la parametrización de cláusulas obligatorias"""
    tipo_contrato = request.POST.get('tipo_contrato')
    tipo_contrato_id = request.POST.get('tipo_contrato_id') or None
    tipo_servicio_id = request.POST.get('tipo_servicio_id') or None
    clausulas_seleccionadas = request.POST.getlist('clausulas[]')
    
    if not tipo_contrato:
        messages.error(request, 'Debe seleccionar un tipo de contrato.')
        return redirect('gestion:parametrizar_clausulas')
    
    try:
        tipo_contrato_obj = None
        tipo_servicio_obj = None
        
        if tipo_contrato == 'CLIENTE':
            if tipo_contrato_id:
                tipo_contrato_obj = get_object_or_404(TipoContrato, id=tipo_contrato_id)
        else:
            if tipo_servicio_id:
                tipo_servicio_obj = get_object_or_404(TipoServicio, id=tipo_servicio_id)
        
        ClausulaObligatoria.objects.filter(
            tipo_contrato_cliente_proveedor=tipo_contrato,
            tipo_contrato=tipo_contrato_obj,
            tipo_servicio=tipo_servicio_obj
        ).update(activa=False)
        
        for clausula_id in clausulas_seleccionadas:
            clausula = get_object_or_404(Clausula, id=clausula_id, activa=True)
            ClausulaObligatoria.objects.update_or_create(
                clausula=clausula,
                tipo_contrato_cliente_proveedor=tipo_contrato,
                tipo_contrato=tipo_contrato_obj,
                tipo_servicio=tipo_servicio_obj,
                defaults={'activa': True, 'creado_por': request.user.username}
            )
        
        tipo_detalle = ''
        if tipo_contrato == 'CLIENTE':
            tipo_detalle = tipo_contrato_obj.nombre if tipo_contrato_obj else 'Todos los tipos'
        else:
            tipo_detalle = tipo_servicio_obj.nombre if tipo_servicio_obj else 'Todos los tipos'
        
        messages.success(
            request,
            f'Parametrización de cláusulas guardada exitosamente para {tipo_contrato} - {tipo_detalle}.'
        )
        
    except Exception as e:
        messages.error(request, f'Error al guardar la parametrización: {str(e)}')
    
    return redirect('gestion:parametrizar_clausulas')


@login_required_custom
@admin_required
def gestionar_clausulas(request):
    """Vista para gestionar las cláusulas disponibles (CRUD)"""
    clausulas = Clausula.objects.all().order_by('orden', 'titulo')
    
    context = {
        'clausulas': clausulas,
    }
    
    return render(request, 'gestion/clausulas/gestionar.html', context)


@login_required_custom
@admin_required
@require_http_methods(["POST"])
def crear_clausula(request):
    """Crea una nueva cláusula"""
    titulo = request.POST.get('titulo', '').strip()
    orden = request.POST.get('orden', 0)
    
    if not titulo:
        messages.error(request, 'El título de la cláusula es obligatorio.')
        return redirect('gestion:gestionar_clausulas')
    
    try:
        orden = int(orden) if orden else 0
        Clausula.objects.create(
            titulo=titulo,
            orden=orden,
            activa=True,
            creado_por=request.user.username
        )
        messages.success(request, f'Cláusula "{titulo}" creada exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al crear la cláusula: {str(e)}')
    
    return redirect('gestion:gestionar_clausulas')


@login_required_custom
@admin_required
@require_http_methods(["POST"])
def editar_clausula(request, clausula_id):
    """Edita una cláusula existente"""
    clausula = get_object_or_404(Clausula, id=clausula_id)
    titulo = request.POST.get('titulo', '').strip()
    orden = request.POST.get('orden', 0)
    activa = request.POST.get('activa') == 'on'
    
    if not titulo:
        messages.error(request, 'El título de la cláusula es obligatorio.')
        return redirect('gestion:gestionar_clausulas')
    
    try:
        orden = int(orden) if orden else 0
        clausula.titulo = titulo
        clausula.orden = orden
        clausula.activa = activa
        clausula.modificado_por = request.user.username
        clausula.save()
        messages.success(request, f'Cláusula "{titulo}" actualizada exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al actualizar la cláusula: {str(e)}')
    
    return redirect('gestion:gestionar_clausulas')


@login_required_custom
@admin_required
@require_http_methods(["POST"])
def eliminar_clausula(request, clausula_id):
    """Elimina una cláusula (desactiva)"""
    clausula = get_object_or_404(Clausula, id=clausula_id)
    
    try:
        clausula.activa = False
        clausula.eliminado_por = request.user.username
        clausula.save()
        messages.success(request, f'Cláusula "{clausula.titulo}" desactivada exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al desactivar la cláusula: {str(e)}')
    
    return redirect('gestion:gestionar_clausulas')


@login_required_custom
def auditoria_clausulas_contrato(request, contrato_id):
    """Vista para auditar las cláusulas de un contrato antes de guardarlo"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    tipo_contrato = contrato.tipo_contrato_cliente_proveedor
    tipo_contrato_obj = contrato.tipo_contrato
    tipo_servicio_obj = contrato.tipo_servicio
    
    clausulas_disponibles = Clausula.objects.filter(activa=True).order_by('orden', 'titulo')
    clausulas_contrato = ClausulaContrato.objects.filter(contrato=contrato).values_list('clausula_id', flat=True)
    
    clausulas_obligatorias = []
    if tipo_contrato == 'CLIENTE':
        if tipo_contrato_obj:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                Q(tipo_contrato_cliente_proveedor='CLIENTE'),
                Q(tipo_contrato=tipo_contrato_obj) | Q(tipo_contrato__isnull=True),
                activa=True
            ).select_related('clausula')
        else:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                tipo_contrato_cliente_proveedor='CLIENTE',
                tipo_contrato__isnull=True,
                activa=True
            ).select_related('clausula')
    else:
        if tipo_servicio_obj:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                Q(tipo_contrato_cliente_proveedor='PROVEEDOR'),
                Q(tipo_servicio=tipo_servicio_obj) | Q(tipo_servicio__isnull=True),
                activa=True
            ).select_related('clausula')
        else:
            clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                tipo_contrato_cliente_proveedor='PROVEEDOR',
                tipo_servicio__isnull=True,
                activa=True
            ).select_related('clausula')
    
    clausulas_obligatorias_ids = [co.clausula_id for co in clausulas_obligatorias]
    clausulas_faltantes = [
        co.clausula for co in clausulas_obligatorias
        if co.clausula_id not in clausulas_contrato
    ]
    
    context = {
        'contrato': contrato,
        'clausulas_disponibles': clausulas_disponibles,
        'clausulas_contrato': list(clausulas_contrato),
        'clausulas_obligatorias_ids': clausulas_obligatorias_ids,
        'clausulas_faltantes': clausulas_faltantes,
    }
    
    return render(request, 'gestion/clausulas/auditoria.html', context)


@login_required_custom
@require_http_methods(["POST"])
def guardar_clausulas_contrato(request, contrato_id):
    """Guarda las cláusulas seleccionadas para un contrato"""
    contrato = get_object_or_404(Contrato, id=contrato_id)
    clausulas_seleccionadas = request.POST.getlist('clausulas[]')
    continuar_sin_completar = request.POST.get('continuar_sin_completar', 'false') == 'true'
    
    try:
        ClausulaContrato.objects.filter(contrato=contrato).delete()
        
        for clausula_id in clausulas_seleccionadas:
            clausula = get_object_or_404(Clausula, id=clausula_id, activa=True)
            ClausulaContrato.objects.create(
                contrato=contrato,
                clausula=clausula,
                creado_por=request.user.username
            )
        
        tipo_contrato = contrato.tipo_contrato_cliente_proveedor
        tipo_contrato_obj = contrato.tipo_contrato
        tipo_servicio_obj = contrato.tipo_servicio
        
        clausulas_obligatorias = []
        if tipo_contrato == 'CLIENTE':
            if tipo_contrato_obj:
                clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                    Q(tipo_contrato_cliente_proveedor='CLIENTE'),
                    Q(tipo_contrato=tipo_contrato_obj) | Q(tipo_contrato__isnull=True),
                    activa=True
                ).values_list('clausula_id', flat=True)
            else:
                clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                    tipo_contrato_cliente_proveedor='CLIENTE',
                    tipo_contrato__isnull=True,
                    activa=True
                ).values_list('clausula_id', flat=True)
        else:
            if tipo_servicio_obj:
                clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                    Q(tipo_contrato_cliente_proveedor='PROVEEDOR'),
                    Q(tipo_servicio=tipo_servicio_obj) | Q(tipo_servicio__isnull=True),
                    activa=True
                ).values_list('clausula_id', flat=True)
            else:
                clausulas_obligatorias = ClausulaObligatoria.objects.filter(
                    tipo_contrato_cliente_proveedor='PROVEEDOR',
                    tipo_servicio__isnull=True,
                    activa=True
                ).values_list('clausula_id', flat=True)
        
        clausulas_seleccionadas_ids = [int(cid) for cid in clausulas_seleccionadas]
        clausulas_faltantes_ids = [
            cid for cid in clausulas_obligatorias
            if cid not in clausulas_seleccionadas_ids
        ]
        
        if clausulas_faltantes_ids and not continuar_sin_completar:
            clausulas_faltantes = Clausula.objects.filter(id__in=clausulas_faltantes_ids)
            return JsonResponse({
                'success': True,
                'tiene_advertencias': True,
                'clausulas_faltantes': [
                    {'id': c.id, 'titulo': c.titulo} for c in clausulas_faltantes
                ]
            })
        
        mensaje_exito = 'Cláusulas guardadas exitosamente.'
        if clausulas_faltantes_ids and continuar_sin_completar:
            clausulas_faltantes = Clausula.objects.filter(id__in=clausulas_faltantes_ids)
            titulos_faltantes = ', '.join([c.titulo for c in clausulas_faltantes])
            mensaje_exito = f'Contrato guardado con advertencia: Faltan {len(clausulas_faltantes)} cláusula(s) obligatoria(s): {titulos_faltantes}'
            messages.warning(request, mensaje_exito)
        else:
            messages.success(request, mensaje_exito)
        
        redirect_url = reverse('gestion:detalle_contrato', args=[contrato.id])
        
        return JsonResponse({
            'success': True,
            'tiene_advertencias': bool(clausulas_faltantes_ids),
            'mensaje': mensaje_exito,
            'redirect_url': redirect_url
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
