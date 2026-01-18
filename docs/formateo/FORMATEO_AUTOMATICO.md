# Formateo Automático de Números

## Descripción
El sistema incluye formateo automático de números que se aplica a todos los templates sin configuración adicional.

## Funcionalidades

### ✅ Formateo Automático
- **Campos monetarios**: Se formatean automáticamente con separadores de miles (1.000.000)
- **Campos de porcentaje**: Se formatean automáticamente sin decimales innecesarios
- **Detección inteligente**: No formatea valores ya formateados
- **Manejo de base de datos**: Quita automáticamente `.00` de valores de base de datos

### 🎯 Clases CSS Requeridas

Para que el formateo funcione automáticamente, los campos deben tener las siguientes clases:

#### Campos Monetarios
```html
<input type="text" class="form-control money-input" name="valor">
```

#### Campos de Porcentaje
```html
<input type="text" class="form-control percentage-input" name="porcentaje">
```

## Ejemplos de Uso

### Formulario Django
```python
# En forms.py
class MiFormulario(forms.ModelForm):
    class Meta:
        model = MiModelo
        fields = ['valor_monetario', 'porcentaje']
        widgets = {
            'valor_monetario': forms.TextInput(attrs={
                'class': 'form-control money-input',
                'type': 'text',
                'pattern': '[0-9.,]*',
                'inputmode': 'numeric'
            }),
            'porcentaje': forms.TextInput(attrs={
                'class': 'form-control percentage-input',
                'type': 'text',
                'pattern': '[0-9.,]*',
                'inputmode': 'numeric'
            }),
        }
```

### Template HTML
```html
<!-- Campo monetario -->
<div class="form-group">
    <label for="valor">Valor Monetario</label>
    <input type="text" class="form-control money-input" id="valor" name="valor">
</div>

<!-- Campo de porcentaje -->
<div class="form-group">
    <label for="porcentaje">Porcentaje</label>
    <input type="text" class="form-control percentage-input" id="porcentaje" name="porcentaje">
</div>
```

## Comportamiento

### Al Cargar la Página
- Los valores existentes se formatean automáticamente
- Se quitan los `.00` de valores de base de datos
- Se aplican separadores de miles

### Al Editar
- **Al hacer clic**: Se muestra el valor sin formato para edición fácil
- **Al salir del campo**: Se formatea automáticamente con separadores de miles
- **Al enviar**: Se limpian los formatos antes de enviar al servidor

### Validación
- Solo acepta números
- Limpia automáticamente caracteres no numéricos
- Previene formateo múltiple del mismo valor

## Archivos Involucrados

- `static/js/formato_numeros.js`: JavaScript global para formateo
- `templates/base.html`: Incluye el script automáticamente
- `gestion/templatetags/formato_filters.py`: Filtros para templates

## Ventajas

1. **Automático**: No requiere configuración adicional
2. **Consistente**: Funciona igual en todos los templates
3. **Inteligente**: Detecta valores ya formateados
4. **Compatible**: Funciona con Django forms y HTML puro
5. **Mantenible**: Un solo archivo controla todo el formateo

## Notas Técnicas

- El formateo se aplica automáticamente a todos los templates que extienden `base.html`
- Los campos deben tener las clases CSS correctas para funcionar
- El JavaScript se ejecuta después de que el DOM esté completamente cargado
- Compatible con formularios dinámicos y AJAX
