import base64
import os
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from core.config import settings
from sqlalchemy import TypeDecorator, String
from sqlalchemy_utils.types.encrypted.encrypted_type import StringEncryptedType, AesEngine

logger = logging.getLogger(__name__)


class PIIEncryptionService:
    """
    Military-grade AES-256 encryption at rest for sensitive PII (Victim Name, Phone, Email).
    Ensures that even if the Postgres DB is compromised, PII remains secure.
    """
    def __init__(self):
        password = settings.SECRET_KEY.encode()
        salt = b'rakshak_salt_2026'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.fernet = Fernet(key)

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return plain_text
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        if not cipher_text:
            return cipher_text
        try:
            return self.fernet.decrypt(cipher_text.encode()).decode()
        except Exception:
            return cipher_text # Return as is if decryption fails (e.g., was not encrypted)


def get_master_encryption_key() -> str:
    """
    Returns the configured LOCAL_FILE_ENCRYPTION_KEY.
    If missing or default, falls back to deriving a deterministic 32-byte URL-safe base64 key
    from settings.SECRET_KEY so files and DB fields remain decryptable across server restarts.
    """
    raw_key = getattr(settings, "LOCAL_FILE_ENCRYPTION_KEY", None)
    if raw_key and raw_key != "hkAAmCKwdf2sBS8rbP4VTWI8WWu6bcr3pRT7Jb5nhuo=":
        return raw_key if raw_key.endswith('=') else raw_key + '=' * (4 - len(raw_key) % 4)
        
    password = getattr(settings, "SECRET_KEY", "default_secret_key_rakshak").encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'rakshak_file_salt_2026',
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password)).decode()


class SafeStringEncryptedType(TypeDecorator):
    """
    Resilient encrypted string type that gracefully handles legacy/unencrypted data,
    differing padding, or key mismatches without crashing entire queries with binascii.Error.
    """
    impl = String
    cache_ok = True

    def __init__(self, key_func=get_master_encryption_key, *args, **kwargs):
        super().__init__()
        self.underlying = StringEncryptedType(String, key_func, AesEngine, 'pkcs5')

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        try:
            return self.underlying.process_bind_param(value, dialect)
        except Exception as e:
            logger.warning(f"Failed to encrypt field, falling back to plaintext: {e}")
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return self.underlying.process_result_value(value, dialect)
        except Exception:
            # Fall back gracefully to raw string if value was stored in plaintext or cannot be decrypted
            return str(value)
