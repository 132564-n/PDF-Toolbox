"""
PDF Watermark Module — Add text/image watermarks to PDF files.
(To be implemented in Phase 2 - Week 5)
"""

from .base import BaseModule, ModuleSettingsPanel
from PySide6.QtWidgets import QWidget


class WatermarkModule(BaseModule):
    """Add text and image watermarks to PDFs."""

    name = "PDF 水印"
    icon = "💧"
    description = "添加文字水印、图片水印，自定义位置、透明度、旋转角度"

    def process(self, input_files, output_dir, **settings) -> dict:
        return {"success": False,
                "errors": ["Watermark module not yet implemented"],
                "stats": {}}

    def create_settings_panel(self) -> QWidget:
        panel = ModuleSettingsPanel("PDF 水印")
        return panel

