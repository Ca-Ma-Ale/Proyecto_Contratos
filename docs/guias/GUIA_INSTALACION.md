# 🚀 Guía de Instalación - Sistema de Gestión de Contratos

## 📋 Requisitos Previos

- Python 3.10+
- pip (gestor de paquetes de Python)
- Git (opcional, para clonar el repositorio)

## 🔧 Instalación Paso a Paso

### 1. **Clonar el Repositorio** (si aplica)
```bash
git clone <url-del-repositorio>
cd Proyecto_Contratos
```

### 2. **Crear Entorno Virtual**
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

### 3. **Instalar Dependencias**
```bash
pip install -r requirements.txt
```

### 4. **Configurar Variables de Entorno**
```bash
# Copiar archivo de ejemplo
copy env_example.txt .env

# Editar .env con tus configuraciones
notepad .env
```

**Contenido del archivo .env:**
```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

**Generar SECRET_KEY segura:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. **Configurar Base de Datos**
```bash
# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

### 6. **Crear Directorios Necesarios**
```bash
mkdir logs
mkdir media
echo. > logs\django_errors.log
```

### 7. **Recolectar Archivos Estáticos**
```bash
python manage.py collectstatic
```

### 8. **Ejecutar Servidor de Desarrollo**
```bash
python manage.py runserver
```

## 🌐 Acceso al Sistema

### **URLs Principales:**
- **Login:** http://localhost:8000/login/
- **Dashboard:** http://localhost:8000/
- **Administración:** http://localhost:8000/admin/

### **Credenciales por Defecto:**
- **Usuario:** (el que creaste con createsuperuser)
- **Contraseña:** (la que configuraste)

## ✅ Verificación de Instalación

### **1. Probar Login**
1. Ve a http://localhost:8000/login/
2. Inicia sesión con tu usuario
3. Deberías ser redirigido al dashboard

### **2. Probar Funcionalidades**
1. Crear un contrato
2. Crear un arrendatario
3. Crear un local
4. Verificar que el formateo funciona

### **3. Verificar Formateo**
1. En cualquier campo monetario, escribe: `2500000`
2. Debería mostrarse como: `2.500.000`
3. En campos de porcentaje, escribe: `8`
4. Debería mostrarse como: `8%`

## 🔧 Configuración Avanzada

### **Configuración de Base de Datos**
Por defecto usa SQLite. Para cambiar a MySQL o PostgreSQL:

1. **Instalar driver de base de datos:**
```bash
# Para MySQL
pip install mysqlclient

# Para PostgreSQL
pip install psycopg2-binary
```

2. **Configurar en settings.py:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # o postgresql
        'NAME': 'nombre_bd',
        'USER': 'usuario',
        'PASSWORD': 'contraseña',
        'HOST': 'localhost',
        'PORT': '3306',  # 5432 para PostgreSQL
    }
}
```

### **Configuración de Email** (opcional)
```python
# En settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu-email@gmail.com'
EMAIL_HOST_PASSWORD = 'tu-contraseña'
```

## 🚨 Solución de Problemas

### **Error: "No module named 'decouple'"**
```bash
pip install python-decouple
```

### **Error: "SECRET_KEY not found"**
1. Verifica que el archivo `.env` existe
2. Verifica que `SECRET_KEY` está en el archivo
3. Reinicia el servidor

### **Error: "Database is locked"**
```bash
# Detener servidor (Ctrl+C)
# Esperar unos segundos
python manage.py runserver
```

### **Error: "Static files not found"**
```bash
python manage.py collectstatic --noinput
```

### **Error: "Permission denied"**
```bash
# En Linux/Mac
chmod +x venv/bin/activate
```

## 📊 Verificación de Funcionalidades

### **Checklist de Instalación:**
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas
- [ ] Archivo .env configurado
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] Directorios logs/ y media/ creados
- [ ] Servidor ejecutándose
- [ ] Login funciona
- [ ] Dashboard carga
- [ ] Formateo funciona

## 🎯 Próximos Pasos

Una vez que la instalación funcione:

1. **Lee la documentación:** [README.md](README.md)
2. **Configura para producción:** [DEPLOYMENT_PYTHONANYWHERE.md](DEPLOYMENT_PYTHONANYWHERE.md)
3. **Revisa la seguridad:** [CHECKLIST_PRODUCCION.md](CHECKLIST_PRODUCCION.md)

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en `logs/django_errors.log`
2. Verifica la consola del navegador (F12)
3. Consulta la documentación de Django
4. Revisa este archivo de nuevo

---

**Última actualización:** Octubre 2025  
**Versión:** 2.0  
**Compatible con:** Python 3.10+, Django 5.0+
