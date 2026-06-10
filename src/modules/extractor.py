"""
PDF Extractor Module — Extract text, images, and tables from PDF.
(To be implemented in Phase 2 - Week 6)
"""

from .base import BaseModule, ModuleSettingsPanel
from PySide6.QtWidgets import QWidget


class ExtractorModule(BaseModule):
    """Extract content from PDF files."""

    name = "PDF 提取"
    icon = "📤"
    description = "提取PDF中的文字(OCR)、图片、表格数据"

    def process(self, input_files, output_dir, **settings) -> dict:
        return {"success": False,
                "errors": ["Extractor module not yet implemented"],
                "stats": {}}

    def create_settings_panel(self) -> QWidget:
        panel = ModuleSettingsPanel("PDF 提取")
        return panel

