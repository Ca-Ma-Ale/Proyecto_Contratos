@echo off
REM Script para automatizar backups diarios en Windows
REM Uso: Agregar a Tareas Programadas de Windows para ejecución diaria
REM Incluye envío automático a ubicaciones remotas configuradas

REM Configuración
set PROJECT_DIR=C:\ruta\al\proyecto
set VENV_DIR=%PROJECT_DIR%\venv
set BACKUP_DIR=%PROJECT_DIR%\backups
set KEEP_DAYS=30

REM Activar entorno virtual
call "%VENV_DIR%\Scripts\activate.bat"

REM Cambiar al directorio del proyecto
cd /d "%PROJECT_DIR%"

REM Ejecutar comando de backup con envío remoto automático
REM El envío remoto se controla mediante variables de entorno en .env
REM Para habilitar: BACKUP_REMOTE_ENABLED=True en .env
python manage.py backup_database --keep-days %KEEP_DAYS% --format both --remote

REM Opcional: Comprimir backups antiguos (requiere 7-Zip o similar)
REM forfiles /p "%BACKUP_DIR%" /m backup_*.json /d -7 /c "cmd /c 7z a @path.zip @path && del @path"

echo Backup diario completado: %date% %time%

