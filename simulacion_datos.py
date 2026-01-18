#!/usr/bin/env python
"""
Script de simulación de datos para el sistema de gestión de contratos.
Genera al menos 20 contratos con diferentes escenarios:
- Contratos activos, vencidos, por vencer
- Otrosí (modificaciones) para cada contrato
- Pólizas (RCE, Cumplimiento, Arrendamiento) con diferentes estados
- Reportes de ventas
- Cálculos de facturación
- Diferentes modalidades y tipos
"""

import os
import sys
import django
from datetime import date, timedelta, datetime
from decimal import Decimal
import random
from calendar import monthrange

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratos.settings')
django.setup()

from gestion.models import (
    ConfiguracionEmpresa, Arrendatario, Local, Contrato,
    Poliza, OtroSi, RequerimientoPoliza, TipoContrato,
    InformeVentas, CalculoFacturacionVentas
)
from gestion.utils import calcular_fecha_vencimiento
from gestion.utils_otrosi import obtener_valores_vigentes_facturacion_ventas
from django.utils import timezone

TIPO_CONTRATO_MAPA_SIMULACION = {
    'Concesión de Espacio': 'STAND PRIMER PISO',
    'Arrendamiento Local': 'STAND SEGUNDO PISO',
    'Licencia de Uso': 'PUBLICIDAD',
    'Otro': 'ARRIENDO PLAZOLETA',
}

