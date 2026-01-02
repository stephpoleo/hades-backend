from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Ejecuta un archivo SQL personalizado"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="create_tables.sql",
            help="Nombre del archivo SQL a ejecutar (debe estar en la carpeta sql/)",
        )

    def handle(self, *args, **options):
        file_name = options["file"]
        sql_file_path = os.path.join(settings.BASE_DIR, "sql", file_name)

        if not os.path.exists(sql_file_path):
            self.stdout.write(self.style.ERROR(f"El archivo {sql_file_path} no existe"))
            return

        try:
            with open(sql_file_path, "r", encoding="utf-8") as file:
                sql_content = file.read()

            with connection.cursor() as cursor:
                sql_commands = [
                    cmd.strip() for cmd in sql_content.split(";") if cmd.strip()
                ]

                for command in sql_commands:
                    if command:
                        self.stdout.write(f"Ejecutando: {command[:50]}...")
                        cursor.execute(command)

            self.stdout.write(
                self.style.SUCCESS(f"Archivo SQL {file_name} ejecutado exitosamente")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error al ejecutar el archivo SQL: {str(e)}")
            )
