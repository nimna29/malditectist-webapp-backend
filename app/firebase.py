import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import storage
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from the .env file


# Get vavlues from environment variables
service_account_data = {
    "type": "service_account",
    "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
    "auth_uri": os.environ.get("FIREBASE_AUTH_URI"),
    "token_uri": os.environ.get("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL"),
}

# Initialize the Firebase app with the service account credentials
cred = credentials.Certificate(service_account_data)
firebase_admin.initialize_app(cred, {
    'storageBucket': os.environ.get("FIREBASE_STORAGE_BUCKET")
})

# Get a reference to the default bucket
bucket = storage.bucket()

# Check if the bucket exists and connection
if bucket.exists():
    print('Firebase Storage connected successfully!')
else:
    print('Error connecting to Firebase Storage.')
