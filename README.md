# Hades Backend

API REST backend desarrollada con Django y Django REST Framework para el proyecto Hades, que sustituye a sistema de JARBOSS.

## 🚀 Características

- **Django 5.2.4** - Framework web robusto y escalable
- **Django REST Framework** - Para construir APIs REST potentes
- **PostgreSQL** - Base de datos relacional
- **Autenticación por Token** - Sistema de autenticación seguro
- **Configuración por variables de entorno** - Fácil deployment y configuración

## 📋 Requisitos

- Python 3.8+
- PostgreSQL 12+
- pip (gestor de paquetes de Python)

## 🛠️ Instalación

### Método 1: Usando Makefile (Recomendado)

Si tienes `make` instalado en tu sistema:

```bash
# Ver todos los comandos disponibles
make help

# Configuración completa desde cero
make all-setup

# Crear superusuario
make create-superuser

# Ejecutar servidor de desarrollo
make run-server
```

#### Comandos Makefile disponibles:

- `make help` - Muestra todos los comandos disponibles
- `make install` - Instala las dependencias de Python
- `make setup-db` - Configura la base de datos con datos dummy
- `make reset-db` - Reinicia la base de datos con datos frescos
- `make run-server` - Inicia el servidor de desarrollo
- `make create-superuser` - Crea un superusuario para el admin
- `make clean` - Limpia archivos temporales
- `make clean-db` - Limpia datos de la base de datos (mantiene estructura)
- `make drop-tables` - Borra todas las tablas completamente

#### Instalación de Make:

**Windows:**

```bash
# Con winget (Gestor de paquetes oficial de Microsoft)
winget install --id GnuWin32.Make -e

# Con Chocolatey
choco install make

# O usar Git Bash (viene con Git)
```

