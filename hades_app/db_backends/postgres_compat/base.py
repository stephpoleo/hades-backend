from django.db.backends.postgresql.base import (
    DatabaseWrapper as PostgresDatabaseWrapper,
)


class DatabaseWrapper(PostgresDatabaseWrapper):
    """Permite conectarse a instancias PostgreSQL < 14 (solo lectura)."""

    def check_database_version_supported(self):
        # Omite la validación estricta de versión que trae Django 5.2
        return
