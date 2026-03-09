/**
 * Utilidades JavaScript para cálculos de fechas uniformes
 * Este archivo centraliza los cálculos de fechas para mantener consistencia en todo el sistema
 */

/**
 * Parsea una fecha YYYY-MM-DD en hora local (evita desfases por UTC)
 * @param {string} str - Fecha en formato YYYY-MM-DD
 * @returns {Date} Fecha en hora local
 */
function parseFechaLocal(str) {
    if (!str) return null;
    const parts = String(str).trim().split('-');
    if (parts.length !== 3) return new Date(str);
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    return new Date(year, month, day);
}

/**
 * Calcula fecha de vencimiento usando meses calendario reales.
 * Regla: inicio 01/01/2025 + 12 meses = 31/12/2025 | inicio 23/07/2025 + 12 meses = 22/07/2026
 * @param {Date|string} fechaInicio - Fecha de inicio (Date o YYYY-MM-DD)
 * @param {number} meses - Número de meses de vigencia
 * @returns {Date} Fecha de vencimiento calculada (último día del período)
 */
function calcularFechaVencimiento(fechaInicio, meses) {
    const fecha = typeof fechaInicio === 'string' ? parseFechaLocal(fechaInicio) : new Date(fechaInicio.getTime());
    if (!fecha || isNaN(fecha.getTime())) return null;
    const fechaFin = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
    fechaFin.setMonth(fechaFin.getMonth() + meses);
    fechaFin.setDate(fechaFin.getDate() - 1);
    return fechaFin;
}

/**
 * Calcula el número de meses entre dos fechas usando meses calendario reales
 * @param {Date} fechaInicio - Fecha de inicio
 * @param {Date} fechaFin - Fecha de fin
 * @returns {number} Número de meses
 */
function calcularMesesVigencia(fechaInicio, fechaFin) {
    const diffTime = fechaFin - fechaInicio;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    // Usar 30 días por mes como estándar para cálculos inversos
    return Math.round(diffDays / 30);
}

/**
 * Formatea una fecha para input de tipo date (YYYY-MM-DD) usando componentes locales
 * @param {Date} fecha - Fecha a formatear
 * @returns {string} Fecha formateada
 */
