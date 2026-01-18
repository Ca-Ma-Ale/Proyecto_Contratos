/**
 * Formateo para vistas de solo lectura (detalle/resumen)
 * Formatea valores con las clases:
 * - .formato-moneda: Aplica separador de miles (ej: 25000000 → 25.000.000)
 * - .formato-porcentaje: Ya tiene el símbolo %, solo verifica formato
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configuración del formateador para Colombia
    const formatter = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });

    /**
     * Formatea elementos con clase .formato-moneda
     */
    function formatearValoresMonetarios() {
        const elementosMonetarios = document.querySelectorAll('.formato-moneda');
        
        elementosMonetarios.forEach(function(elemento) {
            const valorOriginal = elemento.textContent.trim();
            
            if (!valorOriginal || valorOriginal === '') {
                return;
            }
            
            // Si ya tiene formato de miles, saltar
            if (valorOriginal.match(/^\d{1,3}(\.\d{3})+$/)) {
                return;
            }
            
            // Extraer solo dígitos (en caso de que tenga decimales o comas)
            let valorLimpio = valorOriginal.replace(/[^\d]/g, '');
            
            if (!valorLimpio || valorLimpio === '0') {
                return;
            }
            
            // Convertir a número
            let valorNumerico = parseInt(valorLimpio, 10);
            
            if (!isNaN(valorNumerico) && valorNumerico > 0) {
                let valorFormateado = formatter.format(valorNumerico);
                elemento.textContent = valorFormateado;
            }
        });
    }

    /**
     * Formatea elementos con clase .formato-porcentaje
     */
    function formatearValoresPorcentaje() {
        const elementosPorcentaje = document.querySelectorAll('.formato-porcentaje');
        
        elementosPorcentaje.forEach(function(elemento) {
            const valorOriginal = elemento.textContent.trim();
            
            if (!valorOriginal || valorOriginal === '') {
                return;
            }
            
            // Si ya tiene formato correcto, saltar
            if (valorOriginal.match(/^\d+(\.\d+)?$/)) {
                return;
            }
            
            // Extraer número (puede tener decimales con coma o punto)
            // Primero convertir coma a punto para normalizar
            let valorNormalizado = valorOriginal.replace(',', '.');
            // Luego extraer solo dígitos y punto decimal
            let valorLimpio = valorNormalizado.replace(/[^\d.]/g, '');
            let valorNumerico = parseFloat(valorLimpio);
            
            if (!isNaN(valorNumerico)) {
                // Si es entero, mostrar sin decimales
                let valorFormateado;
                if (valorNumerico % 1 === 0) {
                    valorFormateado = Math.round(valorNumerico).toString();
                } else {
                    valorFormateado = valorNumerico.toString();
                }
                elemento.textContent = valorFormateado;
            }
        });
    }

    // Ejecutar formateo después de un pequeño delay para asegurar que el DOM esté completamente cargado
    setTimeout(function() {
        formatearValoresMonetarios();
        formatearValoresPorcentaje();
    }, 100);
});

