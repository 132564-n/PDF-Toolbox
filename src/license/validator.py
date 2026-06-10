"""
License validation for PDF Toolbox.
Offline RSA signature verification + machine ID binding.
"""

import json
import base64
from pathlib import Path
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from .machine import get_machine_id
from src.utils.logger import logger

# ============================================================
# PUBLIC KEY — This is embedded in the distributed software.
# The corresponding PRIVATE KEY is kept ONLY by the developer.
#
# IMPORTANT: To generate your own key pair, run:
#   openssl genpkey -algorithm RSA -out private_key.pem \
#       -pkeyopt rsa_keygen_bits:2048
#   openssl rsa -pubout -in private_key.pem -out public_key.pem
# ============================================================

# Default placeholder public key — REPLACE WITH YOUR REAL PUBLIC KEY
_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArK8Kk7G0R3LG6vJl7fVL
FHvQ2FjNqfhxMNXGKJYhRqFPVNLGgXN1qWfJN5qXkMZSmDqMqP0RxVhGRqGkOj0B
pLmXqN4Q6pKzL9nR3rFtGyMwX5k7Sv8kJtPqHvRkW2MxBhN6xCvDpR3QvBnQtWN8
LkWmGpZqX5zN9mRfKqJvPxVwWQK8mZpHkR3TqBmXwCqNmDkLpR8vQzHxWJkZmXq
NpR5kKwQx8vJmHqXnZpRkWkLzNmXpQZqRJvHkQ8vXqZmZkWJxRpRmN8vQpHZkQzX
LqWmXnXpZmZkWJqRpZkLzNmXpQ8vXqZmZkWJxRpRmN8vQpHZkQzXLqWmXnXpZmZk
WJqRpZkLzNmXpQ8vXqZmZkWJxRpRmN8vQpHZkQzXLqWmXnXpZmZkWJqRpZkLzNmX
pQIDAQAB
-----END PUBLIC KEY-----"""


def validate_license(license_key: str, machine_id: str = None) -> dict:
    """
    Validate an activation code.

    Args:
        license_key: The activation code (format: PDFTB-XXXXX-...)
        machine_id: Current machine ID (if None, auto-detect)

    Returns:
        dict with keys:
            valid (bool): Whether the license is valid
            message (str): Human-readable result message
            payload (dict, optional): License data if valid
    """
    if machine_id is None:
        machine_id = get_machine_id()

    # 1. Clean up license key
    code = license_key.replace("PDFTB-", "").replace("-", "").strip().upper()

    # 2. Base32 decode
    padding_len = 8 - len(code) % 8
    if padding_len != 8:
        code += "=" * padding_len

    try:
        combined = base64.b32decode(code)
    except Exception:
        logger.warning("License key format error (base32 decode failed)")
        return {"valid": False, "message": "激活码格式错误，请检查是否完整复制"}

    # 3. Split data and signature
    separator_pos = combined.find(b"||")
    if separator_pos == -1:
        logger.warning("License key format error (no separator)")
        return {"valid": False, "message": "激活码格式错误"}

    data = combined[:separator_pos]
    signature = combined[separator_pos + 2:]

    # 4. Verify RSA signature
    try:
        public_key = serialization.load_pem_public_key(_PUBLIC_KEY_PEM)
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except InvalidSignature:
        logger.warning("License signature verification failed")
        return {"valid": False, "message": "激活码无效，签名验证失败"}
    except Exception as e:
        logger.error(f"License verification error: {e}")
        return {"valid": False, "message": "激活验证异常，请重试"}

    # 5. Parse payload and verify machine ID
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return {"valid": False, "message": "激活码数据损坏"}

    if payload.get("mid") != machine_id:
        logger.warning(
            f"Machine ID mismatch: "
            f"expected={payload.get('mid')[:8]}..., "
            f"actual={machine_id[:8]}..."
        )
        return {"valid": False, "message": "激活码与当前设备不匹配，请重新获取"}

    # 6. Check expiration
    exp_str = payload.get("exp")
    if exp_str:
        try:
            exp_time = datetime.fromisoformat(exp_str)
            if datetime.utcnow() > exp_time:
                return {"valid": False, "message": "激活码已过期"}
        except (ValueError, TypeError):
            pass

    logger.info("License validated successfully")
    return {"valid": True, "message": "激活成功", "payload": payload}


def save_activation(license_key: str, machine_id: str = None):
    """
    Save activation state to local file.

    Args:
        license_key: Valid activation code
        machine_id: Machine ID (auto-detect if None)
    """
    if machine_id is None:
        machine_id = get_machine_id()

    data_dir = Path.home() / "AppData" / "Roaming" / "PDFToolbox"
    data_dir.mkdir(parents=True, exist_ok=True)

    data = json.dumps({
        "lk": license_key,
        "mi": machine_id,
        "ts": datetime.utcnow().isoformat(),
    })
    encoded = base64.b64encode(data.encode()).decode()

    with open(data_dir / "activation.dat", "w") as f:
        f.write(encoded)

    logger.info("Activation state saved")


def check_activation() -> bool:
    """
    Check if the software is activated.

    Returns True if a valid activation is found.

    Note: This is called at startup. If True, the main window
    opens normally. If False, the activation dialog is shown.
    """
    data_file = (
        Path.home() / "AppData" / "Roaming" /
        "PDFToolbox" / "activation.dat"
    )

    if not data_file.exists():
        logger.debug("No activation file found")
        return False

    try:
        with open(data_file) as f:
            encoded = f.read()

        data = json.loads(base64.b64decode(encoded))
        license_key = data.get("lk", "")
        saved_mid = data.get("mi", "")
        current_mid = get_machine_id()

        # Check if machine changed
        if saved_mid != current_mid:
            logger.warning("Machine ID changed — activation invalidated")
            return False

        # Re-validate license
        result = validate_license(license_key, current_mid)
        if not result["valid"]:
            logger.warning(f"Stored license invalid: {result['message']}")
            return False

        return True

    except Exception as e:
        logger.error(f"Activation check failed: {e}")
        return False

