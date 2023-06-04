from cryptography.fernet import Fernet
from django.conf import settings

f = Fernet(settings.API_KEY_STORAGE_KEY)
   
def encrypt_key(key):
    return f.encrypt(bytes(key, 'utf-8'))

def decrypt_key(key):
    return f.decrypt(bytes(key, 'utf-8'))
