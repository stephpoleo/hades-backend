# Makefile utilitario para el backend de Hades
# Enfocado en tareas usadas diariamente y con soporte a DJANGO_ENV

.PHONY: help preflight check-venv check-env-file install migrations migrate seed create-superuser shell run-server test

VENV := venv
PYTHON := $(VENV)\Scripts\python.exe
REQUIREMENTS := requirements.txt
DJANGO_ENV ?= prod
EDS_PROFILE ?= erelis
ENV_FILE := .env.$(DJANGO_ENV)
SET_ENV := set DJANGO_ENV=$(DJANGO_ENV) & set EDS_PROFILE=$(EDS_PROFILE) &
MANAGE := $(SET_ENV) $(PYTHON) manage.py

help:
	@echo "Comandos disponibles (DJANGO_ENV=$(DJANGO_ENV) / EDS_PROFILE=$(EDS_PROFILE)):"
	@echo "  make install          - Instala/actualiza dependencias"
	@echo "  make migrations       - Genera migraciones"
	@echo "  make migrate          - Aplica migraciones"
	@echo "  make seed             - Inserta datos dummy"
	@echo "  make create-superuser - Crea un superusuario"
	@echo "  make shell            - Abre la shell de Django"
	@echo "  make run-server       - Aplica migraciones y levanta el server"
	@echo "  make test             - Ejecuta pruebas"
	@echo "Puedes cambiar el entorno con: make run-server DJANGO_ENV=prod"
	@echo "Puedes alternar EDS con:    make run-server EDS_PROFILE=oasis"

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

test: preflight
	@$(MANAGE) test