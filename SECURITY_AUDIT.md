# Auditoría de Seguridad - Hades Backend

**Fecha:** 2026-02-17
**Estado:** Pendiente de implementación
**Prioridad:** CRÍTICA

---

## Resumen Ejecutivo

Se identificaron múltiples vulnerabilidades de seguridad que requieren atención antes de producción. Este documento sirve como plan de remediación.

| Severidad | Cantidad | Estado |
|-----------|----------|--------|
| CRÍTICA | 6 | Pendiente |
| ALTA | 8 | Pendiente |
| MEDIA | 5 | Pendiente |

---

## Estado de Remediación

### [COMPLETADO] Limpieza de Credenciales en Git

- [x] Archivos `.env`, `.env.dev`, `.env.prod`, `.env.docker` eliminados del historial
- [x] Usada herramienta `git filter-repo`
- [ ] **PENDIENTE: Rotar credenciales expuestas** (DB passwords, SECRET_KEY)
- [ ] **PENDIENTE: Force push al repositorio remoto**

---

## VULNERABILIDADES CRÍTICAS

### 1. Credenciales Expuestas en Historial de Git
**Estado:** Parcialmente resuelto
**Archivos afectados:** `.env`, `.env.dev`, `.env.prod`, `.env.docker`

**Credenciales que fueron expuestas:**
```
SECRET_KEY="g8awx^wbw^)fsx-&zj#duzyn**^!qhc-ynmneg4qt1syo!rx*s"
DB_PASSWORD=.Vx.0O|M8,y\n2=P
EDS_ERELIS_DB_PASSWORD=r3Wn82CZCemW62Z
```

**Acciones completadas:**
- [x] Eliminados archivos del historial con git filter-repo

**Acciones pendientes:**
- [ ] Rotar SECRET_KEY en producción
- [ ] Rotar DB_PASSWORD en Cloud SQL
- [ ] Rotar EDS_ERELIS_DB_PASSWORD en Azure
- [ ] Force push: `git push origin --force --all`
- [ ] Notificar a colaboradores que re-clonen

---

### 2. DEBUG=True en Producción
**Estado:** Pendiente
**Archivo:** `server/settings.py:174`

```python
# ACTUAL (VULNERABLE):
DEBUG = env("DEBUG", "true").lower() == "true"

# SOLUCIÓN:
DEBUG = env("DEBUG", "false").lower() == "true"
```

**Riesgo:** Expone stack traces, código fuente, y configuración en errores.

---

### 3. API Sin Autenticación (AllowAny)
**Estado:** Pendiente
**Archivo:** `server/settings.py:437-438`

```python
# ACTUAL (VULNERABLE):
"DEFAULT_PERMISSION_CLASSES": [
    "rest_framework.permissions.AllowAny",
]

# SOLUCIÓN:
"DEFAULT_PERMISSION_CLASSES": [
    "rest_framework.permissions.IsAuthenticated",
]
```

**Riesgo:** Todos los endpoints son accesibles sin autenticación.

---

### 4. Endpoints de Eliminación Masiva Sin Protección
**Estado:** Pendiente
**Archivo:** `hades_app/views.py:1299-1345`

**Endpoints vulnerables:**
- `DELETE /api/form-templates/clear-all/`
- `DELETE /api/work-orders/clear-all/`

```python
# SOLUCIÓN: Agregar decorador a cada endpoint
from rest_framework.permissions import IsAdminUser

@action(detail=False, methods=["delete"], url_path="clear-all")
@permission_classes([IsAdminUser])
def clear_all(self, request):
    # ... código existente
```

**Riesgo:** Cualquier usuario puede borrar toda la base de datos.

---

### 5. Path Traversal en Comando SQL
**Estado:** Pendiente
**Archivo:** `hades_app/management/commands/run_sql.py:20-38`

```python
# ACTUAL (VULNERABLE):
file_name = options["file"]
sql_file_path = os.path.join(settings.BASE_DIR, "sql", file_name)
# Permite: python manage.py run_sql --file ../../etc/passwd

# SOLUCIÓN:
ALLOWED_SQL_FILES = {'create_tables.sql', 'seed_data.sql'}

def handle(self, *args, **options):
    file_name = options["file"]
    if file_name not in ALLOWED_SQL_FILES:
        raise CommandError(f"Archivo no permitido: {file_name}")
    # ... resto del código
```

**Riesgo:** Lectura de archivos arbitrarios del sistema.

---

### 6. Ejecución de SQL Raw
**Estado:** Pendiente
**Archivo:** `hades_app/management/commands/run_sql.py:38`

**Recomendación:** Migrar a Django migrations en lugar de ejecutar SQL raw.

---

## VULNERABILIDADES ALTAS

### 7. Sin Rate Limiting en Login
**Estado:** Pendiente
**Archivo:** `hades_app/views.py:56-91`

```python
# SOLUCIÓN: Instalar django-ratelimit
# pip install django-ratelimit

from django_ratelimit.decorators import ratelimit

@api_view(["POST"])
@ratelimit(key='ip', rate='5/m', block=True)
def login_view(request):
    # ... código existente
```

**Riesgo:** Ataques de fuerza bruta ilimitados.

---

### 8. CSRF Cookie Accesible por JavaScript
**Estado:** Pendiente
**Archivo:** `server/settings.py:499`

```python
# ACTUAL (VULNERABLE):
CSRF_COOKIE_HTTPONLY = False

# SOLUCIÓN:
CSRF_COOKIE_HTTPONLY = True
```

**Riesgo:** Token CSRF puede ser robado via XSS.

---

### 9. Fallback de Autenticación
**Estado:** Pendiente
**Archivo:** `hades_app/views.py:77-83`