TIPOS_CONTRATO_PREDETERMINADOS = [
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


def asegurar_tipos_contrato():
    """Garantiza que existan los tipos de contrato requeridos y retorna un mapa nombre -> instancia."""
    tipos = {}
    for nombre in TIPOS_CONTRATO_PREDETERMINADOS:
        tipo_obj, _ = TipoContrato.objects.get_or_create(nombre=nombre)
        tipos[nombre] = tipo_obj
    return tipos

def crear_configuracion_empresa():
    """Crea la configuración de empresa si no existe"""
    if not ConfiguracionEmpresa.objects.exists():
        empresa = ConfiguracionEmpresa.objects.create(
            nombre_empresa="Centro Comercial Simulación",
            nit_empresa="900123456-7",
            representante_legal="María González Pérez",
            direccion="Carrera 15 # 93-07, Bogotá D.C.",
            telefono="+57 1 234-5678",
            email="admin@centrocomercial.com",
            activo=True
        )
        return empresa
    else:
        return ConfiguracionEmpresa.objects.first()

def crear_arrendatarios():
    """Crea arrendatarios de prueba"""
    arrendatarios_data = [
        {
            'nit': '800123456-1',
            'razon_social': 'Tienda de Ropa Fashion S.A.S.',
            'nombre_rep_legal': 'Carlos Mendoza',
            'nombre_supervisor_op': 'Ana López',
            'email_supervisor_op': 'ana.lopez@fashion.com'
        },
        {
            'nit': '800234567-2',
            'razon_social': 'Electrodomésticos del Norte Ltda.',
            'nombre_rep_legal': 'Roberto Silva',
            'nombre_supervisor_op': 'María Rodríguez',
            'email_supervisor_op': 'maria.rodriguez@electro.com'
        },
        {
            'nit': '800345678-3',
            'razon_social': 'Restaurante El Buen Sabor S.A.S.',
            'nombre_rep_legal': 'Patricia Vega',
            'nombre_supervisor_op': 'Luis Herrera',
            'email_supervisor_op': 'luis.herrera@buensabor.com'
        },
        {
            'nit': '800456789-4',
            'razon_social': 'Farmacia Salud Total S.A.S.',
            'nombre_rep_legal': 'Dr. Fernando Castro',
            'nombre_supervisor_op': 'Carmen Díaz',
            'email_supervisor_op': 'carmen.diaz@saludtotal.com'
        },
        {
            'nit': '800567890-5',
            'razon_social': 'Tecnología Avanzada Ltda.',
            'nombre_rep_legal': 'Ing. Sandra Morales',
            'nombre_supervisor_op': 'Diego Ramírez',
            'email_supervisor_op': 'diego.ramirez@tecnologia.com'
        },
        {
            'nit': '800678901-6',
            'razon_social': 'Joyería Diamantes S.A.S.',
            'nombre_rep_legal': 'Alberto Jiménez',
            'nombre_supervisor_op': 'Isabel Torres',
            'email_supervisor_op': 'isabel.torres@diamantes.com'
        },
        {
            'nit': '800789012-7',
            'razon_social': 'Deportes Extremos S.A.S.',
            'nombre_rep_legal': 'Miguel Ángel Ruiz',
            'nombre_supervisor_op': 'Valentina Sánchez',
            'email_supervisor_op': 'valentina.sanchez@deportes.com'
        },
        {
            'nit': '800890123-8',
            'razon_social': 'Librería El Saber S.A.S.',
            'nombre_rep_legal': 'Prof. Elena Vargas',
            'nombre_supervisor_op': 'Andrés Moreno',
            'email_supervisor_op': 'andres.moreno@elsaber.com'
        },
        {
            'nit': '800901234-9',
            'razon_social': 'Café Gourmet Express S.A.S.',
            'nombre_rep_legal': 'Catalina Herrera',
            'nombre_supervisor_op': 'Jorge Martínez',
            'email_supervisor_op': 'jorge.martinez@cafegourmet.com'
        },
        {
            'nit': '801012345-0',
            'razon_social': 'Muebles y Decoración S.A.S.',
            'nombre_rep_legal': 'Ricardo Peña',
            'nombre_supervisor_op': 'Natalia Gómez',
            'email_supervisor_op': 'natalia.gomez@muebles.com'
        },
        {
            'nit': '801123456-1',
            'razon_social': 'Óptica Visión Clara S.A.S.',
            'nombre_rep_legal': 'Dr. Oscar Martínez',
            'nombre_supervisor_op': 'Laura Fernández',
            'email_supervisor_op': 'laura.fernandez@visionclara.com'
        },
        {
            'nit': '801234567-2',
            'razon_social': 'Perfumería Elegante S.A.S.',
            'nombre_rep_legal': 'Sofía Ramírez',
            'nombre_supervisor_op': 'Carlos Andrade',
            'email_supervisor_op': 'carlos.andrade@elegante.com'
        },
        {
            'nit': '801345678-3',
            'razon_social': 'Zapatería Moderna Ltda.',
            'nombre_rep_legal': 'Pedro Gómez',
            'nombre_supervisor_op': 'Mónica Suárez',
            'email_supervisor_op': 'monica.suarez@zapateria.com'
        },
        {
            'nit': '801456789-4',
            'razon_social': 'Supermercado Express S.A.S.',
            'nombre_rep_legal': 'Juan Carlos Pérez',
            'nombre_supervisor_op': 'Diana Castro',
            'email_supervisor_op': 'diana.castro@express.com'
        },
        {
            'nit': '801567890-5',
            'razon_social': 'Tienda de Mascotas PetLove S.A.S.',
            'nombre_rep_legal': 'Andrea Morales',
            'nombre_supervisor_op': 'Felipe Torres',
            'email_supervisor_op': 'felipe.torres@petlove.com'
        }
    ]
    
    arrendatarios = []
    for data in arrendatarios_data:
        arrendatario, created = Arrendatario.objects.get_or_create(
            nit=data['nit'],
            defaults=data
        )
        if created:
        arrendatarios.append(arrendatario)
    
    return arrendatarios

def crear_locales():
    """Crea locales de prueba"""
    locales_data = [
        {'nombre_comercial_stand': 'Local A-101', 'total_area_m2': Decimal('45.50')},
        {'nombre_comercial_stand': 'Local A-102', 'total_area_m2': Decimal('38.75')},
        {'nombre_comercial_stand': 'Local A-103', 'total_area_m2': Decimal('52.25')},
        {'nombre_comercial_stand': 'Local B-201', 'total_area_m2': Decimal('67.80')},
        {'nombre_comercial_stand': 'Local B-202', 'total_area_m2': Decimal('41.30')},
        {'nombre_comercial_stand': 'Local B-203', 'total_area_m2': Decimal('58.90')},
        {'nombre_comercial_stand': 'Local C-301', 'total_area_m2': Decimal('72.15')},
        {'nombre_comercial_stand': 'Local C-302', 'total_area_m2': Decimal('35.60')},
        {'nombre_comercial_stand': 'Local C-303', 'total_area_m2': Decimal('48.40')},
        {'nombre_comercial_stand': 'Local D-401', 'total_area_m2': Decimal('85.20')},
        {'nombre_comercial_stand': 'Local D-402', 'total_area_m2': Decimal('29.75')},
        {'nombre_comercial_stand': 'Local D-403', 'total_area_m2': Decimal('63.45')},
        {'nombre_comercial_stand': 'Local E-501', 'total_area_m2': Decimal('91.30')},
        {'nombre_comercial_stand': 'Local E-502', 'total_area_m2': Decimal('44.85')},
        {'nombre_comercial_stand': 'Local E-503', 'total_area_m2': Decimal('76.50')},
        {'nombre_comercial_stand': 'Local F-601', 'total_area_m2': Decimal('55.20')},
        {'nombre_comercial_stand': 'Local F-602', 'total_area_m2': Decimal('39.90')},
        {'nombre_comercial_stand': 'Local F-603', 'total_area_m2': Decimal('68.75')},
        {'nombre_comercial_stand': 'Local G-701', 'total_area_m2': Decimal('82.40')},
        {'nombre_comercial_stand': 'Local G-702', 'total_area_m2': Decimal('47.60')},
        {'nombre_comercial_stand': 'Local G-703', 'total_area_m2': Decimal('71.25')},
        {'nombre_comercial_stand': 'Local H-801', 'total_area_m2': Decimal('96.80')},
        {'nombre_comercial_stand': 'Local H-802', 'total_area_m2': Decimal('33.45')},
        {'nombre_comercial_stand': 'Local H-803', 'total_area_m2': Decimal('59.30')},
        {'nombre_comercial_stand': 'Local I-901', 'total_area_m2': Decimal('74.65')},
        {'nombre_comercial_stand': 'Local I-902', 'total_area_m2': Decimal('42.10')},
        {'nombre_comercial_stand': 'Local I-903', 'total_area_m2': Decimal('65.85')},
        {'nombre_comercial_stand': 'Local J-1001', 'total_area_m2': Decimal('88.90')},
        {'nombre_comercial_stand': 'Local J-1002', 'total_area_m2': Decimal('36.70')},
        {'nombre_comercial_stand': 'Local J-1003', 'total_area_m2': Decimal('53.20')}
    ]
    
    locales = []
    for data in locales_data:
        local, created = Local.objects.get_or_create(
            nombre_comercial_stand=data['nombre_comercial_stand'],
            defaults=data
        )
        if created:
        locales.append(local)
    
    return locales

def generar_fecha_aleatoria(dias_atras=365, dias_adelante=365):
    """Genera una fecha aleatoria entre el rango especificado"""
    fecha_inicio = date.today() - timedelta(days=dias_atras)
    fecha_fin = date.today() + timedelta(days=dias_adelante)
    rango_dias = (fecha_fin - fecha_inicio).days
    return fecha_inicio + timedelta(days=random.randint(0, rango_dias))

def mes_nombre_offset(offset_meses: int) -> str:
    """Devuelve el nombre del mes (ES) desplazado desde hoy por offset_meses."""
    meses = ['ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE']
    hoy = date.today()
    idx = (hoy.month - 1 + offset_meses) % 12
    return meses[idx]

def crear_contratos(arrendatarios, locales):
    """Crea al menos 20 contratos con diferentes escenarios"""
    tipos_contrato_catalogo = asegurar_tipos_contrato()
    
    # Definir escenarios de contratos
    escenarios = [
        # Contratos por vencer (próximos 30-90 días)
        {'escenario': 'por_vencer', 'dias_inicio': -300, 'duracion': 12, 'modalidad': 'Hibrido (Min Garantizado)', 'reporta_ventas': True},
        {'escenario': 'por_vencer', 'dias_inicio': -450, 'duracion': 18, 'modalidad': 'Variable Puro', 'reporta_ventas': True},
        {'escenario': 'por_vencer', 'dias_inicio': -330, 'duracion': 12, 'modalidad': 'Fijo', 'reporta_ventas': False},
        
        # Contratos activos (vigentes)
        {'escenario': 'activo', 'dias_inicio': -200, 'duracion': 24, 'modalidad': 'Hibrido (Min Garantizado)', 'reporta_ventas': True},
        {'escenario': 'activo', 'dias_inicio': -150, 'duracion': 12, 'modalidad': 'Variable Puro', 'reporta_ventas': True},
        {'escenario': 'activo', 'dias_inicio': -100, 'duracion': 36, 'modalidad': 'Fijo', 'reporta_ventas': False},
        {'escenario': 'activo', 'dias_inicio': -180, 'duracion': 18, 'modalidad': 'Hibrido (Min Garantizado)', 'reporta_ventas': True},
        {'escenario': 'activo', 'dias_inicio': -250, 'duracion': 24, 'modalidad': 'Variable Puro', 'reporta_ventas': True},
        {'escenario': 'activo', 'dias_inicio': -120, 'duracion': 12, 'modalidad': 'Fijo', 'reporta_ventas': False},
        
        # Contratos recientes
        {'escenario': 'reciente', 'dias_inicio': -30, 'duracion': 12, 'modalidad': 'Hibrido (Min Garantizado)', 'reporta_ventas': True},
        {'escenario': 'reciente', 'dias_inicio': -60, 'duracion': 24, 'modalidad': 'Variable Puro', 'reporta_ventas': True},
        {'escenario': 'reciente', 'dias_inicio': -45, 'duracion': 18, 'modalidad': 'Fijo', 'reporta_ventas': False},
        
        # Contratos antiguos (cerca de vencer)
        {'escenario': 'antiguo', 'dias_inicio': -600, 'duracion': 24, 'modalidad': 'Hibrido (Min Garantizado)', 'reporta_ventas': True},
        {'escenario': 'antiguo', 'dias_inicio': -700, 'duracion': 36, 'modalidad': 'Variable Puro', 'reporta_ventas': True},
        {'escenario': 'antiguo', 'dias_inicio': -800, 'duracion': 36, 'modalidad': 'Fijo', 'reporta_ventas': False},
        
        # Contratos vencidos
        {'escenario': 'vencido', 'dias_inicio': -400, 'duracion': 12, 'modalidad': 'Hibrido (Min Garantizado)', 'reporta_ventas': True},
        {'escenario': 'vencido', 'dias_inicio': -500, 'duracion': 18, 'modalidad': 'Variable Puro', 'reporta_ventas': True},
        {'escenario': 'vencido', 'dias_inicio': -380, 'duracion': 12, 'modalidad': 'Fijo', 'reporta_ventas': False},
        
        # Contratos con IPC próximo
        {'escenario': 'ipc_proximo', 'dias_inicio': -720, 'duracion': 36, 'modalidad': 'Hibrido (Min Garantizado)', 'reporta_ventas': True},
        {'escenario': 'ipc_proximo', 'dias_inicio': -400, 'duracion': 24, 'modalidad': 'Variable Puro', 'reporta_ventas': True},
    ]
    
    objetos_destinacion = [
        'Concesión de espacio comercial para venta de ropa y accesorios',
        'Concesión de espacio para restaurante',
        'Concesión de espacio para farmacia',
        'Arrendamiento de local para tecnología',
        'Concesión de espacio para joyería',
        'Arrendamiento de local para deportes',
        'Concesión de espacio para librería',
        'Concesión de espacio para muebles',
        'Arrendamiento de local para tecnología avanzada',
        'Concesión de espacio para accesorios',
        'Concesión de espacio para óptica',
        'Concesión de espacio para perfumería',
        'Arrendamiento de local para zapatería',
        'Concesión de espacio para supermercado',
        'Concesión de espacio para tienda de mascotas',
        'Arrendamiento de local para café',
        'Concesión de espacio para electrónica',
        'Arrendamiento de local para servicios',
        'Concesión de espacio para juguetería',
        'Arrendamiento de local para servicios financieros',
    ]
    
    contratos = []
    for i, esc in enumerate(escenarios):
        num_contrato = f'CON-2024-{str(i+1).zfill(3)}'
        
        # Seleccionar arrendatario y local aleatorios
        arrendatario = random.choice(arrendatarios)
        local = random.choice(locales)
        
        # Seleccionar tipo de contrato
        tipo_nombre = random.choice(['STAND PRIMER PISO', 'STAND SEGUNDO PISO', 'PUBLICIDAD', 'ARRIENDO PLAZOLETA'])
        tipo_contrato_obj = tipos_contrato_catalogo.get(tipo_nombre)
        if not tipo_contrato_obj:
            tipo_contrato_obj, _ = TipoContrato.objects.get_or_create(nombre=tipo_nombre)
            tipos_contrato_catalogo[tipo_nombre] = tipo_contrato_obj
        
        # Calcular fechas
        fecha_inicial = date.today() + timedelta(days=esc['dias_inicio'])
        fecha_firma = fecha_inicial - timedelta(days=random.randint(1, 30))
        fecha_final_inicial = calcular_fecha_vencimiento(fecha_inicial, esc['duracion'])
        fecha_final_actualizada = fecha_final_inicial
        
        # Valores financieros según modalidad
        valor_canon_fijo = None
        canon_minimo_garantizado = None
        porcentaje_ventas = None
        
        if esc['modalidad'] == 'Fijo':
            valor_canon_fijo = Decimal(random.randint(1500000, 5000000))
        elif esc['modalidad'] == 'Variable Puro':
            porcentaje_ventas = Decimal(random.uniform(6.0, 15.0)).quantize(Decimal('0.1'))
        else:  # Híbrido
            valor_canon_fijo = Decimal(random.randint(2000000, 4000000))
            canon_minimo_garantizado = Decimal(random.randint(1500000, 3000000))
            porcentaje_ventas = Decimal(random.uniform(7.0, 12.0)).quantize(Decimal('0.1'))
        
        # Configurar pólizas (algunos contratos tienen, otros no)
        exige_rce = random.choice([True, True, True, False])  # 75% tienen RCE
        exige_cumplimiento = random.choice([True, True, False])  # 66% tienen cumplimiento
        exige_arrendamiento = random.choice([True, False, False])  # 33% tienen arrendamiento
        
        # Crear contrato
        contrato, created = Contrato.objects.get_or_create(
            num_contrato=num_contrato,
            defaults={
                'objeto_destinacion': objetos_destinacion[i % len(objetos_destinacion)],
                'tipo_contrato': tipo_contrato_obj,
                'nit_concedente': "900123456-7",
                'rep_legal_concedente': "María González Pérez",
                'marca_comercial': f"Marca {arrendatario.razon_social.split()[0]}",
                'supervisor_concedente': "Ana Supervisor",
                'supervisor_concesionario': arrendatario.nombre_supervisor_op,
                'fecha_firma': fecha_firma,
                'duracion_inicial_meses': esc['duracion'],
                'fecha_inicial_contrato': fecha_inicial,
                'fecha_final_inicial': fecha_final_inicial,
                'fecha_final_actualizada': fecha_final_actualizada,
                'prorroga_automatica': random.choice([True, False]),
                'dias_preaviso_no_renovacion': random.choice([30, 60, 90]),
                'dias_terminacion_anticipada': random.choice([30, 45, 60, 90]),
                'vigente': esc['escenario'] != 'vencido',
                'modalidad_pago': esc['modalidad'],
                'valor_canon_fijo': valor_canon_fijo,
                'canon_minimo_garantizado': canon_minimo_garantizado,
                'porcentaje_ventas': porcentaje_ventas,
                'reporta_ventas': esc['reporta_ventas'],
                'dia_limite_reporte_ventas': random.choice([5, 10, 15]) if esc['reporta_ventas'] else None,
                'cobra_servicios_publicos_aparte': random.choice([True, False]),
                'interes_mora_pagos': f"{random.randint(1, 3)}% mensual",
                'tipo_condicion_ipc': 'IPC',
                'puntos_adicionales_ipc': Decimal(random.uniform(1.0, 3.0)).quantize(Decimal('0.1')),
                'periodicidad_ipc': random.choice(['ANUAL', 'FECHA_ESPECIFICA']),
                'mes_aumento_ipc': random.choice(['ENERO', 'JULIO', mes_nombre_offset(1)]),
                'tiene_periodo_gracia': random.choice([True, False]),
                'fecha_inicio_periodo_gracia': fecha_inicial + timedelta(days=30) if random.choice([True, False]) else None,
                'fecha_fin_periodo_gracia': fecha_inicial + timedelta(days=90) if random.choice([True, False]) else None,
                'condicion_gracia': "Periodo de gracia de 3 meses" if random.choice([True, False]) else None,
                'exige_poliza_rce': exige_rce,
                'valor_asegurado_rce': Decimal(random.randint(30000000, 100000000)) if exige_rce else None,
                'meses_vigencia_rce': 12 if exige_rce else None,
                'exige_poliza_cumplimiento': exige_cumplimiento,
                'valor_asegurado_cumplimiento': Decimal(random.randint(8000000, 20000000)) if exige_cumplimiento else None,
                'meses_vigencia_cumplimiento': 12 if exige_cumplimiento else None,
                'exige_poliza_arrendamiento': exige_arrendamiento,
                'valor_asegurado_arrendamiento': Decimal(random.randint(10000000, 30000000)) if exige_arrendamiento else None,
                'meses_vigencia_arrendamiento': 12 if exige_arrendamiento else None,
                'clausula_penal_incumplimiento': Decimal(random.randint(500000, 2000000)),
                'penalidad_terminacion_anticipada': Decimal(random.randint(1000000, 3000000)),
                'multa_mora_no_restitucion': Decimal(random.randint(300000, 1000000)),
                'arrendatario': arrendatario,
                'local': local
            }
        )
        
        if created:
        contratos.append(contrato)
    
    return contratos

def crear_requerimientos_polizas(contratos):
    """Crea requerimientos de pólizas para cada contrato"""
    for contrato in contratos:
        # RCE
        if contrato.exige_poliza_rce and contrato.valor_asegurado_rce:
            RequerimientoPoliza.objects.get_or_create(
                contrato=contrato,
                tipo='RCE - Responsabilidad Civil',
                defaults={
                    'valor_asegurado_requerido': contrato.valor_asegurado_rce,
                    'vigencia_requerida_meses': contrato.meses_vigencia_rce or 12,
                    'condiciones_especiales': 'Cobertura para daños a terceros en el ejercicio de la actividad comercial',
                    'observaciones': 'Póliza requerida según cláusula contractual'
                }
            )
        
        # Cumplimiento
        if contrato.exige_poliza_cumplimiento and contrato.valor_asegurado_cumplimiento:
            RequerimientoPoliza.objects.get_or_create(
                contrato=contrato,
                tipo='Cumplimiento',
                defaults={
                    'valor_asegurado_requerido': contrato.valor_asegurado_cumplimiento,
                    'vigencia_requerida_meses': contrato.meses_vigencia_cumplimiento or 12,
                    'condiciones_especiales': 'Garantía de cumplimiento de las obligaciones contractuales',
                    'observaciones': 'Póliza requerida según cláusula contractual'
                }
            )
        
        # Arrendamiento
        if contrato.exige_poliza_arrendamiento and contrato.valor_asegurado_arrendamiento:
            RequerimientoPoliza.objects.get_or_create(
                contrato=contrato,
                tipo='Poliza de Arrendamiento',
                defaults={
                    'valor_asegurado_requerido': contrato.valor_asegurado_arrendamiento,
                    'vigencia_requerida_meses': contrato.meses_vigencia_arrendamiento or 12,
                    'condiciones_especiales': 'Póliza de arrendamiento para garantizar el pago de cánones',
                    'observaciones': 'Póliza requerida según cláusula contractual'
                }
            )

def crear_polizas(contratos):
    """Crea pólizas con diferentes estados"""
    aseguradoras = [
        'Seguros Bolívar S.A.',
        'Seguros del Estado S.A.',
        'Sura Seguros S.A.',
        'Colseguros S.A.',
        'Liberty Seguros S.A.',
        'Mapfre Seguros S.A.',
        'Allianz Seguros S.A.',
        'HDI Seguros S.A.'
    ]
    
    for contrato in contratos:
        requerimientos = RequerimientoPoliza.objects.filter(contrato=contrato)
        
        for req in requerimientos:
            # Determinar estado de la póliza (vigente, vencida, por vencer)
            fecha_inicio = contrato.fecha_inicial_contrato
            fecha_vencimiento_base = calcular_fecha_vencimiento(fecha_inicio, req.vigencia_requerida_meses)
            
            # Distribuir estados: 40% vigentes, 30% vencidas, 30% por vencer
            estado_random = random.random()
            if estado_random < 0.3:  # Vencidas
                fecha_vencimiento = date.today() - timedelta(days=random.randint(15, 180))
            elif estado_random < 0.6:  # Por vencer
                fecha_vencimiento = date.today() + timedelta(days=random.randint(10, 60))
            else:  # Vigentes
                fecha_vencimiento = date.today() + timedelta(days=random.randint(90, 365))
            
            # Determinar tipo de entrega
            estado_aportado = random.choice(['Aporte inicial', 'Actualización', 'Prórroga'])
            
            # Crear póliza
            numero_poliza = f'{req.tipo[:3]}-{contrato.num_contrato}-{random.randint(1000, 9999)}'
            poliza, created = Poliza.objects.get_or_create(
                contrato=contrato,
                numero_poliza=numero_poliza,
                defaults={
                    'tipo': req.tipo,
                    'valor_asegurado': req.valor_asegurado_requerido,
                    'fecha_inicio_vigencia': fecha_inicio,
                    'fecha_vencimiento': fecha_vencimiento,
                    'estado_aportado': estado_aportado,
                    'aseguradora': random.choice(aseguradoras),
                    'cobertura': f'Cobertura {req.tipo}',
                    'condiciones': f'Condiciones estándar para {req.tipo}',
                    'garantias': f'Garantías según póliza {req.tipo}'
                }
            )
            
            if created:

def crear_otrosi(contratos):
    """Crea otrosí (modificaciones) para cada contrato"""
    tipos_otrosi = ['CANON_CHANGE', 'IPC_UPDATE', 'PLAZO_EXTENSION', 'POLIZAS_UPDATE', 'AMENDMENT']
    estados_otrosi = ['APROBADO', 'APROBADO', 'EN_REVISION', 'BORRADOR']  # Más aprobados que otros
    
    for contrato in contratos:
        # Cada contrato tiene entre 1 y 3 otrosí
        num_otrosi = random.randint(1, 3)
        
        for i in range(num_otrosi):
            tipo = random.choice(tipos_otrosi)
            estado = random.choice(estados_otrosi)
            
            # Fecha del otrosí (después del inicio del contrato)
            dias_desde_inicio = random.randint(30, (date.today() - contrato.fecha_inicial_contrato).days if (date.today() - contrato.fecha_inicial_contrato).days > 30 else 60)
            fecha_otrosi = contrato.fecha_inicial_contrato + timedelta(days=dias_desde_inicio)
            effective_from = fecha_otrosi + timedelta(days=random.randint(0, 30))
            
            # Campos según tipo
            nuevo_valor_canon = None
            nuevo_canon_minimo = None
            nuevo_porcentaje = None
            nueva_fecha_final = None
            nuevo_plazo = None
            nuevos_puntos_ipc = None
            
            if tipo == 'CANON_CHANGE':
                if contrato.modalidad_pago == 'Fijo':
                    nuevo_valor_canon = contrato.valor_canon_fijo * Decimal('1.1') if contrato.valor_canon_fijo else None
                elif contrato.modalidad_pago == 'Hibrido (Min Garantizado)':
                    nuevo_canon_minimo = contrato.canon_minimo_garantizado * Decimal('1.1') if contrato.canon_minimo_garantizado else None
                    nuevo_porcentaje = contrato.porcentaje_ventas * Decimal('1.05') if contrato.porcentaje_ventas else None
            elif tipo == 'IPC_UPDATE':
                nuevos_puntos_ipc = contrato.puntos_adicionales_ipc + Decimal('0.5') if contrato.puntos_adicionales_ipc else Decimal('2.0')
            elif tipo == 'PLAZO_EXTENSION':
                nuevo_plazo = random.randint(3, 12)
                nueva_fecha_final = contrato.fecha_final_actualizada + timedelta(days=nuevo_plazo * 30) if contrato.fecha_final_actualizada else None
            
            otrosi, created = OtroSi.objects.get_or_create(
                contrato=contrato,
                numero_otrosi=f'{contrato.num_contrato}-OS-{i+1}',
                defaults={
                    'tipo': tipo,
                    'estado': estado,
                    'fecha_otrosi': fecha_otrosi,
                    'effective_from': effective_from,
                    'nuevo_valor_canon': nuevo_valor_canon,
                    'nuevo_canon_minimo_garantizado': nuevo_canon_minimo,
                    'nuevo_porcentaje_ventas': nuevo_porcentaje,
                    'nueva_fecha_final_actualizada': nueva_fecha_final,
                    'nuevo_plazo_meses': nuevo_plazo,
                    'nuevos_puntos_adicionales_ipc': nuevos_puntos_ipc,
                    'descripcion': f'Modificación {tipo.lower().replace("_", " ")} para el contrato',
                    'clausulas_modificadas': f'Cláusulas relacionadas con {tipo}',
                    'justificacion_legal': 'Modificación justificada según necesidades del negocio',
                    'observaciones': 'Aplicable según términos acordados',
                    'creado_por': 'Sistema de Gestión',
                    'fecha_aprobacion': effective_from + timedelta(days=5) if estado == 'APROBADO' else None,
                    'aprobado_por': 'María González Pérez' if estado == 'APROBADO' else None
                }
            )
            
            if created:

def crear_informes_ventas(contratos):
    """Crea informes de ventas para contratos que reportan ventas"""
    contratos_con_ventas = [c for c in contratos if c.reporta_ventas]
    
    año_actual = date.today().year
    mes_actual = date.today().month
    
    for contrato in contratos_con_ventas:
        # Crear informes para los últimos 6 meses
        for offset_mes in range(6, 0, -1):
            mes = mes_actual - offset_mes
            año = año_actual
            
            if mes <= 0:
                mes += 12
                año -= 1
            
            # Verificar que el mes esté dentro de la vigencia del contrato
            fecha_mes = date(año, mes, 1)
            if fecha_mes < contrato.fecha_inicial_contrato:
                continue
            
            if contrato.fecha_final_actualizada and fecha_mes > contrato.fecha_final_actualizada:
                continue
            
            # Determinar estado (algunos entregados, otros pendientes)
            estado = random.choice(['ENTREGADO', 'ENTREGADO', 'PENDIENTE'])
            fecha_entrega = None
            fecha_limite = date(año, mes, contrato.dia_limite_reporte_ventas or 10)
            
            if estado == 'ENTREGADO':
                fecha_entrega = fecha_limite + timedelta(days=random.randint(0, 5))
            
            informe, created = InformeVentas.objects.get_or_create(
                contrato=contrato,
                mes=mes,
                año=año,
                defaults={
                    'estado': estado,
                    'fecha_entrega': fecha_entrega,
                    'fecha_limite': fecha_limite,
                    'observaciones': f'Informe de ventas para {mes}/{año}',
                    'registrado_por': 'Sistema de Gestión'
                }
            )
            
            if created:

def crear_calculos_facturacion(contratos):
    """Crea cálculos de facturación para informes entregados"""
    informes_entregados = InformeVentas.objects.filter(estado='ENTREGADO')
    
    for informe in informes_entregados:
        contrato = informe.contrato
        
        # Solo crear cálculo si no existe ya
        if CalculoFacturacionVentas.objects.filter(contrato=contrato, mes=informe.mes, año=informe.año).exists():
            continue
        
        # Generar ventas realistas
        if contrato.modalidad_pago == 'Variable Puro':
            ventas_totales = Decimal(random.randint(50000000, 200000000))
        elif contrato.modalidad_pago == 'Hibrido (Min Garantizado)':
            # Ventas que puedan superar el mínimo garantizado
            if contrato.canon_minimo_garantizado:
                ventas_minimas = (contrato.canon_minimo_garantizado / (contrato.porcentaje_ventas / Decimal('100'))) if contrato.porcentaje_ventas else Decimal('50000000')
                ventas_totales = ventas_minimas * Decimal(random.uniform(1.0, 2.5))
            else:
                ventas_totales = Decimal(random.randint(50000000, 200000000))
        else:
            continue  # No calcular para modalidad Fijo
        
        devoluciones = ventas_totales * Decimal(random.uniform(0.01, 0.05))
        base_neta = ventas_totales - devoluciones
        
        # Obtener valores vigentes usando la función del sistema
        valores_vigentes = obtener_valores_vigentes_facturacion_ventas(contrato, informe.mes, informe.año)
        
        if not valores_vigentes:
            continue  # No se puede calcular para este mes
        
        porcentaje = valores_vigentes['porcentaje_ventas']
        modalidad = valores_vigentes['modalidad']
        valor_calculado = base_neta * (porcentaje / Decimal('100'))
        
        # Determinar modalidad de cálculo
        if modalidad == 'Variable Puro':
            modalidad_calculo = 'VARIABLE_PURO'
            valor_a_facturar = valor_calculado
            excedente = None
            aplica_variable = True
        else:  # Híbrido
            modalidad_calculo = 'HIBRIDO_MIN_GARANTIZADO'
            canon_minimo = valores_vigentes.get('canon_minimo_garantizado') or Decimal('0')
            if valor_calculado <= canon_minimo:
                valor_a_facturar = Decimal('0')
                excedente = None
                aplica_variable = False
            else:
                excedente = valor_calculado - canon_minimo
                valor_a_facturar = excedente
                aplica_variable = True
        
        calculo, created = CalculoFacturacionVentas.objects.get_or_create(
            contrato=contrato,
            mes=informe.mes,
            año=informe.año,
            defaults={
                'informe_ventas': informe,
                'ventas_totales': ventas_totales,
                'devoluciones': devoluciones,
                'base_neta': base_neta,
                'modalidad_contrato': modalidad_calculo,
                'porcentaje_ventas_vigente': porcentaje,
                'canon_minimo_garantizado_vigente': valores_vigentes.get('canon_minimo_garantizado'),
                'canon_fijo_vigente': valores_vigentes.get('canon_fijo'),
                'otrosi_referencia': valores_vigentes.get('otrosi_referencia'),
                'valor_calculado_porcentaje': valor_calculado,
                'valor_a_facturar_variable': valor_a_facturar,
                'excedente_sobre_minimo': excedente,
                'aplica_variable': aplica_variable,
                'observaciones': f'Cálculo generado automáticamente para {informe.get_mes_display()}/{informe.año}',
                'calculado_por': 'Sistema de Gestión'
            }
        )
        
        if created:

def main():
    """Función principal para ejecutar la simulación"""
    try:
        # Crear configuracion de empresa
        empresa = crear_configuracion_empresa()
        
        # Crear arrendatarios
        arrendatarios = crear_arrendatarios()
        
        # Crear locales
        locales = crear_locales()
        
        # Crear contratos
        contratos = crear_contratos(arrendatarios, locales)
        
        # Crear requerimientos de pólizas
        crear_requerimientos_polizas(contratos)
        
        # Crear pólizas
        crear_polizas(contratos)
        
        # Crear Otrosi
        crear_otrosi(contratos)
        
        # Crear informes de ventas
        crear_informes_ventas(contratos)
        
        # Crear cálculos de facturación
        crear_calculos_facturacion(contratos)
        
    except Exception as e:
        import traceback
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
