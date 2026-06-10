"""
Activation Code Generator — Run locally to generate license keys for customers.

Usage:
    python scripts/gen_license.py <machine_id>

Or interactively:
    python scripts/gen_license.py

Requirements:
    - private_key.pem (generated using openssl)
    - pip install cryptography
"""

import sys
import os
import json
import base64
from datetime import datetime
from pathlib import Path

import secrets
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


# Path to private key (KEEP THIS SAFE — NEVER DISTRIBUTE!)
PRIVATE_KEY_PATH = Path(__file__).parent / "private_key.pem"


def load_private_key() -> bytes:
    """Load the RSA private key."""
    if not PRIVATE_KEY_PATH.exists():
        print(f"\n❌ Private key not found: {PRIVATE_KEY_PATH}")
        print("\nGenerate your key pair first:")
        print("  openssl genpkey -algorithm RSA -out private_key.pem "
              "-pkeyopt rsa_keygen_bits:2048")
        print("  openssl rsa -pubout -in private_key.pem -out public_key.pem")
        sys.exit(1)

    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def generate_license(machine_id: str) -> str:
    """
    Generate an activation code for a given machine ID.

    Args:
        machine_id: 32-character MD5 hex machine identifier

    Returns:
        Formatted activation code (PDFTB-XXXXX-XXXXX-XXXXX-XXXXX)
    """
    private_key = load_private_key()

    # 1. Build payload
    payload = {
        "mid": machine_id,
        "ver": 1,
        "feat": ["all"],
        "iat": datetime.utcnow().isoformat(),
        "exp": None,  # None = lifetime license
        "non": secrets.token_hex(3),
    }

    # 2. Serialize to compact JSON
    data = json.dumps(payload, separators=(",", ":")).encode()

    # 3. Sign with private key
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

    # 4. Combine data + signature, Base32 encode
    combined = data + b"||" + signature
    encoded = base64.b32encode(combined).decode().rstrip("=")

    # 5. Format with product prefix and separators
    formatted = "PDFTB-" + "-".join(
        encoded[i:i+5] for i in range(0, len(encoded), 5)
    )

    return formatted


def main():
    """Interactive license generation."""
    print("=" * 60)
    print("  PDF Toolbox — Activation Code Generator")
    print("=" * 60)
    print()

    # Get machine ID
    if len(sys.argv) > 1:
        machine_id = sys.argv[1].strip()
    else:
        machine_id = input("请输入用户的机器码 (32位MD5): ").strip()

    # Validate
    if not machine_id or len(machine_id) != 32:
        print("\n❌ 错误：机器码必须是32位MD5字符串")
        sys.exit(1)

    if not all(c in "0123456789abcdef" for c in machine_id.lower()):
        print("\n⚠️  警告：机器码格式可能不正确，继续生成吗？(y/n)", end=" ")
        if input().strip().lower() != "y":
            sys.exit(0)

    # Generate
    print("\n⏳ 正在生成激活码...")
    try:
        license_key = generate_license(machine_id)
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        sys.exit(1)

    # Output
    print("\n" + "=" * 60)
    print(f"  ✅ 激活码已生成")
    print("=" * 60)
    print(f"\n  📋 激活码: {license_key}")
    print(f"  🖥️  机器码: {machine_id}")
    print(f"  📅 日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  ⏰ 有效期: 终身")
    print()
    print("  将以上激活码复制发送给用户即可。")
    print("  记得在 CSV 中记录：日期, 买家, 机器码, 激活码")
    print("=" * 60)


if __name__ == "__main__":
    main()

