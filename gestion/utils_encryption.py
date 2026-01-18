"""
Utilidades para encriptación de datos sensibles.
Usa Fernet (symmetric encryption) de la librería cryptography.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env (si existe)
try:
    from decouple import config as env_config
    USE_DECOUPLE = True
except ImportError:
    try:
        from dotenv import load_dotenv
        # Cargar .env desde el directorio raíz del proyecto
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        load_dotenv(BASE_DIR / '.env')
        USE_DECOUPLE = False
    except ImportError:
        USE_DECOUPLE = False


def get_encryption_key():
    """
    Obtiene o genera la clave de encriptación desde variables de entorno.
    
    Si ENCRYPTION_KEY no está configurada, genera una basada en SECRET_KEY.
    Esto permite compatibilidad hacia atrás pero es menos seguro.
    
    Returns:
        bytes: Clave de encriptación Fernet
    """
    if USE_DECOUPLE:
        encryption_key = env_config('ENCRYPTION_KEY', default=None)
    else:
        encryption_key = os.environ.get('ENCRYPTION_KEY')
    
    if encryption_key:
        try:
            return encryption_key.encode()
        except Exception as e:
            logger.error(f"Error procesando ENCRYPTION_KEY: {e}")
            raise ValueError("ENCRYPTION_KEY inválida")
    
    # Fallback: generar clave desde SECRET_KEY (menos seguro pero funcional)
    secret_key = settings.SECRET_KEY
    if not secret_key or secret_key.startswith('django-insecure'):
        raise ValueError(
            "ENCRYPTION_KEY debe estar configurada en variables de entorno. "
            "No se puede usar SECRET_KEY por defecto en producción."
        )
    
    # Generar clave desde SECRET_KEY usando PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'contratos_salt_fixed',  # Salt fijo para consistencia
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return key


def encrypt_value(plain_text: str) -> str:
    """
    Encripta un valor de texto plano.
    
    Args:
        plain_text: Texto a encriptar
        
    Returns:
        str: Texto encriptado (base64)
        
    Raises:
        ValueError: Si no se puede obtener la clave de encriptación
    """
    if not plain_text:
        return plain_text
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(plain_text.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Error encriptando valor: {e}", exc_info=True)
        raise ValueError(f"Error al encriptar: {str(e)}")


def decrypt_value(encrypted_text: str) -> str:
    """
    Desencripta un valor encriptado.
    
    Args:
        encrypted_text: Texto encriptado (base64)
        
    Returns:
        str: Texto desencriptado
        
    Raises:
        ValueError: Si no se puede desencriptar
    """
    if not encrypted_text:
        return encrypted_text
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_text.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Error desencriptando valor: {e}", exc_info=True)
        raise ValueError(f"Error al desencriptar: {str(e)}")


def generate_encryption_key() -> str:
    """
    Genera una nueva clave de encriptación Fernet.
    
    Returns:
        str: Clave generada (base64)
        
    Uso:
        python -c "from gestion.utils_encryption import generate_encryption_key; print(generate_encryption_key())"
    """
    key = Fernet.generate_key()
    return key.decode()

