"""
Script para obtener o generar el token de un usuario existente.

Uso en LOCAL:
    venv\Scripts\python.exe get_token.py powerbi@natgas.com

Uso en PRODUCCION (con Cloud SQL Proxy corriendo):
    set DJANGO_ENV=prod
    venv\Scripts\python.exe get_token.py powerbi@natgas.com
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from hades_app.models import Users
from rest_framework.authtoken.models import Token

def get_user_token(email):
    """Obtiene o genera el token para un usuario."""

    try:
        # Buscar usuario
        user = Users.objects.get(email=email)

        # Crear o obtener el token
        token, created = Token.objects.get_or_create(user=user)

        print("\n" + "=" * 60)
        print(f"  TOKEN PARA: {email}")
        print("=" * 60)
        print(f"\nUsuario: {user.email}")
        print(f"Nombre: {user.name}")
        print(f"Token: {token.key}")
        print("\n" + "=" * 60)
        print("\nUsa este header en Postman:")
        print(f"Authorization: Token {token.key}")
        print("=" * 60 + "\n")

        if created:
            print("[INFO] Token generado (no existia previamente)\n")
        else:
            print("[INFO] Token existente recuperado\n")

    except Users.DoesNotExist:
        print(f"\n[ERROR] Usuario '{email}' no encontrado en la base de datos.\n")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\nUso: python get_token.py <email_del_usuario>")
        print("Ejemplo: python get_token.py powerbi@natgas.com\n")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    get_user_token(email)
