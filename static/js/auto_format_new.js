/**
 * Formateo automático nuevo - DESACTIVADO EN MODO EDICIÓN
 * Solo se aplica en modo creación de nuevo contrato
 */

document.addEventListener('DOMContentLoaded', function() {
    // Verificar si estamos en modo edición
    const titulo = document.querySelector('h3');
    const isEditMode = titulo && titulo.textContent.includes('Editar');
    
    if (isEditMode) {
        return;
    }
    
    // Esperar para que todos los elementos estén listos (SOLO EN MODO CREACIÓN)
    setTimeout(function() {
        // Inicializar formateo para campos monetarios
        if (typeof initMoneyFormatter === 'function') {
            initMoneyFormatter('.money-input');
        }
        
        // Inicializar formateo para campos de porcentaje
        if (typeof initPercentageFormatter === 'function') {
            initPercentageFormatter('.percentage-input');
        }
    }, 200);
});
