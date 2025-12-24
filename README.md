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
- Docker / Docker Compose (para la nueva opción de contenedores)

## 🛠️ Instalación

### Opción rápida: Docker / Docker Compose

```bash
# Copia la plantilla general y crea una variante local
cp .env.docker.example .env.docker
cp .env.docker .env.docker.local  # ajusta valores para pruebas

# Ejecuta toda la pila usando el archivo local
ENV_FILE=.env.docker.local docker compose up --build

# La API quedará en http://localhost:8000 y la DB en 5432
```

> El backend carga automáticamente `.env.<entorno>.local` si existe (por ejemplo `.env.docker.local`).
> Para casos especiales puedes forzar un archivo exacto exportando `DJANGO_ENV_FILE=/ruta/a/archivo` antes de ejecutar `manage.py` o `docker compose`.

El entrypoint del contenedor espera a que Postgres esté disponible, corre migraciones y arranca Gunicorn. Los volúmenes `postgres_data` y `media_data` persisten la base y los uploads.

Cuando termines:

```bash
ENV_FILE=.env.docker.local docker compose down
# Para limpiar datos locales
docker compose --env-file .env.docker.local down -v
```

Para ejecutar comandos dentro del contenedor (por ejemplo crear un superusuario):

```bash
ENV_FILE=.env.docker.local docker compose exec backend python manage.py createsuperuser
```

> **¿Y después para GCP?** Usa exactamente el mismo `Dockerfile`. Cuando estés listo:
>
> 1. Construye la imagen dirigida a tu registro en GCP: `docker build -t gcr.io/PROJECT_ID/hades-backend:latest .`
> 2. Súbela: `docker push gcr.io/PROJECT_ID/hades-backend:latest`.
> 3. Despliega en Cloud Run (o tu servicio preferido) apuntando a Cloud SQL y cargando las variables reales (por ejemplo `DB_HOST=/cloudsql/INSTANCE`, `DJANGO_ENV=prod`, `SECRET_KEY` desde Secret Manager). El `docker-compose` queda reservado para pruebas locales, así que no necesitas modificarlo para producción; solo cambian las variables que pasas al servicio gestionado.

### ⚠️ Requisito previo: Cloud SQL Proxy

Tanto la pila Docker como los comandos del Makefile esperan llegar a la base de datos productiva mediante el Cloud SQL Proxy expuesto en tu máquina (`host.docker.internal:5434`). Antes de cualquier prueba local abre otra terminal y deja corriendo:

```bash
make cloud-proxy DJANGO_ENV=prod
```

Ese comando levanta `cloud_sql_proxy.exe` apuntando a la instancia real y debe permanecer activo mientras ejecutes `docker compose ...` o `make run-server/test/...`. Si prefieres usar una base local, ajusta tu `.env` para apuntar a ella y no ejecutes el proxy.

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

### Documentaci¢n Swagger/Redoc

- Swagger UI: `http://localhost:8000/api/swagger/`
- Redoc: `http://localhost:8000/api/redoc/`
- Esquema JSON: `http://localhost:8000/api/schema.json`

En Docker los est ticos se sirven con WhiteNoise y `collectstatic` se ejecuta en el entrypoint, as¡ que basta con `docker compose up --build` para tener la UI. En local, instala dependencias (`pip install -r requirements.txt`) y corre `python manage.py runserver`.

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

| Variable        | Descripción                                                     | Valor por defecto     |
| --------------- | --------------------------------------------------------------- | --------------------- |
| `SECRET_KEY`    | Clave secreta de Django                                         | -                     |
| `DEBUG`         | Modo debug                                                      | `True`                |
| `ALLOWED_HOSTS` | Hosts permitidos                                                | `localhost,127.0.0.1` |
| `DJANGO_ENV`    | Selecciona qué archivo `.env.<env>` cargar (`dev` o `prod`)     | `prod`                |
| `DB_NAME`       | Nombre de la base de datos                                      | `hades_db`            |
| `DB_USER`       | Usuario de la base de datos                                     | `hades_user`          |
| `DB_PASSWORD`   | Contraseña de la base de datos                                  | -                     |
| `DB_HOST`       | Host de la base de datos                                        | `localhost`           |
| `DB_PORT`       | Puerto de la base de datos                                      | `5432`                |
| `EDS_SOURCES`   | Perfiles EDS disponibles en orden de prioridad                  | `erelis,oasis`        |
| `EDS_PROFILE`   | Fuerza el perfil EDS activo (`erelis`, `oasis`, `legacy`, etc.) | Primer perfil válido  |
| `EDS_DB_TABLE`  | Nombre de la tabla remota a usar para el modelo `EDS`           | `oasis_cat_eds`       |

### Perfiles de EDS (erelis / oasis)

El backend puede leer EDS desde múltiples orígenes externos y permite alternar entre ellos sin tocar el código.

1. Define el orden de perfiles disponibles:

   ```env
   EDS_SOURCES=erelis,oasis
   ```

2. Registra las credenciales de cada perfil:

   ```env
   # Perfil erelis (variables clásicas tomadas del .env dev/prod)
   EDS_ERELIS_DB_NAME=erelis_db
   EDS_ERELIS_DB_USER=erelis_user
   EDS_ERELIS_DB_PASSWORD=secret
   EDS_ERELIS_DB_HOST=10.0.0.10
   EDS_ERELIS_DB_PORT=5432

   # Perfil oasis (puede vivir fuera del .env)
   EDS_OASIS_DB_JSON=secrets/oasis-sa.json
   ```

3. Selecciona el perfil activo exportando la variable o pasándola al comando `make`/`manage.py`:

   ```bash
   # Usar el perfil oasis solo para esta ejecución
   make run-server EDS_PROFILE=oasis

   # O dejarlo fijo en tu .env
   EDS_PROFILE=oasis
   ```

Si no defines `EDS_PROFILE`, se toma el primer perfil que tenga credenciales válidas; todavía se acepta la configuración histórica tipo `EDS_DB_NAME` bajo el alias `legacy`.

#### Credenciales desde JSON / Google Service Account

- Apunta `EDS_<PERFIL>_DB_JSON` a un archivo JSON (ruta absoluta o relativa a la raíz del repo).
- El JSON debe exponer al menos los campos `name`, `user`, `password`, `host` y `port`. También puedes incluir `engine` y `sslmode`.
- Si trabajas con un Google Service Account, duplica el JSON original y añade los campos anteriores junto con tus `private_key`/`client_email`; el backend reutiliza esos valores para conectarse mediante el driver PostgreSQL.
- El helper ignora claves vacías y valida que `name` exista antes de activar el perfil.

La tabla utilizada por el modelo `EDS` puede variar entre orígenes (por ejemplo `oasis_cat_eds` vs `erelis_cat_eds`); ajústala con la variable `EDS_DB_TABLE` cuando necesites apuntar a otra vista/materialización remota.

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
