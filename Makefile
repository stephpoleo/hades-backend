# Makefile utilitario para el backend de Hades
# Enfocado en tareas usadas diariamente y con soporte a DJANGO_ENV

.PHONY: help preflight check-venv check-env-file install migrations migrate seed create-superuser shell run-server test test-v test-vv test-coverage test-fast test-module deploy lint format cloud-proxy clean

VENV := venv
PYTHON := $(VENV)\Scripts\python.exe
REQUIREMENTS := requirements.txt
DJANGO_ENV ?= prod
EDS_PROFILE ?= erelis
ENV_FILE := .env.$(DJANGO_ENV)
SET_ENV := set DJANGO_ENV=$(DJANGO_ENV) & set EDS_PROFILE=$(EDS_PROFILE) &
MANAGE := $(SET_ENV) $(PYTHON) manage.py
CLOUD_SQL_PROXY := cloud_sql_proxy.exe
CLOUD_SQL_INSTANCE ?= hades-backend-prod:us-central1:hades-bd
CLOUD_SQL_PORT ?= 5434
CLOUD_SQL_CREDENTIALS ?= hades-backend-prod.json

help:
	@echo "Comandos disponibles (DJANGO_ENV=$(DJANGO_ENV) / EDS_PROFILE=$(EDS_PROFILE)):"
	@echo ""
	@echo "  DESARROLLO:"
	@echo "    make install          - Instala/actualiza dependencias"
	@echo "    make run-server       - Aplica migraciones y levanta el server"
	@echo "    make shell            - Abre la shell de Django"
	@echo ""
	@echo "  BASE DE DATOS:"
	@echo "    make migrations       - Genera migraciones"
	@echo "    make migrate          - Aplica migraciones"
	@echo "    make seed             - Inserta datos dummy"
	@echo "    make create-superuser - Crea un superusuario"
	@echo "    make cloud-proxy      - Abre tunel Cloud SQL (requiere cloud_sql_proxy.exe)"
	@echo ""
	@echo "  TESTING:"
	@echo "    make test             - Ejecuta todos los tests"
	@echo "    make test-v           - Tests con verbosidad media (nombres de tests)"
	@echo "    make test-vv          - Tests con verbosidad alta (detalles completos)"
	@echo "    make test-fast        - Tests sin migraciones (--keepdb)"
	@echo "    make test-coverage    - Tests con reporte de cobertura"
	@echo "    make test-module M=X  - Tests de un modulo especifico (ej: M=AuthenticationTests)"
	@echo ""
	@echo "  CALIDAD DE CODIGO:"
	@echo "    make lint             - Ejecuta pylint sobre la app hades"
	@echo "    make format           - Ejecuta black sobre el codigo"
	@echo ""
	@echo "  DEPLOY:"
	@echo "    make deploy           - Ejecuta tests y despliega a Cloud Run"
	@echo "    make clean            - Limpiar archivos temporales"
	@echo ""
	@echo "  EJEMPLOS:"
	@echo "    make run-server DJANGO_ENV=prod"
	@echo "    make test-module M=WorkOrderTests"
	@echo "    make run-server EDS_PROFILE=oasis"

check-venv:
	@if not exist $(PYTHON) ( \
		echo "No se encontró el entorno virtual en $(VENV). Crea uno con: python -m venv $(VENV)" && exit 1 \
	)

check-env-file:
	@if not exist $(ENV_FILE) ( \
		echo "No existe $(ENV_FILE). Copia/crea el archivo antes de continuar." && exit 1 \
	)

preflight: check-venv check-env-file
	@echo "Usando DJANGO_ENV=$(DJANGO_ENV) -> $(ENV_FILE)"

install: check-venv
	@echo "Instalando dependencias..."
	@$(PYTHON) -m pip install --upgrade pip >nul
	@$(PYTHON) -m pip install -r $(REQUIREMENTS)
	@echo "Dependencias listas."

migrations: preflight
	@$(MANAGE) makemigrations

migrate: preflight
	@$(MANAGE) migrate

seed: preflight
	@$(MANAGE) run_sql --file=insert_dummy_data.sql

create-superuser: preflight
	@$(MANAGE) createsuperuser

shell: preflight
	@$(MANAGE) shell

run-server: preflight
	@echo "Aplicando migraciones pendientes..."
	@$(MANAGE) migrate
	@echo "Iniciando servidor de desarrollo..."
	@$(MANAGE) runserver 0.0.0.0:8000

# =============================================================================
# TESTING
# =============================================================================

# Ejecuta todos los tests con verbosidad basica
test: preflight
	@echo "Ejecutando todos los tests..."
	@$(MANAGE) test hades_app.tests --verbosity=1

# Tests con verbosidad media (muestra nombres de tests)
test-v: preflight
	@echo "Ejecutando tests con verbosidad media..."
	@$(MANAGE) test hades_app.tests --verbosity=2

# Tests con verbosidad alta (muestra todo el detalle)
test-vv: preflight
	@echo "Ejecutando tests con verbosidad alta..."
	@$(MANAGE) test hades_app.tests --verbosity=3

# Tests rapidos sin recrear la base de datos
test-fast: preflight
	@echo "Ejecutando tests (modo rapido, reutilizando DB)..."
	@$(MANAGE) test hades_app.tests --keepdb --verbosity=1

# Tests con reporte de cobertura (requiere coverage instalado)
test-coverage: preflight
	@echo "Ejecutando tests con cobertura..."
	@$(PYTHON) -m coverage run --source='hades_app' manage.py test hades_app.tests --verbosity=1
	@$(PYTHON) -m coverage report -m
	@$(PYTHON) -m coverage html
	@echo "Reporte HTML generado en htmlcov/index.html"

# Tests de un modulo especifico
# Uso: make test-module M=AuthenticationTests
# Uso: make test-module M=WorkOrderTests.test_create_work_order_with_user_id
M ?= ""
test-module: preflight
	@if "$(M)"=="" ( \
		echo "ERROR: Especifica el modulo con M=NombreDelTest" && \
		echo "Ejemplo: make test-module M=AuthenticationTests" && \
		exit 1 \
	)
	@echo "Ejecutando tests del modulo: $(M)"
	@$(MANAGE) test hades_app.tests.$(M) --verbosity=2

# =============================================================================
# DEPLOY
# =============================================================================

# Ejecuta tests y despliega a Cloud Run (usa deploy.ps1)
deploy: preflight
	@echo "Iniciando proceso de deploy..."
	@powershell -ExecutionPolicy Bypass -File .\deploy.ps1

# =============================================================================
# CALIDAD DE CODIGO
# =============================================================================

lint: check-venv
	@echo "Analizando código con pylint..."
	@$(PYTHON) -m pylint hades_app server manage.py

format: check-venv
	@echo "Formateando código con black..."
	@$(PYTHON) -m black hades_app server manage.py

clean:
	@echo "Limpiando archivos temporales..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
	@echo "Archivos temporales eliminados."

cloud-proxy:
	@if not exist $(CLOUD_SQL_CREDENTIALS) ( \
		echo "No se encontró $(CLOUD_SQL_CREDENTIALS)." && exit 1 \
	)
	@echo "Iniciando Cloud SQL Proxy -> $(CLOUD_SQL_INSTANCE) en puerto $(CLOUD_SQL_PORT)"
	@$(CLOUD_SQL_PROXY) -instances=$(CLOUD_SQL_INSTANCE)=tcp:$(CLOUD_SQL_PORT) -log_debug_stdout -credential_file=$(CLOUD_SQL_CREDENTIALS)