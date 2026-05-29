"""
Security Utilities - AES-256 Encryption
========================================
Encrypts/decrypts user API keys. Keys are encrypted at rest in the DB
and only decrypted temporarily in RAM during API calls.
"""
import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from utils.logger import get_logger

logger = get_logger(__name__)

# Master encryption key - derived from env or generated on first run
# In production, use a hardware security module (HSM) or vault
_MASTER_KEY: Optional[bytes] = None


def _derive_key(secret: str, salt: bytes = None) -> bytes:
    """Derive a Fernet-compatible key from a secret string using PBKDF2"""
    if salt is None:
        salt = b"ai-cyber-trader-salt-2024"  # Fixed salt for reproducibility
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key


def _get_fernet() -> Fernet:
    """Get or create the Fernet cipher instance"""
    global _MASTER_KEY
    if _MASTER_KEY is None:
        # Use config if available, fall back to env var
        try:
            from config import config
            secret = config.ai.encryption_secret
        except Exception:
            secret = os.getenv(
                "ENCRYPTION_SECRET",
                "ai-cyber-trader-default-secret-change-in-production"
            )
        _MASTER_KEY = _derive_key(secret)
        logger.info("Encryption cipher initialized (AES-256/Fernet)")
    return Fernet(_MASTER_KEY)


def encrypt_api_key(plaintext: str) -> str:
    """
    Encrypt an API key with AES-256.
    
    Args:
        plaintext: The raw API key string
        
    Returns:
        Base64-encoded encrypted string (safe for DB storage)
    """
    if not plaintext:
        return ""
    try:
        f = _get_fernet()
        encrypted = f.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return ""


def decrypt_api_key(encrypted: str) -> str:
    """
    Decrypt an API key - ONLY use in RAM temporarily.
    Never log or store the decrypted value.
    
    Args:
        encrypted: The encrypted base64 string from DB
        
    Returns:
        Decrypted plaintext API key
    """
    if not encrypted:
        return ""
    try:
        f = _get_fernet()
        decrypted = f.decrypt(encrypted.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return ""


def mask_key(key: str, visible: int = 6) -> str:
    """Mask an API key for display: sk-12ab...xyz"""
    if len(key) <= visible * 2:
        return "*" * len(key)
    return key[:visible] + "..." + key[-4:]


def hash_key_for_audit(key: str) -> str:
    """
    Create a non-reversible hash of a key for audit logs.
    This allows checking if a key changed without storing the key itself.
    """
    return hashlib.sha256(key.encode()).hexdigest()[:16]
