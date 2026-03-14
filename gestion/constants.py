"""
Constantes para el sistema de validación de efecto cadena.

Define:
  - CAMPOS_BLOQUEABLES_CONTRATO   : campos del Contrato que pueden quedar bloqueados
  - CAMPOS_BLOQUEABLES_OTROSI     : campos del OtroSí que pueden quedar bloqueados
  - MAPA_OTROSI_A_CONTRATO        : equivalencia campo OtroSí → campo Contrato
  - LABELS_CAMPOS                 : etiquetas legibles de cada campo
  - CAMPOS_POLIZAS_OTROSI         : campos de pólizas dentro del OtroSí
"""

# ── Campos del Contrato Base que pueden ser bloqueados ────────────────────────
# Son exactamente los que OtroSí puede modificar + los que tocan cálculos.
CAMPOS_BLOQUEABLES_CONTRATO = [
    'valor_canon_fijo',
    'modalidad_pago',
    'canon_minimo_garantizado',
    'porcentaje_ventas',
    'fecha_final_actualizada',
    'duracion_inicial_meses',
    'prorroga_automatica',
    'tipo_condicion_ipc',
    'puntos_adicionales_ipc',
    'periodicidad_ipc',
    'fecha_aumento_ipc',
    'porcentaje_salario_minimo',
    # Requerimientos de pólizas
    'exige_poliza_rce',
    'valor_asegurado_rce',
    'valor_propietario_locatario_ocupante_rce',
    'valor_patronal_rce',
    'valor_gastos_medicos_rce',
    'valor_vehiculos_rce',
    'valor_contratistas_rce',
    'valor_perjuicios_extrapatrimoniales_rce',
    'valor_dano_moral_rce',
    'valor_lucro_cesante_rce',
    'meses_vigencia_rce',
    'exige_poliza_cumplimiento',
    'valor_asegurado_cumplimiento',
    'valor_remuneraciones_cumplimiento',
    'valor_servicios_publicos_cumplimiento',
    'valor_iva_cumplimiento',
    'valor_otros_cumplimiento',
    'meses_vigencia_cumplimiento',
    'exige_poliza_arrendamiento',
    'valor_asegurado_arrendamiento',
    'valor_remuneraciones_arrendamiento',
    'valor_servicios_publicos_arrendamiento',
    'valor_iva_arrendamiento',
    'valor_otros_arrendamiento',
    'meses_vigencia_arrendamiento',
    'exige_poliza_todo_riesgo',
    'valor_asegurado_todo_riesgo',
    'meses_vigencia_todo_riesgo',
    'exige_poliza_otra_1',
    'nombre_poliza_otra_1',
    'valor_asegurado_otra_1',
    'meses_vigencia_otra_1',
]

# ── Campos del OtroSí que pueden ser bloqueados por un OtroSí posterior ───────
CAMPOS_BLOQUEABLES_OTROSI = [
    'nuevo_valor_canon',
    'nueva_modalidad_pago',
    'nuevo_canon_minimo_garantizado',
    'nuevo_porcentaje_ventas',
    'nueva_fecha_final_actualizada',
    'nuevo_plazo_meses',
    'nuevo_tipo_condicion_ipc',
    'nuevos_puntos_adicionales_ipc',
    'nueva_periodicidad_ipc',
    'nueva_fecha_aumento_ipc',
    'modifica_polizas',
    'nueva_prorroga_automatica',
    'nueva_duracion_renovacion_meses',
]

# ── Mapa: campo en OtroSí → campo equivalente en Contrato Base ───────────────
MAPA_OTROSI_A_CONTRATO = {
    'nuevo_valor_canon':               'valor_canon_fijo',
    'nueva_modalidad_pago':            'modalidad_pago',
    'nuevo_canon_minimo_garantizado':  'canon_minimo_garantizado',
    'nuevo_porcentaje_ventas':         'porcentaje_ventas',
    'nueva_fecha_final_actualizada':   'fecha_final_actualizada',
    'nuevo_plazo_meses':               'duracion_inicial_meses',
    'nuevo_tipo_condicion_ipc':        'tipo_condicion_ipc',
    'nuevos_puntos_adicionales_ipc':   'puntos_adicionales_ipc',
    'nueva_periodicidad_ipc':          'periodicidad_ipc',
    'nueva_fecha_aumento_ipc':         'fecha_aumento_ipc',
    'nueva_prorroga_automatica':       'prorroga_automatica',
    'nueva_duracion_renovacion_meses': 'duracion_inicial_meses',
    # modifica_polizas bloquea todos los campos de pólizas del contrato
}

# Campos de pólizas del Contrato que quedan bloqueados cuando
# un OtroSí tiene modifica_polizas=True
CAMPOS_POLIZAS_CONTRATO = [
    'exige_poliza_rce', 'valor_asegurado_rce', 'valor_propietario_locatario_ocupante_rce',
    'valor_patronal_rce', 'valor_gastos_medicos_rce', 'valor_vehiculos_rce',
    'valor_contratistas_rce', 'valor_perjuicios_extrapatrimoniales_rce',
    'valor_dano_moral_rce', 'valor_lucro_cesante_rce', 'meses_vigencia_rce',
    'exige_poliza_cumplimiento', 'valor_asegurado_cumplimiento',
    'valor_remuneraciones_cumplimiento', 'valor_servicios_publicos_cumplimiento',
    'valor_iva_cumplimiento', 'valor_otros_cumplimiento', 'meses_vigencia_cumplimiento',
    'exige_poliza_arrendamiento', 'valor_asegurado_arrendamiento',
    'valor_remuneraciones_arrendamiento', 'valor_servicios_publicos_arrendamiento',
    'valor_iva_arrendamiento', 'valor_otros_arrendamiento', 'meses_vigencia_arrendamiento',
    'exige_poliza_todo_riesgo', 'valor_asegurado_todo_riesgo', 'meses_vigencia_todo_riesgo',
    'exige_poliza_otra_1', 'nombre_poliza_otra_1', 'valor_asegurado_otra_1',
    'meses_vigencia_otra_1',
]

