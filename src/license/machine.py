"""
Machine ID generation for license activation.
Generates a unique identifier based on hardware characteristics.
"""

import hashlib
import subprocess
import uuid
import platform

from src.utils.logger import logger


def get_machine_id() -> str:
    """
    Generate a unique machine identifier.

    Uses multiple hardware characteristics:
    1. CPU Serial Number
    2. Motherboard Serial Number
    3. MAC Address
    4. Hard Drive Serial Number (fallback)

    Returns:
        32-character MD5 hex string
    """
    components = []

    # 1. CPU Serial Number
    try:
        cpu = _run_wmic("cpu get processorid")
        if cpu and cpu != "None":
            components.append(f"cpu:{cpu.strip()}")
    except Exception:
        pass

    # 2. Motherboard Serial Number
    try:
        board = _run_wmic("baseboard get serialnumber")
        if board and board != "None" and "Default string" not in board:
            components.append(f"board:{board.strip()}")
    except Exception:
        pass

    # 3. MAC Address
    try:
        mac = hex(uuid.getnode())
        if mac and mac != "0x0":
            components.append(f"mac:{mac}")
    except Exception:
        pass

    # 4. Hard Drive Serial Number (fallback)
    try:
        disk = _run_wmic("diskdrive get serialnumber")
        if disk and disk != "None":
            components.append(f"disk:{disk.strip()}")
    except Exception:
        pass

    # 5. Hostname + Platform (last resort)
    if len(components) < 2:
        components.append(f"host:{platform.node()}")
        components.append(f"os:{platform.platform()}")

    # Combine and hash
    raw = "|".join(components)
    machine_id = hashlib.md5(raw.encode()).hexdigest()

    logger.debug(f"Machine ID generated from {len(components)} components")
    return machine_id


def _run_wmic(query: str) -> str:
    """Run a WMIC query and return the last line of output."""
    try:
        result = subprocess.run(
            ["wmic", *query.split()],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
            if platform.system() == "Windows" else 0,
        )
        # Parse output: take the last non-empty line
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if len(lines) > 1:
            return lines[-1]  # Last line is usually the value
        return ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""

