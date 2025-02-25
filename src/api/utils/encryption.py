import os
from cryptography.fernet import Fernet
from api.settings import settings


def decrypt_openai_api_key(encrypted_api_key: str) -> str:
    cipher = Fernet(settings.openai_api_key_encryption_key)

    # fetched_encrypted_api_key is what you get from the DB
    return cipher.decrypt(encrypted_api_key).decode()


def encrypt_openai_api_key(api_key: str) -> str:
    cipher = Fernet(settings.openai_api_key_encryption_key)

    return cipher.encrypt(api_key.encode()).decode()