function formatearFechaInput(fecha) {
    if (!fecha || isNaN(fecha.getTime())) return '';
    const y = fecha.getFullYear();
    const m = String(fecha.getMonth() + 1).padStart(2, '0');
    const d = String(fecha.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

/**
 * Valida si una fecha de vencimiento cumple con los meses requeridos
 * @param {Date} fechaInicio - Fecha de inicio de la vigencia
 * @param {Date} fechaVencimiento - Fecha de vencimiento a validar
 * @param {number} mesesRequeridos - Número de meses requeridos
 * @returns {object} Objeto con 'cumple' (boolean) y 'observaciones' (array)
 */
function validarFechaVencimientoPoliza(fechaInicio, fechaVencimiento, mesesRequeridos) {
    const fechaEsperada = calcularFechaVencimiento(fechaInicio, mesesRequeridos);
    if (!fechaEsperada) return { cumple: false, observaciones: ['Error al calcular fecha esperada'] };
    const cumple = fechaVencimiento >= fechaEsperada;
    
    const observaciones = [];
    if (!cumple) {
        observaciones.push(
            `Vigencia insuficiente. Requerida hasta: ${formatearFechaInput(fechaEsperada)}, ` +
            `Actual: ${formatearFechaInput(fechaVencimiento)}`
        );
    }
    
    return {
        cumple: cumple,
        observaciones: observaciones
    };
}

/**
 * Configura el cálculo automático de fechas para un formulario de contrato
 * @param {string} fechaInicialId - ID del campo de fecha inicial del contrato
 * @param {string} duracionId - ID del campo de duración en meses
 * @param {string} fechaFinalId - ID del campo de fecha final
 */
function configurarCalculoFechaFinalContrato(fechaInicialId, duracionId, fechaFinalId) {
    const fechaInicial = document.getElementById(fechaInicialId);
    const duracion = document.getElementById(duracionId);
    const fechaFinal = document.getElementById(fechaFinalId);
    
    if (!fechaInicial || !duracion || !fechaFinal) {
        console.warn('No se pudieron encontrar todos los elementos para el cálculo de fecha final del contrato');
        return;
    }
    
    function calcularFechaFinal() {
        if (fechaInicial.value && duracion.value) {
            const meses = parseInt(String(duracion.value).replace(/[^\d]/g, ''), 10);
            if (!isNaN(meses) && meses > 0) {
                const fechaFin = calcularFechaVencimiento(fechaInicial.value, meses);
                if (fechaFin) fechaFinal.value = formatearFechaInput(fechaFin);
            }
        }
    }
    
    // Configurar eventos
    fechaInicial.addEventListener('change', calcularFechaFinal);
    duracion.addEventListener('input', calcularFechaFinal);
    duracion.addEventListener('change', calcularFechaFinal);
    
    // Ejecutar cálculo inicial si hay datos (y tras breve delay por si el DOM se actualiza)
    function ejecutarInicial() {
        if (fechaInicial.value && duracion.value) {
            calcularFechaFinal();
        }
    }
    ejecutarInicial();
    setTimeout(ejecutarInicial, 100);
}

/**
 * Configura el cálculo automático de fechas para un formulario de póliza
 * @param {string} fechaInicioId - ID del campo de fecha de inicio
 * @param {string} mesesId - ID del campo de meses
 * @param {string} fechaVencimientoId - ID del campo de fecha de vencimiento
 */
function configurarCalculoFechasPoliza(fechaInicioId, mesesId, fechaVencimientoId) {
    const fechaInicio = document.getElementById(fechaInicioId);
    const meses = document.getElementById(mesesId);
    const fechaVencimiento = document.getElementById(fechaVencimientoId);
    
    if (!fechaInicio || !meses || !fechaVencimiento) {
        console.warn('No se pudieron encontrar todos los elementos para el cálculo de fechas');
        return;
    }
    
    function calcularFechaVencimientoHandler() {
        if (fechaInicio.value && meses.value) {
            const mesesNum = parseInt(meses.value);
            const fechaFin = calcularFechaVencimiento(fechaInicio.value, mesesNum);
            if (fechaFin) fechaVencimiento.value = formatearFechaInput(fechaFin);
        }
    }
    
    function calcularMesesDesdeFechas() {
        if (fechaInicio.value && fechaVencimiento.value) {
            const fechaInicioDate = parseFechaLocal(fechaInicio.value);
            const fechaFinDate = parseFechaLocal(fechaVencimiento.value);
            if (!fechaInicioDate || !fechaFinDate || isNaN(fechaInicioDate.getTime()) || isNaN(fechaFinDate.getTime())) return;
            const mesesCalculados = calcularMesesVigencia(fechaInicioDate, fechaFinDate);
            if (mesesCalculados > 0) {
                meses.value = mesesCalculados;
            }
        }
    }
    
    // Configurar eventos
    fechaInicio.addEventListener('change', calcularFechaVencimientoHandler);
    meses.addEventListener('input', calcularFechaVencimientoHandler);
    fechaVencimiento.addEventListener('change', calcularMesesDesdeFechas);
    
    // Ejecutar cálculo inicial si hay datos
    if (fechaInicio.value && meses.value) {
        calcularFechaVencimientoHandler();
    }
}

/**
 * Configura el cálculo automático de fechas para todas las pólizas de un contrato
 * @param {string} fechaInicialContratoId - ID del campo de fecha inicial del contrato
 */
function configurarCalculoFechasPolizasContrato(fechaInicialContratoId) {
    const fechaInicialContrato = document.getElementById(fechaInicialContratoId);
    
    if (!fechaInicialContrato) {
        console.warn('No se pudo encontrar el campo de fecha inicial del contrato');
        return;
    }
    
    // Configurar cálculo automático para cada tipo de póliza
    const configuracionesPolizas = [
        {
            mesesId: 'id_meses_vigencia_rce',
            fechaInicioId: 'id_fecha_inicio_vigencia_rce',
            fechaFinId: 'id_fecha_fin_vigencia_rce',
            nombre: 'RCE'
        },
        {
            mesesId: 'id_meses_vigencia_cumplimiento',
            fechaInicioId: 'id_fecha_inicio_vigencia_cumplimiento',
            fechaFinId: 'id_fecha_fin_vigencia_cumplimiento',
            nombre: 'Cumplimiento'
        },
        {
            mesesId: 'id_meses_vigencia_arrendamiento',
            fechaInicioId: 'id_fecha_inicio_vigencia_arrendamiento',
            fechaFinId: 'id_fecha_fin_vigencia_arrendamiento',
            nombre: 'Póliza de Arrendamiento'
        },
        {
            mesesId: 'id_meses_vigencia_todo_riesgo',
            fechaInicioId: 'id_fecha_inicio_vigencia_todo_riesgo',
            fechaFinId: 'id_fecha_fin_vigencia_todo_riesgo',
            nombre: 'Todo Riesgo'
        },
        {
            mesesId: 'id_meses_vigencia_otra_1',
            fechaInicioId: 'id_fecha_inicio_vigencia_otra_1',
            fechaFinId: 'id_fecha_fin_vigencia_otra_1',
            nombre: 'Otra Póliza'
        }
    ];
    
    configuracionesPolizas.forEach(config => {
        const meses = document.getElementById(config.mesesId);
        const fechaInicio = document.getElementById(config.fechaInicioId);
        const fechaFin = document.getElementById(config.fechaFinId);
        
        if (meses && fechaInicio && fechaFin) {
            function calcularFechasPoliza() {
                if (fechaInicialContrato.value && meses.value) {
                    fechaInicio.value = fechaInicialContrato.value;
                    const fechaFinDate = calcularFechaVencimiento(fechaInicialContrato.value, parseInt(meses.value));
                    if (fechaFinDate) fechaFin.value = formatearFechaInput(fechaFinDate);
                }
            }
            
            // Configurar eventos
            meses.addEventListener('input', calcularFechasPoliza);
            fechaInicialContrato.addEventListener('change', calcularFechasPoliza);
            
            // Ejecutar cálculo inicial si hay datos
            if (fechaInicialContrato.value && meses.value) {
                calcularFechasPoliza();
            }
        }
    });
}
