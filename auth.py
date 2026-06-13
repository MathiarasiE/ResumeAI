import secrets
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Hardcoded credentials — change these as needed
CREDENTIALS = {
    os.getenv("APP_USERNAME", "admin"): os.getenv("APP_PASSWORD", "admin123"),
}

# In-memory token store
_valid_tokens: set[str] = set()


def login(username: str, password: str) -> Optional[str]:
    if CREDENTIALS.get(username) == password:
        token = secrets.token_urlsafe(32)
        _valid_tokens.add(token)
        return token
    return None


def verify(token: str) -> bool:
    return token in _valid_tokens


def logout(token: str):
    _valid_tokens.discard(token)
