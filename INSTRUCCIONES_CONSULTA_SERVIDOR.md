# Instrucciones para Ejecutar Consulta en Servidor PythonAnywhere

## Opción 1: Usando la Consola Bash de PythonAnywhere (Recomendado)

1. **Accede a PythonAnywhere:**
   - Ve a https://www.pythonanywhere.com/
   - Inicia sesión con tu cuenta

2. **Abre la Consola Bash:**
   - En el Dashboard, haz clic en "Consoles"
   - Haz clic en "Bash" para abrir una nueva consola

3. **Navega al directorio del proyecto:**
   ```bash
   cd ~/Proyecto_Contratos
   # O el nombre de tu directorio del proyecto
   ```

4. **Ejecuta el script de consulta:**
   ```bash
   python consulta_sqlite.py
   ```

## Opción 2: Usando Django Shell (Más Completo)

1. **Abre la Consola Bash** (igual que arriba)

2. **Navega al directorio del proyecto:**
   ```bash
   cd ~/Proyecto_Contratos
   ```

3. **Ejecuta el script usando Django shell:**
   ```bash
   python manage.py shell < consulta_polizas.py
   ```

   O si prefieres ejecutarlo interactivamente:
   ```bash
   python manage.py shell
   ```
   Luego copia y pega el contenido del archivo `consulta_polizas.py`

## Opción 3: Usando el Script de Verificación Completo

1. **Sube el archivo `verificar_polizas_db.py` al servidor:**
   - Ve a "Files" en el Dashboard
   - Navega a tu directorio del proyecto
   - Sube el archivo `verificar_polizas_db.py`

2. **Ejecuta desde la consola Bash:**
   ```bash
   cd ~/Proyecto_Contratos
   python manage.py shell < verificar_polizas_db.py
   ```

## Opción 4: Consulta SQL Directa (Si prefieres SQL)

1. **Abre la Consola Bash**

2. **Ejecuta SQLite directamente:**
   ```bash
   cd ~/Proyecto_Contratos
   sqlite3 db.sqlite3
   ```

3. **Ejecuta estas consultas SQL:**
   ```sql
   -- Buscar el contrato 5412
   SELECT id, num_contrato FROM gestion_contrato WHERE num_contrato LIKE '%5412%';
   
   -- Reemplaza CONTRATO_ID con el ID obtenido arriba
   -- Ver Otros Sí del contrato
   SELECT id, numero_otrosi, estado FROM gestion_otrosi WHERE contrato_id = CONTRATO_ID;
   
   -- Ver pólizas de Cumplimiento
   SELECT id, numero_poliza, otrosi_id, documento_origen_tipo, fecha_vencimiento 
   FROM gestion_poliza 
   WHERE contrato_id = CONTRATO_ID AND tipo = 'Cumplimiento';
   
   -- Salir de SQLite
   .quit
   ```

## Notas Importantes

- Si el proyecto usa un entorno virtual, actívalo primero:
  ```bash
  source ~/mi_entorno_virtual/bin/activate
  ```

- Si tienes problemas de permisos, verifica que el archivo tenga permisos de ejecución:
  ```bash
  chmod +x consulta_sqlite.py
  ```

- Los resultados se mostrarán directamente en la consola
