from firebase_admin import credentials, firestore, initialize_app

cred = credentials.Certificate('./socratic.json')  
initialize_app(cred)

db = firestore.client()

__all__ = ['db']