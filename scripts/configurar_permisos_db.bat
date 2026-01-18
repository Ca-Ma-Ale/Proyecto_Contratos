@echo off
REM Script para configurar permisos de seguridad en base de datos SQLite (Windows)
REM Uso: scripts\configurar_permisos_db.bat

echo 🔒 Configurando permisos de seguridad para base de datos SQLite
echo ================================================================

set DB_FILE=db.sqlite3

if not exist "%DB_FILE%" (
    echo ⚠️  Archivo %DB_FILE% no encontrado
    echo    Ejecutar primero: python manage.py migrate
    exit /b 1
)

REM En Windows, usar icacls para configurar permisos
REM Restringir acceso solo al usuario actual
icacls "%DB_FILE%" /inheritance:r >nul 2>&1
icacls "%DB_FILE%" /grant:r "%USERNAME%:(F)" >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo ✅ Permisos configurados correctamente
    echo    Solo el usuario actual puede acceder al archivo
) else (
    echo ⚠️  No se pudieron configurar permisos automáticamente
    echo    Configurar manualmente desde Propiedades del archivo
)

REM Verificar que el archivo no está en el repositorio
git ls-files --error-unmatch "%DB_FILE%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ⚠️  ADVERTENCIA: %DB_FILE% está en el repositorio Git
    echo    Agregar a .gitignore y eliminar del repositorio
) else (
    echo ✅ %DB_FILE% no está en el repositorio (correcto)
)

echo.
echo ================================================================
echo ✅ Configuración completada

