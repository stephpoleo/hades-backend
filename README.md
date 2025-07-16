# Hades Backend

API REST backend desarrollada con Django y Django REST Framework para el proyecto Hades.

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

### Desarrollo

Para ejecutar el servidor de desarrollo:

```bash
python manage.py runserver
```

La API estará disponible en: `http://localhost:8000/`

### Panel de administración

Accede al panel de administración en: `http://localhost:8000/admin/`

### API Endpoints

La documentación de la API estará disponible en:

- `http://localhost:8000/api/` - Endpoints principales
- `http://localhost:8000/admin/` - Panel de administración

## 📁 Estructura del proyecto

```
hades-backend/
├── manage.py                 # Comando principal de Django
├── requirements.txt          # Dependencias del proyecto
├── .env.example             # Ejemplo de variables de entorno
├── README.md                # Este archivo
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
    ├── serializers.py      # Serializadores (crear)
    ├── urls.py             # URLs de la app (crear)
    └── admin.py            # Configuración admin
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

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## 📞 Soporte

Para reportar problemas o solicitar ayuda:

- Crea un issue en GitLab
- Contacta al equipo de desarrollo

## 🗺️ Roadmap

- [ ] Implementar autenticación JWT
- [ ] Agregar tests unitarios
- [ ] Implementar logging avanzado
- [ ] Configurar CI/CD
- [ ] Documentación de API con Swagger

## 👥 Autores

- **Equipo NatGas TI** - Desarrollo inicial

## 📄 Licencia

Este proyecto es propietario de NatGas.

## 📊 Estado del proyecto

🚧 **En desarrollo activo** - Este proyecto está siendo desarrollado activamente.
