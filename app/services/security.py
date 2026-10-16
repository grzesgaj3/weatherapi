import hashlib
import secrets

from app.config import settings


def generate_api_key() -> str:
    """Losowy klucz API stacji (pokazywany wyłącznie raz)."""
    return secrets.token_hex(32)


def hash_api_key(api_key: str) -> str:
    """SHA-256 klucza API. Klucze mają wysoką entropię, więc nie używamy soli."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_admin_token(token: str) -> bool:
    """Porównanie w stałym czasie z sekretem admina."""
    return secrets.compare_digest(token, settings.ADMIN_TOKEN)
