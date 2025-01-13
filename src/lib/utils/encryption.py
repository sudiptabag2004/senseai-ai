import os
from cryptography.fernet import Fernet


def decrypt_openai_api_key(encrypted_api_key: str) -> str:
    cipher = Fernet(os.environ.get("OPENAI_API_KEY_ENCRYPTION_KEY"))

    # fetched_encrypted_api_key is what you get from the DB
    return cipher.decrypt(encrypted_api_key).decode()


def encrypt_openai_api_key(api_key: str) -> str:
    cipher = Fernet(os.environ.get("OPENAI_API_KEY_ENCRYPTION_KEY"))

    return cipher.encrypt(api_key.encode()).decode()
