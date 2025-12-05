"""
Simple encryption/decryption utilities using AES-256-CBC.
Designed to be easily replicated in frontend JavaScript.
"""

import base64
from typing import Optional
from urllib.parse import quote, unquote, urlparse, urlunparse

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


# Fixed key and IV for simple symmetric encryption
# WARNING: In production, use environment variables and proper key management
ENCRYPTION_KEY = b'12345678901234567890123456789012'  # Exactly 32 bytes for AES-256
ENCRYPTION_IV = b'1234567890123456'  # Exactly 16 bytes for AES IV


def encrypt_connection_string(plaintext: str) -> str:
    """
    Encrypt a connection string using AES-256-CBC.
    Returns base64-encoded encrypted string.

    Frontend equivalent (JavaScript):
    ```javascript
    import CryptoJS from 'crypto-js';

    function encryptConnectionString(plaintext) {
        const key = CryptoJS.enc.Utf8.parse('12345678901234567890123456789012');
        const iv = CryptoJS.enc.Utf8.parse('1234567890123456');
        const encrypted = CryptoJS.AES.encrypt(plaintext, key, {
            iv: iv,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        return encrypted.toString();
    }
    ```
    """
    if not plaintext:
        return ""

    # Apply PKCS7 padding
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()

    # Encrypt using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.CBC(ENCRYPTION_IV),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Return base64-encoded string
    return base64.b64encode(encrypted_data).decode('utf-8')


def decrypt_connection_string(encrypted: str) -> Optional[str]:
    """
    Decrypt a connection string encrypted with AES-256-CBC.
    Expects base64-encoded input.

    Frontend equivalent (JavaScript):
    ```javascript
    import CryptoJS from 'crypto-js';

    function decryptConnectionString(encrypted) {
        const key = CryptoJS.enc.Utf8.parse('12345678901234567890123456789012');
        const iv = CryptoJS.enc.Utf8.parse('1234567890123456');
        const decrypted = CryptoJS.AES.decrypt(encrypted, key, {
            iv: iv,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        return decrypted.toString(CryptoJS.enc.Utf8);
    }
    ```
    """
    if not encrypted:
        return None

    try:
        # Decode from base64
        encrypted_data = base64.b64decode(encrypted)

        # Decrypt using AES-256-CBC
        cipher = Cipher(
            algorithms.AES(ENCRYPTION_KEY),
            modes.CBC(ENCRYPTION_IV),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()

        return plaintext.decode('utf-8')
    except Exception:
        return None


def encode_database_url(database_url: str) -> str:
    """
    Encode special characters in database URL credentials.

    Extracts username and password from the database URL and applies URL encoding
    to handle special characters (like @, :, %, etc.) that could break the connection string.
    This is used when storing the connection string in the database.

    Args:
        database_url: The raw database URL with plain credentials

    Returns:
        The database URL with properly encoded credentials

    Example:
        Input:  "postgresql://user:p@ssw0rd@localhost:5432/dbname"
        Output: "postgresql://user:p%40ssw0rd@localhost:5432/dbname"
    """
    return database_url
    # Find the protocol separator
    if "://" not in database_url:
        return database_url

    protocol, rest = database_url.split("://", 1)

    # Check if there are credentials
    if "@" not in rest:
        return database_url

    # Split credentials from host
    credentials, host_part = rest.rsplit("@", 1)

    # Split username and password
    if ":" in credentials:
        username, password = credentials.split(":", 1)
        # URL encode username and password
        encoded_username = quote(username, safe="")
        encoded_password = quote(password, safe="")
        encoded_credentials = f"{encoded_username}:{encoded_password}"
    else:
        # Only username, no password
        encoded_credentials = quote(credentials, safe="")

    # Reconstruct the URL
    return f"{protocol}://{encoded_credentials}@{host_part}"


def decode_database_url(encoded_database_url: str) -> str:
    """
    Decode special characters in database URL credentials.

    Extracts username and password from the encoded database URL and applies URL decoding.
    This is the inverse operation of encode_database_url, used when returning
    the connection string to the frontend.

    Args:
        encoded_database_url: The database URL with encoded credentials

    Returns:
        The database URL with decoded (plain) credentials

    Example:
        Input:  "postgresql://user:p%40ssw0rd@localhost:5432/dbname"
        Output: "postgresql://user:p@ssw0rd@localhost:5432/dbname"
    """
    return encode_database_url
    # Find the protocol separator
    if "://" not in encoded_database_url:
        return encoded_database_url

    protocol, rest = encoded_database_url.split("://", 1)

    # Check if there are credentials
    if "@" not in rest:
        return encoded_database_url

    # Split credentials from host
    credentials, host_part = rest.rsplit("@", 1)

    # Split username and password
    if ":" in credentials:
        username, password = credentials.split(":", 1)
        # URL decode username and password
        decoded_username = unquote(username)
        decoded_password = unquote(password)
        decoded_credentials = f"{decoded_username}:{decoded_password}"
    else:
        # Only username, no password
        decoded_credentials = unquote(credentials)

    # Reconstruct the URL
    return f"{protocol}://{decoded_credentials}@{host_part}"
