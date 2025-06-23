from dotenv import load_dotenv
import os
from cryptography.fernet import Fernet

load_dotenv()  # load .env-data

FERNET_KEY = os.environ.get("FERNET_KEY")
if FERNET_KEY is None:
    raise ValueError("FERNET_KEY is not set in environment variables.")

fernet = Fernet(FERNET_KEY)


def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()
