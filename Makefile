# Makefile para el proyecto Hades Backend
# Ejecuta todas las instrucciones necesarias en orden

.PHONY: help install activate setup-db run-server clean clean-db drop-tables reset-db all

# Variables
PYTHON = python
VENV = venv
VENV_SCRIPTS = $(VENV)\Scripts
REQUIREMENTS = requirements.txt

# Comando por defecto
all: help

# Mostrar ayuda
help:
	@echo "Comandos disponibles:"
	@echo "  make install     - Instalar dependencias"
	@echo "  make setup-db    - Crear y configurar la base de datos"
	@echo "  make run-server  - Ejecutar el servidor de desarrollo"
	@echo "  make clean       - Limpiar archivos temporales"
	@echo "  make clean-db    - Limpiar datos de la base de datos (mantiene tablas)"
	@echo "  make drop-tables - Borrar todas las tablas completamente"
	@echo "  make all-setup   - Ejecutar instalación completa"
	@echo "  make reset-db    - Reiniciar la base de datos"

# Verificar que existe el entorno virtual
check-venv:
	@if not exist $(VENV) ( \
		echo "Error: No se encontró el entorno virtual. Crea uno con: python -m venv venv" && \
		exit 1 \
	)

# Instalar dependencias
install: check-venv
	@echo "Instalando dependencias..."
	@call $(VENV_SCRIPTS)\activate.bat & pip install -r $(REQUIREMENTS)
	@echo "Dependencias instaladas correctamente."

# Configurar la base de datos
setup-db: check-venv
	@echo "Configurando la base de datos..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py makemigrations
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py migrate
	@echo "Ejecutando script de creación de tablas..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py run_sql --file=create_tables.sql
	@echo "Insertando datos dummy..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py run_sql --file=insert_dummy_data.sql
	@echo "Base de datos configurada correctamente."

# Limpiar base de datos completamente
clean-db: check-venv
	@echo "Limpiando datos de la base de datos (manteniendo estructura de tablas)..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py run_sql --file=clean_database.sql
	@echo "Datos de la base de datos limpiados. Las tablas se mantienen vacías."

# Borrar todas las tablas completamente
drop-tables: check-venv
	@echo "CUIDADO: Borrando TODAS las tablas de la base de datos..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py run_sql --file=drop_tables.sql
	@echo "Todas las tablas han sido eliminadas completamente."

# Reiniciar la base de datos
reset-db: check-venv
	@echo "Reiniciando la base de datos..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py flush --noinput
	@echo "Ejecutando script de creación de tablas..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py run_sql --file=create_tables.sql
	@echo "Insertando datos dummy..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py run_sql --file=insert_dummy_data.sql
	@echo "Base de datos reiniciada correctamente."

# Crear superusuario
create-superuser: check-venv
	@echo "Creando superusuario..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py createsuperuser

# Ejecutar servidor de desarrollo
run-server: check-venv
	@echo "Iniciando servidor de desarrollo..."
	@call $(VENV_SCRIPTS)\activate.bat & $(PYTHON) manage.py runserver

# Limpiar archivos temporales
clean:
	@echo "Limpiando archivos temporales..."
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
	@echo "Archivos temporales eliminados."

# Configuración completa (desde cero)
all-setup: check-venv install setup-db
	@echo "Configuración completa terminada."
	@echo "Para crear un superusuario ejecuta: make create-superuser"
	@echo "Para iniciar el servidor ejecuta: make run-server"

# Desarrollo - reiniciar todo
dev-reset: clean reset-db
	@echo "Entorno de desarrollo reiniciado."