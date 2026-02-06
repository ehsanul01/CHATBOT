import firebase_admin
from firebase_admin import credentials, firestore

# Prevent "already initialized" when Streamlit reloads
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")  # make sure this file exists
    firebase_admin.initialize_app(cred)

db = firestore.client()