/**
 * Formateo específico para vista de edición - VERSIÓN DEFINITIVA
 * Aplica separador de miles a valores cargados desde la base de datos
 * Maneja correctamente valores Decimal de Django
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configuración del formateador para Colombia
    const formatter = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });

    // Función para detectar si estamos en modo edición
    function isEditMode() {
        const titulo = document.querySelector('h3');
        return titulo && titulo.textContent.includes('Editar');
    }

    // Función para formatear valores de la base de datos
    function formatDatabaseValues() {
        if (!isEditMode()) {
            return;
        }

        // Campos monetarios
        const moneyFields = document.querySelectorAll('.money-input');
        moneyFields.forEach(function(field) {
            if (field.value && field.value.trim() !== '') {
                let valorOriginal = field.value.trim();
                
                // Si ya tiene formato de miles correcto (ej: 2.500.000), no hacer nada
                if (valorOriginal.match(/^\d{1,3}(\.\d{3})+$/)) {
                    return;
                }
                
                // SOLUCIÓN AL BUG: Primero eliminar la parte decimal si existe
                // Django renderiza Decimales como "2500000.00", que se convertía erróneamente en "250000000"
                // Ahora: "2500000.00" -> "2500000" (tomamos solo la parte entera)
                let valorSinDecimales = valorOriginal.split('.')[0];
                
                // Limpiar el valor: remover todo excepto dígitos
                // Esto maneja: "2500000", "2,500,000", etc.
                let valorLimpio = valorSinDecimales.replace(/[^\d]/g, '');
                
                // Si el valor limpio está vacío, no hacer nada
                if (!valorLimpio || valorLimpio === '0' || valorLimpio === '00') {
                    return;
                }
                
                // Convertir a número entero
                let valorNumerico = parseInt(valorLimpio, 10);
                
                if (!isNaN(valorNumerico) && valorNumerico > 0) {
                    let nuevoValor = formatter.format(valorNumerico);
                    field.value = nuevoValor;
                }
            }
        });

        // Campos de porcentaje
        const percentageFields = document.querySelectorAll('.percentage-input');
        percentageFields.forEach(function(field) {
            if (field.value && field.value.trim() !== '') {
                let valorOriginal = field.value.trim();
                
                // Si ya tiene símbolo %, no hacer nada
                if (valorOriginal.includes('%')) {
                    return;
                }
                
                // Normalizar número: convertir coma decimal a punto antes de parsear
                let valorNormalizado = valorOriginal.replace(',', '.');
                
                // Convertir a número (puede tener decimales como 12.00 o 12,5)
                let valorNumerico = parseFloat(valorNormalizado);
                
                if (!isNaN(valorNumerico)) {
                    // Si es un número entero, no mostrar decimales
                    let nuevoValor;
                    if (valorNumerico % 1 === 0) {
                        nuevoValor = Math.round(valorNumerico) + '%';
                    } else {
                        nuevoValor = valorNumerico + '%';
                    }
                    field.value = nuevoValor;
                }
            }
        });
    }

    // Aplicar formateo después de que TODOS los demás scripts hayan cargado
    // Esperar 1.5 segundos para asegurar que otros scripts no interfieran
    setTimeout(function() {
        formatDatabaseValues();
        
        // IMPORTANTE: Después de formatear los valores iniciales,
        // activar el formateo en tiempo real para la edición del usuario
        if (typeof initMoneyFormatter === 'function') {
            initMoneyFormatter('.money-input');
        }
        
        if (typeof initPercentageFormatter === 'function') {
            initPercentageFormatter('.percentage-input');
        }
    }, 1500);
});
