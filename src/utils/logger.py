"""
Logging configuration for PDF Toolbox.
Uses loguru for clean, colorful logging output.
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(log_dir: str = None, level: str = "INFO"):
    """
    Configure logging for the application.

    Args:
        log_dir: Directory for log files. Defaults to %APPDATA%/PDFToolbox/logs
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default handler
    logger.remove()

    # Determine log directory
    if log_dir is None:
        log_dir = Path.home() / "AppData" / "Roaming" / "PDFToolbox" / "logs"
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Console output (colored, compact)
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        ),
        level=level,
        colorize=True,
    )

    # File output (detailed, rotating)
    logger.add(
        log_dir / "pdf_toolbox_{time:YYYY-MM-DD}.log",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )

    # Error log file (only errors, kept longer)
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{name}:{function}:{line} | "
            "{message}\n{exception}"
        ),
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        encoding="utf-8",
    )

    return logger


# Default initialization
logger = setup_logging()

