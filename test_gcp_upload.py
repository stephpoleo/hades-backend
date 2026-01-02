from google.cloud import storage
from google.oauth2 import service_account

# Ruta al archivo de credenciales (ajusta si es necesario)
CREDENTIALS_PATH = "hades-backend-prod.json"
BUCKET_NAME = "hades-media"
DEST_BLOB_NAME = "requirements.txt"
LOCAL_FILE = "requirements.txt"

# Crear un archivo de prueba
with open(LOCAL_FILE, "w") as f:
    f.write("Esto es una prueba de subida directa a GCP desde script Python.")

# Cargar credenciales
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)

# Inicializar cliente de storage
client = storage.Client(credentials=credentials)
bucket = client.bucket(BUCKET_NAME)
blob = bucket.blob(DEST_BLOB_NAME)

# Subir archivo
blob.upload_from_filename(LOCAL_FILE)
print(f"Archivo subido correctamente a gs://{BUCKET_NAME}/{DEST_BLOB_NAME}")
