"""
PDF processing modules.

Each module handles a specific category of PDF operations:
- Converter: PDF to/from other formats
- Editor: Merge, split, rotate, reorder pages
- Compressor: Size reduction and optimization
- Security: Encryption and decryption
- Watermark: Text and image watermarks
- Extractor: Extract text, images, tables
"""

from .base import BaseModule, ModuleSettingsPanel
from .editor import EditorModule
from .converter import ConverterModule
from .compressor import CompressorModule
from .security import SecurityModule
from .watermark import WatermarkModule

# Register all available modules
MODULES = {
    "editor": EditorModule,
    "converter": ConverterModule,
    "compressor": CompressorModule,
    "security": SecurityModule,
    "watermark": WatermarkModule,
    # "extractor": ExtractorModule,  # Phase 2 - Week 6
}

__all__ = [
    "BaseModule",
    "ModuleSettingsPanel",
    "MODULES",
    "EditorModule",
    "ConverterModule",
    "CompressorModule",
    "SecurityModule",
    "WatermarkModule",
]
