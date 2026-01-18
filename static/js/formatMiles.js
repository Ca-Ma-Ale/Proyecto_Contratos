/**
 * Formateo de miles en tiempo real - Solución robusta
 * Basado en la implementación proporcionada por el usuario
 */

(function (global) {
    'use strict';

    // Configuración del formateador
    const formatter = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });

    // Función para extraer solo dígitos
    function onlyDigits(str) {
        return str.replace(/\D/g, '');
    }

    // Función para normalizar número con coma decimal a formato estándar
    function normalizarNumeroDecimal(str) {
        if (!str || typeof str !== 'string') {
            return str;
        }
        // Remover símbolo % si existe
        str = str.replace(/%/g, '').trim();
        // Convertir coma decimal a punto
        str = str.replace(',', '.');
        return str;
    }

    // Función para extraer número de porcentaje permitiendo comas y puntos decimales
    function extraerNumeroPorcentaje(str) {
        if (!str || typeof str !== 'string') {
            return '';
        }
        // Remover símbolo % si existe
        str = str.replace(/%/g, '').trim();
        
        // Remover espacios
        str = str.replace(/\s/g, '');
        
        // Detectar si tiene coma o punto decimal
        // Si tiene ambos, priorizar el último (más reciente)
        let tieneComa = str.includes(',');
        let tienePunto = str.includes('.');
        
        if (tieneComa && tienePunto) {
            // Si tiene ambos, usar el último como separador decimal
            let ultimaComa = str.lastIndexOf(',');
            let ultimoPunto = str.lastIndexOf('.');
            if (ultimaComa > ultimoPunto) {
                // La coma es más reciente, convertir todos los puntos a nada y coma a punto
                str = str.replace(/\./g, '');
                str = str.replace(',', '.');
            } else {
                // El punto es más reciente, convertir todas las comas a nada
                str = str.replace(/,/g, '');
            }
        } else if (tieneComa) {
            // Solo tiene coma, convertirla a punto
            str = str.replace(',', '.');
        }
        // Si solo tiene punto, mantenerlo
        
        // Remover todo excepto dígitos y un punto decimal
        let resultado = '';
        let puntoEncontrado = false;
        for (let i = 0; i < str.length; i++) {
            const char = str[i];
            if (char >= '0' && char <= '9') {
                resultado += char;
            } else if (char === '.' && !puntoEncontrado) {
                resultado += '.';
                puntoEncontrado = true;
            }
        }
        return resultado;
    }

    // Función para formatear en tiempo real
    function formatLive(input) {
        // Verificar si ya tiene listeners para evitar duplicados
        if (input.dataset.formatLiveInitialized) {
            return;
        }
        
        // Marcar como inicializado
        input.dataset.formatLiveInitialized = 'true';
        
        // Cambiar el tipo a text para permitir formateo
        const originalType = input.type;
        input.type = 'text';
        
        // Formatear valor inicial si existe (solo si NO está ya formateado)
        if (input.value && input.value.trim() !== '') {
            let valorOriginal = input.value.trim();
            
            // Si el valor ya tiene formato de miles, no reformatear
            if (valorOriginal.includes('.') && valorOriginal.match(/^\d{1,3}(\.\d{3})*$/)) {
                // NO hacer return aquí, continuar para agregar event listeners
            } else {
                // SOLUCIÓN AL BUG: Manejar valores con decimales de Django (ej: "2500000.00")
                // parseFloat correctamente convierte "2500000.00" a 2500000
                let valorNumerico = parseFloat(valorOriginal);
                
                if (!isNaN(valorNumerico) && valorNumerico > 0) {
                    valorNumerico = Math.round(valorNumerico);
                    let valorFormateado = formatter.format(valorNumerico);
                    input.value = valorFormateado;
                }
            }
        }
        
        // Agregar event listeners para formateo en tiempo real
        
        input.addEventListener('input', (e) => {
            const el = e.target;
            const start = el.selectionStart;
            const digits = onlyDigits(el.value);

            if (digits === '') {
                el.value = '';
                return;
            }

            const formatted = formatter.format(digits);
            const moveToEnd = formatted.length !== el.value.length;
            el.value = formatted;

            if (moveToEnd) {
                el.setSelectionRange(el.value.length, el.value.length);
            } else if (start != null) {
                el.setSelectionRange(start, start);
            }
        });

        input.addEventListener('blur', (e) => {
            const digits = onlyDigits(e.target.value);
            e.target.value = digits ? formatter.format(digits) : '';
        });
        
        input.addEventListener('focus', (e) => {
            // Limpiar formato al entrar para editar
            const digits = onlyDigits(e.target.value);
            if (digits) {
                e.target.value = digits;
            }
        });
    }

    // Función global para aplicar a todos los inputs con clase "miles"
    global.initMilesFormatter = function (selector = 'input.miles') {
        document.querySelectorAll(selector).forEach(formatLive);
    };

    // Función para campos monetarios
    global.initMoneyFormatter = function (selector = '.money-input') {
        document.querySelectorAll(selector).forEach(formatLive);
    };

    // Función para campos de porcentaje
    global.initPercentageFormatter = function (selector = '.percentage-input', forzarReinicializacion = false) {
        const inputs = document.querySelectorAll(selector);
        const inputsArray = Array.from(inputs);
        
        inputsArray.forEach(function(input) {
            // Si ya tiene listeners y no se fuerza reinicialización, saltar
            if (input.dataset.percentLiveInitialized && !forzarReinicializacion) {
                return;
            }
            
            // Variable para trabajar con el input (puede ser el original o el clonado)
            let inputParaUsar = input;
            
            // Si se fuerza reinicialización, remover listeners antiguos clonando el input
            if (forzarReinicializacion && input.dataset.percentLiveInitialized) {
                // Guardar el valor actual y el id/name
                const valorActual = input.value;
                const inputId = input.id;
                const inputName = input.name;
                // Clonar el input para remover todos los listeners
                const nuevoInput = input.cloneNode(true);
                nuevoInput.value = valorActual;
                nuevoInput.id = inputId;
                nuevoInput.name = inputName;
                input.parentNode.replaceChild(nuevoInput, input);
                // Usar el nuevo input
                inputParaUsar = nuevoInput;
            }
            
            // Marcar como inicializado
            inputParaUsar.dataset.percentLiveInitialized = 'true';
            
            // Cambiar el tipo a text para permitir formateo
            const originalType = inputParaUsar.type;
            inputParaUsar.type = 'text';
            
            // Formatear valor inicial si existe (solo si NO está ya formateado)
            if (inputParaUsar.value && inputParaUsar.value.trim() !== '') {
                let valorOriginal = inputParaUsar.value.trim();
                // Si el valor ya tiene símbolo %, no reformatear
                if (valorOriginal.includes('%')) {
                    // NO hacer return aquí, continuar para agregar event listeners
                } else {
                    // Normalizar número (convertir coma a punto) antes de parsear
                    let valorNormalizado = normalizarNumeroDecimal(valorOriginal);
                    let valorNumerico = parseFloat(valorNormalizado);
                    if (!isNaN(valorNumerico) && valorNumerico >= 0) {
                        // Si es entero, mostrar sin decimales
                        if (valorNumerico % 1 === 0) {
                            inputParaUsar.value = Math.round(valorNumerico) + '%';
                        } else {
                            inputParaUsar.value = valorNumerico + '%';
                        }
                    }
                }
            }
            
            // Función para validar si un carácter es permitido
            function esCaracterPermitido(char, valorActual) {
                if (!char) return true; // Permitir borrado, etc.
                
                // Permitir números, comas, puntos y símbolo %
                if (/[0-9.,%]/.test(char)) {
                    const tienePunto = valorActual.includes('.');
                    const tieneComa = valorActual.includes(',');
                    
                    // Si intenta agregar otro punto o coma cuando ya existe uno, no permitir
                    if ((char === '.' && tienePunto) || (char === ',' && tieneComa)) {
                        return false;
                    }
                    
                    return true;
                }
                
                return false;
            }
            
            // Usar beforeinput (moderno) si está disponible
            if ('onbeforeinput' in inputParaUsar) {
                inputParaUsar.addEventListener('beforeinput', (e) => {
                    const char = e.data;
                    if (!esCaracterPermitido(char, e.target.value)) {
                        e.preventDefault();
                    }
                });
            }
            
            // Fallback para navegadores antiguos: usar keypress
            inputParaUsar.addEventListener('keypress', (e) => {
                const char = String.fromCharCode(e.which || e.keyCode);
                if (!esCaracterPermitido(char, e.target.value)) {
                    e.preventDefault();
                    return false;
                }
            });
            
            // Event listener simple para input - no modificar, solo permitir escritura
            inputParaUsar.addEventListener('input', (e) => {
                // No hacer nada - dejar que el usuario escriba libremente
                // El formateo se hará en blur
            });

            inputParaUsar.addEventListener('blur', (e) => {
                let numeroStr = extraerNumeroPorcentaje(e.target.value);
                if (numeroStr === '') {
                    e.target.value = '';
                    return;
                }
                let valorNumerico = parseFloat(numeroStr);
                if (!isNaN(valorNumerico) && valorNumerico >= 0) {
                    if (valorNumerico % 1 === 0) {
                        e.target.value = Math.round(valorNumerico) + '%';
                    } else {
                        e.target.value = valorNumerico + '%';
                    }
                } else {
                    e.target.value = '';
                }
            });
            
            inputParaUsar.addEventListener('focus', (e) => {
                // Limpiar formato al entrar para editar, manteniendo el número con punto decimal
                let numeroStr = extraerNumeroPorcentaje(e.target.value);
                if (numeroStr) {
                    e.target.value = numeroStr;
                }
            });
        });
    };

    // Función para limpiar valores antes de enviar el formulario
    global.cleanFormValues = function() {
        // Limpiar campos monetarios
        document.querySelectorAll('.money-input').forEach(function(input) {
            if (input.value) {
                // Remover puntos de miles
                input.value = input.value.replace(/\./g, '');
            }
        });
        
        // Limpiar campos de porcentaje
        document.querySelectorAll('.percentage-input').forEach(function(input) {
            if (input.value) {
                // Remover símbolo % y mantener el número con punto decimal
                let numeroStr = extraerNumeroPorcentaje(input.value);
                input.value = numeroStr;
            }
        });
    };

    // Exporta si hay módulos
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { initMilesFormatter, initMoneyFormatter, initPercentageFormatter };
    }
})(this);