# ── Campos bloqueados por Cálculo IPC/SMLV en el Contrato ────────────────────
CAMPOS_BLOQUEADOS_POR_CALCULO_IPC = ['valor_canon_fijo', 'puntos_adicionales_ipc']
CAMPOS_BLOQUEADOS_POR_CALCULO_SMLV = ['valor_canon_fijo', 'porcentaje_salario_minimo']

# ── Campos bloqueados por Cálculo de Facturación CONFIRMADO ──────────────────
CAMPOS_BLOQUEADOS_POR_CALCULO_VENTAS = ['porcentaje_ventas', 'canon_minimo_garantizado']

# ── Campos bloqueados en Contrato por Renovación Automática ──────────────────
CAMPOS_BLOQUEADOS_POR_RENOVACION = ['fecha_final_actualizada']

# ── Campos del OtroSí bloqueados por CalculoIPC posterior ────────────────────
CAMPOS_OTROSI_BLOQUEADOS_POR_CALCULO_IPC = ['nuevo_valor_canon', 'nuevos_puntos_adicionales_ipc']

# ── Campos relacionados: si un campo se bloquea, estos también ────────────────
# Cuando un campo del contrato queda bloqueado, los campos que dependen de él
# o forman parte del mismo grupo lógico también deben bloquearse.
CAMPOS_RELACIONADOS_CONTRATO = {
    'valor_canon_fijo': ['canon_minimo_garantizado'],
    'canon_minimo_garantizado': ['valor_canon_fijo'],
    'modalidad_pago': ['valor_canon_fijo', 'canon_minimo_garantizado', 'porcentaje_ventas'],
    'duracion_inicial_meses': ['fecha_inicial_contrato', 'fecha_final_inicial'],
    'fecha_final_actualizada': ['fecha_final_inicial'],
    'tipo_condicion_ipc': ['puntos_adicionales_ipc', 'periodicidad_ipc', 'fecha_aumento_ipc'],
    'periodicidad_ipc': ['fecha_aumento_ipc'],
    'porcentaje_ventas': ['canon_minimo_garantizado'],
}

# ── Etiquetas legibles de cada campo ─────────────────────────────────────────
LABELS_CAMPOS = {
    # Contrato
    'valor_canon_fijo':                         'Valor Canon Fijo',
    'modalidad_pago':                           'Modalidad de Pago',
    'canon_minimo_garantizado':                 'Canon Mínimo Garantizado',
    'porcentaje_ventas':                        'Porcentaje de Ventas (%)',
    'fecha_final_actualizada':                  'Fecha Final Actualizada',
    'duracion_inicial_meses':                   'Duración Inicial (meses)',
    'tipo_condicion_ipc':                       'Tipo Condición IPC',
    'puntos_adicionales_ipc':                   'Puntos Adicionales IPC',
    'periodicidad_ipc':                         'Periodicidad IPC',
    'fecha_aumento_ipc':                        'Fecha de Aumento IPC',
    'porcentaje_salario_minimo':                'Porcentaje Salario Mínimo (%)',
    'exige_poliza_rce':                         'Exige Póliza RCE',
    'valor_asegurado_rce':                      'Valor Asegurado RCE',
    'exige_poliza_cumplimiento':                'Exige Póliza Cumplimiento',
    'valor_asegurado_cumplimiento':             'Valor Asegurado Cumplimiento',
    'exige_poliza_arrendamiento':               'Exige Póliza Arrendamiento',
    'valor_asegurado_arrendamiento':            'Valor Asegurado Arrendamiento',
    'exige_poliza_todo_riesgo':                 'Exige Póliza Todo Riesgo',
    'valor_asegurado_todo_riesgo':              'Valor Asegurado Todo Riesgo',
    'exige_poliza_otra_1':                      'Exige Otra Póliza',
    'nombre_poliza_otra_1':                     'Nombre Otra Póliza',
    # Contrato — prórroga
    'prorroga_automatica':                      'Prórroga Automática',
    # OtroSí
    'nuevo_valor_canon':                        'Nuevo Valor Canon',
    'nueva_modalidad_pago':                     'Nueva Modalidad de Pago',
    'nuevo_canon_minimo_garantizado':           'Nuevo Canon Mínimo Garantizado',
    'nuevo_porcentaje_ventas':                  'Nuevo Porcentaje de Ventas (%)',
    'nueva_fecha_final_actualizada':            'Nueva Fecha Final',
    'nuevo_plazo_meses':                        'Nuevo Plazo (meses)',
    'nuevo_tipo_condicion_ipc':                 'Nuevo Tipo Condición IPC',
    'nuevos_puntos_adicionales_ipc':            'Nuevos Puntos Adicionales IPC',
    'nueva_periodicidad_ipc':                   'Nueva Periodicidad IPC',
    'nueva_fecha_aumento_ipc':                  'Nueva Fecha Aumento IPC',
    'modifica_polizas':                         'Modifica Pólizas',
    'nueva_prorroga_automatica':                'Nueva Prórroga Automática',
    'nueva_duracion_renovacion_meses':          'Nueva Duración de Renovación (Meses)',
}