> **⚠️ Nota importante para winget:** Después de instalar con winget, es posible que necesites agregar `make.exe` al PATH manualmente:
>
> 1. Busca la ubicación de instalación (generalmente `C:\Program Files (x86)\GnuWin32\bin\`)
> 2. Agrega esta ruta a las variables de entorno del sistema:
>    - Abre "Variables de entorno del sistema"
>    - Edita la variable `Path`
>    - Agrega la ruta `C:\Program Files (x86)\GnuWin32\bin\`
>    - Reinicia tu terminal
> 3. Verifica la instalación con: `make --version`

**Linux/Mac:**

```bash
# Ubuntu/Debian
sudo apt install make

# macOS
brew install make
```

### Método 2: Instalación manual

### 1. Clonar el repositorio

```bash
git clone https://gitlab.com/natgas-ti/hades/hades-backend.git
cd hades-backend
```

### 2. Crear y activar entorno virtual

```bash
python -m venv venv
# En Windows
venv\Scripts\activate
# En Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia el archivo `.env.example` a `.env` y configura las variables:

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus configuraciones:

```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=hades_db
DB_USER=hades_user
DB_PASSWORD=tu-password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Configurar base de datos

Asegúrate de que PostgreSQL esté corriendo y crea la base de datos:

```sql
CREATE DATABASE hades_db;
CREATE USER hades_user WITH PASSWORD 'tu-password';
GRANT ALL PRIVILEGES ON DATABASE hades_db TO hades_user;
```

### 6. Ejecutar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear superusuario (opcional)

```bash
python manage.py createsuperuser
```

## 🚀 Uso

### Inicio rápido con Makefile

```bash
# Configurar todo desde cero
make all-setup

# Crear superusuario
make create-superuser

# Iniciar servidor
make run-server
```

### Desarrollo diario

```bash
# Reiniciar base de datos con datos frescos
make reset-db

# Limpiar solo datos (mantener estructura de tablas)
make clean-db

# Borrar todas las tablas completamente
make drop-tables

# Ejecutar servidor
make run-server

# Ejecutar tests
make test

# Limpiar archivos temporales
make clean
```

### Desarrollo manual

### Desarrollo

Para ejecutar el servidor de desarrollo:

```bash
python manage.py runserver
```

La API estará disponible en: `http://localhost:8000/`

### Panel de administración

Accede al panel de administración en: `http://localhost:8000/admin/`

### API Endpoints

La API y dashboard están disponibles en:

- **Dashboard Web:** `http://localhost:8000/` - Vista web con todas las tablas
- **Panel de administración:** `http://localhost:8000/admin/` - Admin de Django
- **API Usuarios:** `http://localhost:8000/api/users/` - JSON con usuarios
- **API Plazas:** `http://localhost:8000/api/plazas/` - JSON con plazas
- **API Órdenes:** `http://localhost:8000/api/work-orders/` - JSON con órdenes
- **API Completa:** `http://localhost:8000/api/dashboard/` - JSON con todos los datos

### Datos de prueba

El proyecto incluye datos dummy que se insertan automáticamente con:

```bash
make setup-db
# o manualmente:
python manage.py run_sql --file=insert_dummy_data.sql
```

Incluye:

- 4 permisos y 2 roles
- 3 plazas en diferentes estados
- 3 estaciones de servicio (EDS)
- 4 usuarios con diferentes roles
- 3 preguntas de formulario
- 4 órdenes de trabajo con diferentes estados

### Gestión de base de datos

#### Comandos de limpieza disponibles:

```bash
# Limpiar solo los datos (mantiene estructura de tablas)
make clean-db

# Borrar todas las tablas completamente
make drop-tables

# Reiniciar con datos frescos (limpia + recrea + inserta datos)
make reset-db
```

#### Flujo de trabajo recomendado:

```bash
# Para desarrollo normal - limpiar datos y recargar:
make reset-db

# Para limpiar solo datos sin recargar:
make clean-db

# Para empezar completamente desde cero:
make drop-tables
make setup-db

# Para recrear estructura después de cambios en modelos:
make drop-tables
python manage.py makemigrations
python manage.py migrate
make setup-db
```

## 📁 Estructura del proyecto

```
hades-backend/
├── manage.py                 # Comando principal de Django
├── requirements.txt          # Dependencias del proyecto
├── Makefile                 # Comandos automatizados
├── setup.bat                # Script batch para Windows
├── .env.example             # Ejemplo de variables de entorno
├── README.md                # Este archivo
├── sql/                     # Scripts SQL
│   ├── create_tables.sql    # Creación de tablas
│   ├── insert_dummy_data.sql # Datos de prueba
│   ├── clean_database.sql   # Limpieza de datos (mantiene tablas)
│   └── drop_tables.sql      # Eliminación completa de tablas
├── server/                  # Configuración del proyecto Django
│   ├── __init__.py
│   ├── settings.py          # Configuración principal
│   ├── urls.py             # URLs principales
│   ├── wsgi.py             # WSGI config
│   └── asgi.py             # ASGI config
└── hades_app/              # App principal
    ├── __init__.py
    ├── models.py           # Modelos de datos
    ├── views.py            # Vistas/endpoints
    ├── urls.py             # URLs de la app
    ├── admin.py            # Configuración admin
    ├── templates/          # Plantillas HTML
    │   └── dashboard.html  # Dashboard web
    └── management/         # Comandos personalizados
        └── commands/
            └── run_sql.py  # Comando para ejecutar SQL
```

## 🔧 Configuración

### Variables de entorno

| Variable        | Descripción                    | Valor por defecto     |
| --------------- | ------------------------------ | --------------------- |
| `SECRET_KEY`    | Clave secreta de Django        | -                     |
| `DEBUG`         | Modo debug                     | `True`                |
| `ALLOWED_HOSTS` | Hosts permitidos               | `localhost,127.0.0.1` |
| `DB_NAME`       | Nombre de la base de datos     | `hades_db`            |
| `DB_USER`       | Usuario de la base de datos    | `hades_user`          |
| `DB_PASSWORD`   | Contraseña de la base de datos | -                     |
| `DB_HOST`       | Host de la base de datos       | `localhost`           |
| `DB_PORT`       | Puerto de la base de datos     | `5432`                |

### Django REST Framework

El proyecto está configurado con:

- Autenticación por sesión y token
- Permisos de autenticación requeridos por defecto
- Paginación de 20 elementos por página

## 🧪 Testing

Para ejecutar los tests:

```bash
python manage.py test
```

## 📦 Deployment

### Configuración de producción

1. Cambia `DEBUG=False` en el archivo `.env`
2. Configura `ALLOWED_HOSTS` con tu dominio
3. Usa una base de datos PostgreSQL en producción
4. Configura un servidor web (nginx + gunicorn)

### Comandos útiles

```bash
# Recoger archivos estáticos
python manage.py collectstatic

# Verificar deployment
python manage.py check --deploy
```

## 📞 Soporte

Para reportar problemas o solicitar ayuda:

- Crea un issue en GitLab
- Contacta al equipo de desarrollo

## 👥 Autores

- **Equipo NatDev** - Conformado por Stephanie Poleo, José Hernández del Castillo y Ángela Flores Araujo

## 📄 Licencia

Este proyecto pertenece a NatGas.

## 📊 Estado del proyecto

🚧 **En desarrollo activo** - Este proyecto está siendo desarrollado activamente.
