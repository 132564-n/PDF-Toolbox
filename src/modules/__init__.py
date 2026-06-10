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

# Register all available modules
MODULES = {
    "editor": EditorModule,
    "converter": ConverterModule,
    "compressor": CompressorModule,
    # Will be implemented later:
    # "security": SecurityModule,
    # "watermark": WatermarkModule,
    # "extractor": ExtractorModule,
}

__all__ = [
    "BaseModule",
    "ModuleSettingsPanel",
    "MODULES",
    "EditorModule",
    "ConverterModule",
    "CompressorModule",
]
