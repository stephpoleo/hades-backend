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

## Despliegue en GCP (Cloud Run + Cloud SQL)

Esta sección explica el proceso completo de migración y despliegue en Google Cloud Platform.

### Arquitectura en GCP

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Cloud Run     │────▶│   Cloud SQL      │     │  Cloud Storage  │
│  (hades-backend)│     │  (PostgreSQL)    │     │  (hades-media)  │
└────────┬────────┘     └──────────────────┘     └────────▲────────┘
         │                                                 │
         │              ┌──────────────────┐               │
         └─────────────▶│  Secret Manager  │───────────────┘
                        │  (credenciales)  │
                        └──────────────────┘
```

### Paso 1: Prerrequisitos en GCP

#### 1.1 Crear proyecto y habilitar APIs

```bash
# Crear proyecto (si no existe)
gcloud projects create hades-backend-prod --name="Hades Backend"

# Establecer proyecto activo
gcloud config set project hades-backend-prod

# Habilitar APIs necesarias
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com
```

#### 1.2 Crear instancia Cloud SQL

```bash
# Crear instancia PostgreSQL
gcloud sql instances create hades-bd \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-type=SSD \
  --storage-size=10GB

# Crear base de datos
gcloud sql databases create postgres --instance=hades-bd

# Crear usuario
gcloud sql users create hades_user \
  --instance=hades-bd \
  --password=TU_PASSWORD_SEGURO
```

#### 1.3 Crear bucket en Cloud Storage

```bash
# Crear bucket para archivos adjuntos
gcloud storage buckets create gs://hades-media \
  --location=us-central1 \
  --uniform-bucket-level-access
```

#### 1.4 Crear repositorio en Artifact Registry

```bash
# Crear repositorio Docker
gcloud artifacts repositories create hades \
  --repository-format=docker \
  --location=us-central1 \
  --description="Hades Backend Docker images"
```

### Paso 2: Configurar Secretos

#### 2.1 Crear secretos en Secret Manager

```bash
# SECRET_KEY de Django
echo -n "tu-clave-secreta-muy-larga-y-segura" | \
  gcloud secrets create SECRET_KEY --data-file=-

# Password de la base de datos principal
echo -n "tu-password-db" | \
  gcloud secrets create DB_PASSWORD --data-file=-

# Usuario de la base de datos
echo -n "hades_user" | \
  gcloud secrets create DB_USER --data-file=-

# Password de base de datos EDS externa (si aplica)
echo -n "password-eds" | \
  gcloud secrets create EDS_ERELIS_DB_PASSWORD --data-file=-

# Credenciales de GCP Storage (JSON de Service Account)
gcloud secrets create GCP_STORAGE_CREDENTIALS \
  --data-file=path/to/service-account.json
