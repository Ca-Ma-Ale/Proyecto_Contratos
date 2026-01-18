# Mejora del Formulario de Otro Sí - Sistema de Checkboxes

## Descripción
Se implementó un sistema de checkboxes en el formulario de "otro sí" que permite al usuario seleccionar qué aspectos del contrato desea modificar, mostrando u ocultando los campos correspondientes de manera dinámica.

## Funcionalidad Implementada

### 1. Checkboxes por Categorías
- **Modificar Condiciones Financieras**: Controla la visibilidad de campos como valor de canon, modalidad de pago, canon mínimo garantizado y porcentaje de ventas.
- **Modificar Plazos y Vigencia**: Controla campos de fecha final actualizada y plazo en meses.
- **Modificar Condiciones IPC**: Controla campos de tipo de condición IPC y puntos adicionales.
- **Modificar Condiciones de Pólizas**: Controla el campo de notas sobre modificaciones de pólizas.

### 2. Comportamiento
- Los campos están ocultos por defecto (`display: none`)
- Al activar un checkbox, se muestran los campos correspondientes
- Al desactivar un checkbox, se ocultan los campos correspondientes
- El estado se mantiene durante la sesión del formulario

### 3. Estructura Visual
- Cada categoría está en una tarjeta (card) separada
- El checkbox está en el header de la tarjeta con un ícono descriptivo
- Los campos están organizados en el body de la tarjeta
- Se mantiene la consistencia visual con el resto del sistema

## Archivos Modificados

### `templates/gestion/otrosi_form.html`
- Reorganizada la estructura HTML para agrupar campos por categorías
- Agregados checkboxes para controlar la visibilidad
- Implementado JavaScript para manejar el toggle de campos
- Mantenida la funcionalidad existente de formateo y validación

## Código JavaScript Implementado

```javascript
// Configurar toggles para mostrar/ocultar campos modificables
const configuracionesToggle = [
    { checkbox: 'modificar_condiciones_financieras', detalles: 'condiciones-financieras-details' },
    { checkbox: 'modificar_plazos', detalles: 'plazos-details' },
    { checkbox: 'modificar_condiciones_ipc', detalles: 'condiciones-ipc-details' },
    { checkbox: '{{ form.modifica_polizas.id_for_label }}', detalles: 'modificacion-polizas-details' }
];

configuracionesToggle.forEach(config => {
    const checkbox = document.getElementById(config.checkbox);
    const detalles = document.getElementById(config.detalles);
    
    if (checkbox && detalles) {
        function toggleDetalles() {
            detalles.style.display = checkbox.checked ? 'block' : 'none';
        }
        
        checkbox.addEventListener('change', toggleDetalles);
        toggleDetalles(); // Estado inicial
    }
});
```

## Beneficios para el Usuario

1. **Interfaz más limpia**: Solo se muestran los campos relevantes para la modificación específica
2. **Mejor experiencia de usuario**: Evita confusión al mostrar solo las opciones necesarias
3. **Consistencia**: Funciona igual que el formulario de creación de contratos
4. **Flexibilidad**: Permite modificar cualquier combinación de aspectos del contrato

## Compatibilidad

- Mantiene toda la funcionalidad existente del formulario
- Compatible con el sistema de validación actual
- No afecta el procesamiento del formulario en el backend
- Mantiene el formateo automático de campos numéricos

## Próximos Pasos

1. Probar la funcionalidad en diferentes navegadores
2. Verificar que la validación del formulario funcione correctamente
3. Considerar agregar animaciones suaves para el toggle de campos
4. Documentar en el manual de usuario si es necesario
