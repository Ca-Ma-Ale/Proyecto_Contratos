#!/bin/bash
# Script para configurar permisos de seguridad en base de datos SQLite
# Uso: bash scripts/configurar_permisos_db.sh

echo "🔒 Configurando permisos de seguridad para base de datos SQLite"
echo "================================================================"

DB_FILE="db.sqlite3"

if [ ! -f "$DB_FILE" ]; then
    echo "⚠️  Archivo $DB_FILE no encontrado"
    echo "   Ejecutar primero: python manage.py migrate"
    exit 1
fi

# Configurar permisos (solo propietario puede leer/escribir)
chmod 600 "$DB_FILE"

# Verificar permisos
PERMISSIONS=$(stat -c "%a" "$DB_FILE" 2>/dev/null || stat -f "%OLp" "$DB_FILE" 2>/dev/null)

if [ "$PERMISSIONS" = "600" ]; then
    echo "✅ Permisos configurados correctamente: $PERMISSIONS"
    echo "   Solo el propietario puede leer/escribir el archivo"
else
    echo "⚠️  Permisos actuales: $PERMISSIONS (debe ser 600)"
    echo "   Intentar manualmente: chmod 600 $DB_FILE"
fi

# Verificar que el archivo no está en el repositorio
if git ls-files --error-unmatch "$DB_FILE" >/dev/null 2>&1; then
    echo "⚠️  ADVERTENCIA: $DB_FILE está en el repositorio Git"
    echo "   Agregar a .gitignore y eliminar del repositorio"
else
    echo "✅ $DB_FILE no está en el repositorio (correcto)"
fi

echo ""
echo "================================================================"
echo "✅ Configuración completada"

