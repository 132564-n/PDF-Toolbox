"""
Build script — Package PDF Toolbox into a distributable Windows executable.

Usage:
    python scripts/build.py

Requirements:
    pip install pyinstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
OUTPUT_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
APP_NAME = "PDFToolbox"
ENTRY_POINT = SRC_DIR / "main.py"
ICON_PATH = PROJECT_ROOT / "resources" / "icons" / "app.ico"


def clean_build_dirs():
    """Remove previous build artifacts."""
    for d in [OUTPUT_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Cleaned: {d}")


def check_icon():
    """Create a default icon if none exists."""
    if not ICON_PATH.exists():
        # Generate a simple .ico using Pillow (if available)
        try:
            from PIL import Image
            ICON_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Create a simple 256x256 blue square as fallback icon
            img = Image.new('RGBA', (256, 256), (30, 102, 245, 255))
            img.save(ICON_PATH)
            print(f"  Generated default icon: {ICON_PATH}")
        except ImportError:
            print("  Warning: Pillow not installed, skipping icon generation")
            return False
    return True


def build():
    """Run PyInstaller to build the executable."""
    print("=" * 60)
    print("  PDF Toolbox — Build Script")
    print("=" * 60)

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"  PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("  Error: PyInstaller not installed. Run: pip install pyinstaller")
        sys.exit(1)

    # Clean previous builds
    print("\n[1/4] Cleaning previous builds...")
    clean_build_dirs()

    # Check / generate icon
    print("\n[2/4] Checking icon...")
    has_icon = check_icon()

    # Build command
    print("\n[3/4] Building executable...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onedir",  # One folder mode (faster startup than --onefile)
        "--windowed",  # No console window
        "--clean",
        "--noconfirm",
        f"--distpath={OUTPUT_DIR}",
        f"--workpath={BUILD_DIR}",
        "--add-data", f"{SRC_DIR / 'ui' / 'styles'};src/ui/styles",
    ]

    if has_icon:
        cmd.extend(["--icon", str(ICON_PATH)])

    # Hidden imports (some libraries need explicit inclusion)
    hidden_imports = [
        "pypdf", "pdfplumber", "pdf2docx", "reportlab",
        "PIL", "PIL._imagingtk", "PIL._tkinter_finder",
        "cryptography", "loguru",
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Exclude unnecessary modules to reduce size
    exclude_modules = [
        "tkinter", "matplotlib", "scipy", "numpy",
        "IPython", "jupyter", "notebook",
        "pandas", "sqlalchemy", "flask", "django",
    ]
    for mod in exclude_modules:
        cmd.extend(["--exclude-module", mod])

    cmd.append(str(ENTRY_POINT))

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("\n  Build FAILED!")
        sys.exit(1)

    print(f"\n[4/4] Build complete!")
    print(f"  Output: {OUTPUT_DIR / APP_NAME}")
    print(f"  Executable: {OUTPUT_DIR / APP_NAME / f'{APP_NAME}.exe'}")

    # Print size
    exe_path = OUTPUT_DIR / APP_NAME / f"{APP_NAME}.exe"
    if exe_path.exists():
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"  EXE Size: {size_mb:.1f} MB")

    print("\n  Next: Use Inno Setup to create an installer.")
    print("=" * 60)


if __name__ == "__main__":
    build()

