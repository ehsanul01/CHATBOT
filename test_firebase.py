from firebase_config import db

db.collection("test").add({"message": "Firebase connected!"})

print(" Firestore is working!")