```python
# ACTUAL (RIESGOSO):
if user is None:
    candidate = Users.objects.filter(email__iexact=email).first()
    if candidate and candidate.check_password(password):
        user = candidate

# SOLUCIÓN: Eliminar fallback, usar solo Django authenticate()
```

**Riesgo:** Evade controles de seguridad del framework de autenticación.

---

### 10. Sin Control de Acceso Basado en Roles
**Estado:** Pendiente
**Archivos:** Todos los ViewSets en `hades_app/views.py`

**ViewSets sin protección:**
- `EDSViewSet` (línea 130)
- `UsersViewSet` (línea 371)
- `FormTemplateViewSet` (línea 668)
- `WorkOrderViewSet` (línea 700)
- `FormQuestionsViewSet` (línea 842)
- `FormAnswersViewSet` (línea 868)
- `RolesViewSet` (línea 1348)
- `PermissionsViewSet` (línea 1387)

```python
# SOLUCIÓN: Agregar permission_classes a cada ViewSet
class UsersViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # Para admin-only:
    # permission_classes = [IsAdminUser]
```

---

### 11. Validación de Archivos Débil
**Estado:** Pendiente
**Archivo:** `hades_app/views.py:963-997`

```python
# SOLUCIÓN: Validar tipo y tamaño
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_image(file_obj):
    if file_obj.size > MAX_FILE_SIZE:
        raise ValidationError("Archivo muy grande (máx 5MB)")
    if file_obj.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("Tipo de archivo no permitido")
```

---

### 12. Validación de Input Faltante
**Estado:** Pendiente
**Archivo:** `hades_app/views.py`

```python
# SOLUCIÓN para parámetros de fecha:
from datetime import datetime

start_date = request.query_params.get("start_date")
if start_date:
    try:
        start_date = datetime.fromisoformat(start_date).date()
    except ValueError:
        return Response({"error": "Formato de fecha inválido"}, status=400)
```

---

## VULNERABILIDADES MEDIAS

### 13. Session Cookie de 14 Días
**Estado:** Pendiente
**Archivo:** `server/settings.py:498`

```python
# ACTUAL:
SESSION_COOKIE_AGE = 1209600  # 14 días

# RECOMENDACIÓN:
SESSION_COOKIE_AGE = 86400  # 1 día
# O máximo:
SESSION_COOKIE_AGE = 604800  # 7 días
```

---

### 14. Credenciales GCP en /tmp
**Estado:** Pendiente
**Archivo:** `server/settings.py:39-70`

```python
# SOLUCIÓN: Limpiar archivo después de uso
import atexit

def cleanup_credentials():
    temp_path = "/tmp/gcp_storage_credentials.json"
    if os.path.exists(temp_path):
        os.remove(temp_path)

atexit.register(cleanup_credentials)
```

---

### 15. Logging de Datos Sensibles
**Estado:** Pendiente
**Archivos:** `server/settings.py:526-536`, `hades_app/views.py:63-68`

```python
# ELIMINAR estos logs:
logging.error(f"[GCP_STORAGE] GS_CREDENTIALS: {GS_CREDENTIALS}...")
logger.info("Login intento email=%s...", email)

# REEMPLAZAR con:
logger.info("Login attempt from IP: %s", request.META.get('REMOTE_ADDR'))
```

---

### 16. Orígenes CORS Locales en Producción
**Estado:** Pendiente
**Archivo:** `server/settings.py:469-507`

```python
# SOLUCIÓN: Separar por ambiente
if DEBUG:
    CORS_ALLOWED_ORIGINS += _LOCAL_ORIGINS
```

---

### 17. Mensajes de Error Exponen Información
**Estado:** Pendiente
**Archivo:** `hades_app/views.py` (múltiples)

```python
# ACTUAL (VULNERABLE):
return Response({"error": str(e)}, status=500)

# SOLUCIÓN:
logger.exception("Error interno")  # Log completo
return Response({"error": "Error interno del servidor"}, status=500)
```

---

## Plan de Implementación

### Fase 1: Inmediata (Antes de cualquier deploy)
1. [ ] Rotar todas las credenciales expuestas
2. [ ] Force push del historial limpio
3. [ ] Cambiar DEBUG default a "false"
4. [ ] Cambiar AllowAny a IsAuthenticated

### Fase 2: Alta Prioridad (Esta semana)
5. [ ] Proteger endpoints clear-all
6. [ ] Implementar rate limiting en login
7. [ ] Fijar CSRF_COOKIE_HTTPONLY = True
8. [ ] Eliminar fallback de autenticación

### Fase 3: Media Prioridad (Próximas 2 semanas)
9. [ ] Agregar permission_classes a todos los ViewSets
10. [ ] Implementar validación de archivos
11. [ ] Agregar validación de inputs
12. [ ] Reducir SESSION_COOKIE_AGE

### Fase 4: Mejoras (Próximo mes)
13. [ ] Limpiar credentials de /tmp
14. [ ] Sanitizar logs
15. [ ] Separar CORS por ambiente
16. [ ] Sanitizar mensajes de error

---

## Comandos de Verificación

```bash
# Verificar que .env no está en historial
git log --all --full-history -- ".env" ".env.prod"

# Verificar DEBUG está en false
grep -n "DEBUG" server/settings.py

# Verificar permisos por defecto
grep -n "AllowAny\|IsAuthenticated" server/settings.py

# Buscar endpoints sin protección
grep -n "def clear_all" hades_app/views.py
```

---

## Notas

- Este documento debe actualizarse conforme se resuelvan las vulnerabilidades
- Marcar cada item como [x] cuando esté completado
- Realizar pruebas después de cada cambio de seguridad
