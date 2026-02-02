# Solución al Error: ModuleNotFoundError: No module named 'axes'

## Problema
Falta instalar las dependencias del proyecto en PythonAnywhere.

## Solución Rápida

1. **En la Consola Bash de PythonAnywhere, ejecuta:**

```bash
cd ~/Proyecto_Contratos
pip3 install --user -r requirements.txt
```

Si eso no funciona, intenta:

```bash
pip3 install --user django-axes
```

## Si Usas Entorno Virtual

Si el proyecto usa un entorno virtual:

```bash
# Activar el entorno virtual primero
source ~/mi_entorno_virtual/bin/activate

# Luego instalar dependencias
pip install -r requirements.txt
```

## Verificar Instalación

Después de instalar, verifica:

```bash
python3 -c "import axes; print('axes instalado correctamente')"
```

## Luego Ejecuta la Consulta

Una vez instalado, ejecuta:

```bash
python3 manage.py shell
```

Y pega el código de consulta.