```

#### 2.2 Configurar permisos del Service Account

```bash
# Obtener el service account de Cloud Run
PROJECT_NUMBER=$(gcloud projects describe hades-backend-prod --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Permisos para Secret Manager
gcloud projects add-iam-policy-binding hades-backend-prod \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

# Permisos para Cloud SQL
gcloud projects add-iam-policy-binding hades-backend-prod \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudsql.client"

# Permisos para Cloud Storage
gcloud projects add-iam-policy-binding hades-backend-prod \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.objectAdmin"
```

### Paso 3: Ejecutar Migraciones en Producción

Para aplicar migraciones a la base de datos de producción, se utiliza **Cloud SQL Proxy** que crea un túnel seguro desde tu máquina local hacia Cloud SQL.

#### Prerrequisitos

1. Tener instalado `gcloud` CLI y estar autenticado
2. Tener el archivo `.env.prod` configurado (ya viene preconfigurado para usar el proxy)
3. Tener el entorno virtual de Python activo

#### Proceso paso a paso

**Terminal 1: Iniciar Cloud SQL Proxy**

```bash
# Usando Makefile (recomendado)
make cloud-proxy DJANGO_ENV=prod

# O manualmente en Windows:
cloud_sql_proxy.exe -instances=hades-backend-prod:us-central1:hades-bd=tcp:5434

# O en Linux/Mac:
./cloud_sql_proxy -instances=hades-backend-prod:us-central1:hades-bd=tcp:5434
```

> El proxy debe permanecer activo durante todo el proceso. Déjalo corriendo en esta terminal.

**Terminal 2: Ejecutar migraciones**

```powershell
# Windows (PowerShell)
.\venv\Scripts\activate
$env:DJANGO_ENV="prod"; python manage.py migrate
```

```bash
# Linux/Mac
source venv/bin/activate
DJANGO_ENV=prod python manage.py migrate
```

#### Verificar migraciones aplicadas

```powershell
# Ver estado de migraciones
$env:DJANGO_ENV="prod"; python manage.py showmigrations
```

#### Notas importantes

- El archivo `.env.prod` ya está configurado con `DB_HOST=127.0.0.1` y `DB_PORT=5434` para conectar via proxy
- Las credenciales de producción (`DB_USER`, `DB_PASSWORD`) se cargan automáticamente desde `.env.prod`
- **No es necesario redesplegar** después de ejecutar migraciones si el código ya está desplegado
- Si agregas nuevos campos al modelo, primero crea la migración (`makemigrations`), luego aplícala a producción

#### Migraciones automáticas en deploy (alternativa)

El `entrypoint.sh` del contenedor ejecuta migraciones automáticamente al iniciar:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Esto significa que si haces un nuevo deploy con migraciones pendientes, se aplicarán automáticamente. Sin embargo, para cambios críticos en el schema es recomendable ejecutar las migraciones manualmente primero usando el proceso anterior.

#### Desarrollo local sin credenciales GCP

Gracias a las mejoras en `settings.py`, las migraciones pueden ejecutarse localmente **sin credenciales de GCP configuradas**:

```python
# settings.py - Manejo graceful de credenciales
GCP_AVAILABLE = True/False  # Detecta si el SDK está instalado

if _gcp_creds_file and GCP_AVAILABLE:
    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(...)
else:
    GS_CREDENTIALS = None  # Permite iniciar sin credenciales
```

Esto permite:
- Ejecutar `python manage.py migrate` localmente sin GCP
- Desarrollo local sin configurar credenciales de storage
- El storage de archivos solo se activa cuando las credenciales están presentes

### Paso 4: Build y Push de la Imagen

```bash
# Autenticarse en Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build y push usando Cloud Build (recomendado)
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/hades-backend-prod/hades/hades-backend:latest .

# Alternativa: Build local y push
docker build -t us-central1-docker.pkg.dev/hades-backend-prod/hades/hades-backend:latest .
docker push us-central1-docker.pkg.dev/hades-backend-prod/hades/hades-backend:latest
```

### Paso 5: Deploy en Cloud Run

#### Variables de entorno requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DJANGO_ENV` | Entorno de ejecución | `prod` |
| `DEBUG` | Modo debug (siempre False en prod) | `False` |
| `FORCE_HTTPS` | Forzar HTTPS | `true` |
| `HOST` | URL del servicio | `hades-backend-xxx.run.app` |
| `DB_HOST` | Socket de Cloud SQL | `/cloudsql/proyecto:region:instancia` |
| `DB_PORT` | Puerto de BD | `5432` |
| `DB_NAME` | Nombre de la BD | `postgres` |
| `FRONT_ORIGIN` | URL del frontend (CORS) | `https://hades-frontend-xxx.run.app` |
| `API_ORIGIN` | URL del backend (CSRF) | `https://hades-backend-xxx.run.app` |

#### Comando de deploy

**PowerShell (Windows):**
```powershell
gcloud run deploy hades-backend `
  --image us-central1-docker.pkg.dev/hades-backend-prod/hades/hades-backend:latest `
  --region us-central1 `
  --platform managed `
  --allow-unauthenticated `
  --add-cloudsql-instances hades-backend-prod:us-central1:hades-bd `
  --set-env-vars "DJANGO_ENV=prod,DEBUG=False,FORCE_HTTPS=true,HOST=hades-backend-694277248400.us-central1.run.app,DB_HOST=/cloudsql/hades-backend-prod:us-central1:hades-bd,DB_PORT=5432,DB_NAME=postgres,FRONT_ORIGIN=https://hades-frontend-694277248400.us-central1.run.app,API_ORIGIN=https://hades-backend-694277248400.us-central1.run.app" `
  --set-secrets "SECRET_KEY=SECRET_KEY:latest,DB_PASSWORD=DB_PASSWORD:latest,DB_USER=DB_USER:latest" `
  --memory 512Mi --cpu 1 --min-instances 1 --port 8000
```

**Bash (Linux/Mac):**
```bash
gcloud run deploy hades-backend \
  --image us-central1-docker.pkg.dev/hades-backend-prod/hades/hades-backend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances hades-backend-prod:us-central1:hades-bd \
  --set-env-vars "DJANGO_ENV=prod,DEBUG=False,FORCE_HTTPS=true,HOST=hades-backend-694277248400.us-central1.run.app,DB_HOST=/cloudsql/hades-backend-prod:us-central1:hades-bd,DB_PORT=5432,DB_NAME=postgres,FRONT_ORIGIN=https://hades-frontend-694277248400.us-central1.run.app,API_ORIGIN=https://hades-backend-694277248400.us-central1.run.app" \
  --set-secrets "SECRET_KEY=SECRET_KEY:latest,DB_PASSWORD=DB_PASSWORD:latest,DB_USER=DB_USER:latest" \
  --memory 512Mi --cpu 1 --min-instances 1 \
  --port 8000
```

### Paso 6: Verificar el Deploy

```bash
# Ver logs del servicio
gcloud run services logs read hades-backend --region us-central1

# Verificar estado
gcloud run services describe hades-backend --region us-central1

# Probar endpoint
curl https://hades-backend-xxx.us-central1.run.app/api/swagger/
```

### Configuración de Base de Datos EDS Externa (Opcional)

Si necesitas conectar a una base de datos EDS externa (Erelis/OASIS):

```bash
# Agregar variables adicionales al deploy
--set-env-vars "...,EDS_SOURCES=erelis,EDS_PROFILE=erelis,EDS_DB_TABLE=oasis_cat_eds,EDS_ERELIS_DB_ENGINE=hades_app.db_backends.postgres_compat,EDS_ERELIS_DB_NAME=postgres,EDS_ERELIS_DB_USER=erelis_admin,EDS_ERELIS_DB_HOST=erelis-prod.postgres.database.azure.com,EDS_ERELIS_DB_PORT=5432,EDS_ERELIS_DB_SSLMODE=require" \
--set-secrets "...,EDS_ERELIS_DB_PASSWORD=EDS_ERELIS_DB_PASSWORD:latest"
```

### Troubleshooting

#### Error: "No se pudieron obtener credenciales GCP"

Este warning es **normal** en desarrollo local sin credenciales configuradas. El backend funciona sin storage de archivos.

**Solución para producción:**
1. Verificar que el secreto `GCP_STORAGE_CREDENTIALS` existe en Secret Manager
2. Verificar que el Service Account tiene el rol `secretmanager.secretAccessor`

#### Error: 400 Bad Request

**Causa:** El host no está en `ALLOWED_HOSTS`

**Solución:**
```bash
# Agregar el host correcto a la variable HOST
--set-env-vars "...,HOST=tu-servicio.run.app"
```

#### Error: Bucles de redirección HTTPS

**Causa:** `FORCE_HTTPS=true` pero el proxy no envía el header correcto

**Solución:** Ya configurado en `settings.py`:
```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

#### Error: Conexión a base de datos rechazada

**Verificar:**
1. El Service Account tiene rol `cloudsql.client`
2. La instancia está en `--add-cloudsql-instances`
3. `DB_HOST` usa formato socket: `/cloudsql/proyecto:region:instancia`
4. Usuario y password correctos en secretos

### Redirección raíz
`/` redirige a `/api/swagger/` (definido en `server/urls.py`).

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
- **API EDS:** `http://localhost:8000/api/eds/` - JSON con estaciones de servicio
- **API Dashboard KPIs:** `http://localhost:8000/api/dashboard/kpis/` - Métricas de cumplimiento
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

### Deploy Rápido con Script (Recomendado)

El proyecto incluye un script `deploy.ps1` que automatiza el deploy a Google Cloud Run con todas las variables de entorno necesarias.

```powershell
# Windows PowerShell (recomendado)
powershell -ExecutionPolicy Bypass -File deploy.ps1
```

El script `deploy.ps1`:
- Construye la imagen Docker usando Cloud Build
- Configura todas las variables de entorno (DJANGO_ENV, DB_*, CORS, EDS_*)
- Configura los secretos desde Secret Manager
- Despliega a Cloud Run con la conexión a Cloud SQL

> **Importante**: Usar siempre `deploy.ps1` para deployar, ya que `gcloud run deploy --source .` no preserva las variables de entorno.

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

---

## 📝 Changelog

### feat/improvements (Rama actual)

#### Dashboard KPIs Endpoint
- **Nuevo endpoint:** `GET /api/dashboard/kpis/` para métricas de cumplimiento
- Soporta filtros por zona (`?zone=`), EDS (`?eds=`), formulario (`?form=`) y rango de fechas (`?start_date=`, `?end_date=`)
- Calcula grades de cumplimiento (porcentaje) por work order
- Agrupa datos por EDS, formulario y zona para visualización en dashboard

#### Soporte para Múltiples Imágenes en FormAnswers
- El modelo `FormAnswers` ahora soporta hasta 3 imágenes: `image`, `image_2`, `image_3`
- Nuevos endpoints para descargar adjuntos adicionales:
  - `GET /api/form-answers/{id}/attachment-2/`
  - `GET /api/form-answers/{id}/attachment-3/`

#### Sistema de Paginación Mejorado
- Nuevo módulo `hades_app/pagination.py` con clases reutilizables
- `StandardPagination`: 20 items por página, máximo 100
- `LargePagination`: Para listados grandes (EDS, usuarios)
- Parámetro `?no_pagination=true` disponible en EDS y Users para dropdowns

#### Optimizaciones de Rendimiento
- Batch loading de EDS en listado de usuarios (evita N+1 queries)
- Stats de work orders precalculados en contexto del serializer
- Nuevos campos `assigned_forms` y `completed_forms` en UsersSerializer

#### Filtros en Usuarios
- Búsqueda por nombre: `GET /api/users/?search=nombre`
- Filtrar por EDS: `GET /api/users/?eds_name=nombre_eds`

#### FormAnswers con Clave EDS
- Serializer modificado para guardar `clave_eds_fk` en respuestas de formulario
- Permite asociar respuestas directamente con la EDS correspondiente
