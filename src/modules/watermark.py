"""
PDF Watermark Module — Add text and image watermarks to PDF files.
"""

import os
import io
import tempfile
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QCheckBox, QGroupBox,
    QRadioButton, QButtonGroup, QComboBox, QFileDialog,
    QSpinBox, QColorDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .base import BaseModule, ModuleSettingsPanel
from src.utils.logger import logger


class WatermarkModule(BaseModule):
    """Add text and image watermarks to PDF pages."""

    name = "PDF 水印"
    icon = "💧"
    description = "添加文字水印、图片水印，自定义位置、透明度、旋转角度"

    MODE_TEXT = "text"
    MODE_IMAGE = "image"

    # Position mapping (fractions of page dimensions)
    POSITIONS = {
        "居中": (0.5, 0.5),
        "左上": (0.15, 0.85),
        "右上": (0.85, 0.85),
        "左下": (0.15, 0.15),
        "右下": (0.85, 0.15),
        "顶部居中": (0.5, 0.90),
        "底部居中": (0.5, 0.10),
    }

    def process(self, input_files: list[str], output_dir: str,
                **settings) -> dict:
        """Add watermarks to PDF files."""
        mode = settings.get("mode", self.MODE_TEXT)
        output_files = []
        errors = []
        stats = {"total_pages": 0}

        try:
            if mode == self.MODE_TEXT:
                result = self._add_text_watermark(
                    input_files, output_dir, settings
                )
            elif mode == self.MODE_IMAGE:
                result = self._add_image_watermark(
                    input_files, output_dir, settings
                )
            else:
                return {"success": False,
                        "errors": [f"未知模式: {mode}"], "stats": stats}

            output_files = result.get("output_files", [])
            errors = result.get("errors", [])
            stats = result.get("stats", stats)
        except Exception as e:
            logger.error(f"Watermark process error: {e}")
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "output_files": output_files,
            "errors": errors,
            "stats": stats,
        }

    def _create_text_watermark_pdf(
        self, page_width: float, page_height: float, settings: dict
    ) -> str:
        """Create a temporary PDF with the text watermark."""
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor

        text = settings.get("watermark_text", "机密")
        font_size = int(settings.get("font_size", 48))
        color_hex = settings.get("color", "#ff0000")
        opacity = float(settings.get("opacity", 30)) / 100.0
        rotation = float(settings.get("rotation", 45))
        position = settings.get("position", "居中")

        # Get position coordinates
        pos_x_frac, pos_y_frac = self.POSITIONS.get(
            position, (0.5, 0.5)
        )

        # Create temporary file
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

        try:
            c = canvas.Canvas(tmp_path, pagesize=(page_width, page_height))

            # Set transparency
            c.setFillAlpha(opacity)

            # Set color
            try:
                r, g, b = self._hex_to_rgb(color_hex)
                c.setFillColorRGB(r / 255, g / 255, b / 255)
            except (ValueError, IndexError):
                c.setFillColorRGB(1, 0, 0)  # Default red

            # Set font
            c.setFont("Helvetica", font_size)

            # Calculate position
            x = page_width * pos_x_frac
            y = page_height * pos_y_frac

            # Save state, translate, rotate, draw, restore
            c.saveState()
            c.translate(x, y)
            c.rotate(rotation)
            c.drawCentredString(0, 0, text)
            c.restoreState()

            c.save()
        finally:
            pass

        return tmp_path

    def _create_image_watermark_pdf(
        self, page_width: float, page_height: float, settings: dict
    ) -> str:
        """Create a temporary PDF with the image watermark."""
        from reportlab.pdfgen import canvas

        image_path = settings.get("image_path", "")
        opacity = float(settings.get("opacity", 50)) / 100.0
        scale = float(settings.get("scale", 30)) / 100.0
        position = settings.get("position", "居中")

        pos_x_frac, pos_y_frac = self.POSITIONS.get(
            position, (0.5, 0.5)
        )

        fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

        try:
            from PIL import Image as PILImage
            img = PILImage.open(image_path)
            img_w, img_h = img.size

            # Scale image
            target_w = page_width * scale
            target_h = img_h * (target_w / img_w) if img_w > 0 else target_w

            c = canvas.Canvas(tmp_path, pagesize=(page_width, page_height))
            c.setFillAlpha(opacity)

            # Calculate position (top-left anchor for drawImage)
            x = page_width * pos_x_frac - target_w / 2
            y = page_height * pos_y_frac - target_h / 2

            c.drawImage(
                image_path, x, y,
                width=target_w, height=target_h,
                mask='auto'
            )

            c.save()
        finally:
            pass

        return tmp_path

    def _add_text_watermark(self, input_files: list[str], output_dir: str,
                            settings: dict) -> dict:
        """Apply text watermark to PDFs."""
        output_files = []
        errors = []
        total_pages = 0

        watermark_text = settings.get("watermark_text", "").strip()
        if not watermark_text:
            return {"output_files": [],
                    "errors": ["请输入水印文字"], "stats": {}}

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)
                total = len(reader.pages)
                total_pages += total

                # Get page dimensions from first page
                first_page = reader.pages[0]
                mediabox = first_page.mediabox
                page_w = float(mediabox.width)
                page_h = float(mediabox.height)

                # Create watermark overlay
                wm_path = self._create_text_watermark_pdf(
                    page_w, page_h, settings
                )
                wm_reader = PdfReader(wm_path)
                wm_page = wm_reader.pages[0]

                writer = PdfWriter()
                for page in reader.pages:
                    page.merge_page(wm_page, over=False)
                    writer.add_page(page)

                base_name = Path(file_path).stem
                out_path = self._unique_path(
                    os.path.join(output_dir, f"{base_name}_watermarked.pdf")
                )

                with open(out_path, "wb") as f:
                    writer.write(f)

                output_files.append(out_path)
                logger.info(
                    f"Watermarked: {os.path.basename(file_path)} "
                    f"({total} pages)"
                )

                # Clean up temp file
                try:
                    os.unlink(wm_path)
                except OSError:
                    pass

            except Exception as e:
                msg = (f"添加水印失败 {os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
        }

    def _add_image_watermark(self, input_files: list[str], output_dir: str,
                             settings: dict) -> dict:
        """Apply image watermark to PDFs."""
        output_files = []
        errors = []
        total_pages = 0

        image_path = settings.get("image_path", "")
        if not image_path or not os.path.exists(image_path):
            return {"output_files": [],
                    "errors": ["请选择水印图片"], "stats": {}}

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)
                total = len(reader.pages)
                total_pages += total

                first_page = reader.pages[0]
                mediabox = first_page.mediabox
                page_w = float(mediabox.width)
                page_h = float(mediabox.height)

                wm_path = self._create_image_watermark_pdf(
                    page_w, page_h, settings
                )
                wm_reader = PdfReader(wm_path)
                wm_page = wm_reader.pages[0]

                writer = PdfWriter()
                for page in reader.pages:
                    page.merge_page(wm_page, over=False)
                    writer.add_page(page)

                base_name = Path(file_path).stem
                out_path = self._unique_path(
                    os.path.join(output_dir, f"{base_name}_watermarked.pdf")
                )

                with open(out_path, "wb") as f:
                    writer.write(f)

                output_files.append(out_path)
                logger.info(
                    f"Image watermark added: "
                    f"{os.path.basename(file_path)} ({total} pages)"
                )

                try:
                    os.unlink(wm_path)
                except OSError:
                    pass

            except Exception as e:
                msg = (f"添加图片水印失败 "
                       f"{os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
        }

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert hex color string to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            return (int(hex_color[0:2], 16),
                    int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16))
        return (255, 0, 0)

    def _unique_path(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return filepath
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def create_settings_panel(self) -> QWidget:
        return WatermarkSettingsPanel(self)


class WatermarkSettingsPanel(ModuleSettingsPanel):
    """Settings panel for PDF watermark operations."""

    def __init__(self, module: WatermarkModule):
        super().__init__("PDF 水印")
        self.module = module

        # Mode selector
        mode_group = QGroupBox("水印类型")
        mode_layout = QVBoxLayout(mode_group)

        self.btn_text = QRadioButton("文字水印")
        self.btn_image = QRadioButton("图片水印")
        self.btn_text.setChecked(True)

        self._mode_buttons = QButtonGroup(self)
        self._mode_buttons.addButton(self.btn_text, 0)
        self._mode_buttons.addButton(self.btn_image, 1)

        mode_layout.addWidget(self.btn_text)
        mode_layout.addWidget(self.btn_image)
        self.add_widget(mode_group)

        # === Text Watermark Settings ===
        self._text_widget = QWidget()
        text_layout = QVBoxLayout(self._text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)

        # Text input
        text_group = QGroupBox("水印文字")
        text_group_layout = QVBoxLayout(text_group)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("如: 机密 / 仅供内部使用 / 草稿")
        self.text_input.setText("机密")
        text_group_layout.addWidget(self.text_input)
        text_layout.addWidget(text_group)

        # Font size
        size_group = QGroupBox("字体大小")
        size_layout = QHBoxLayout(size_group)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 200)
        self.size_spin.setValue(48)
        self.size_spin.setSuffix(" pt")
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        text_layout.addWidget(size_group)

        # Color button
        color_group = QGroupBox("水印颜色")
        color_layout = QHBoxLayout(color_group)
        self._current_color = QColor(255, 0, 0)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(32, 32)
        self._update_color_btn()
        self.color_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(QLabel("点击选择颜色"))
        color_layout.addStretch()
        text_layout.addWidget(color_group)

        # Opacity
        opacity_group = QGroupBox("透明度")
        opacity_layout = QVBoxLayout(opacity_group)
        opacity_header = QWidget()
        oh_layout = QHBoxLayout(opacity_header)
        oh_layout.setContentsMargins(0, 0, 0, 0)
        oh_layout.addWidget(QLabel("不透明度:"))
        self.opacity_value = QLabel("30%")
        oh_layout.addWidget(self.opacity_value)
        oh_layout.addStretch()
        opacity_layout.addWidget(opacity_header)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(5, 100)
        self.opacity_slider.setValue(30)
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_value.setText(f"{v}%")
        )
        opacity_layout.addWidget(self.opacity_slider)
        text_layout.addWidget(opacity_group)

        self.add_widget(self._text_widget)

        # === Image Watermark Settings ===
        self._image_widget = QWidget()
        img_layout = QVBoxLayout(self._image_widget)
        img_layout.setContentsMargins(0, 0, 0, 0)

        # Image selector
        img_sel_group = QGroupBox("选择图片")
        img_sel_layout = QVBoxLayout(img_sel_group)

        self.image_path_label = QLabel("未选择图片")
        self.image_path_label.setWordWrap(True)
        self.image_path_label.setStyleSheet(
            "color: #888; font-size: 11px; padding: 4px;"
        )
        img_sel_layout.addWidget(self.image_path_label)

        self.browse_btn = QPushButton("📁 浏览图片")
        self.browse_btn.clicked.connect(self._browse_image)
        img_sel_layout.addWidget(self.browse_btn)
        img_layout.addWidget(img_sel_group)

        # Scale
        scale_group = QGroupBox("图片缩放")
        scale_layout = QVBoxLayout(scale_group)
        scale_header = QWidget()
        sh_layout = QHBoxLayout(scale_header)
        sh_layout.setContentsMargins(0, 0, 0, 0)
        sh_layout.addWidget(QLabel("大小比例:"))
        self.scale_value = QLabel("30%")
        sh_layout.addWidget(self.scale_value)
        sh_layout.addStretch()
        scale_layout.addWidget(scale_header)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(5, 100)
        self.scale_slider.setValue(30)
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_value.setText(f"{v}%")
        )
        scale_layout.addWidget(self.scale_slider)
        img_layout.addWidget(scale_group)

        # Image opacity
        img_opacity_group = QGroupBox("图片透明度")
        img_opacity_layout = QVBoxLayout(img_opacity_group)
        io_header = QWidget()
        ioh_layout = QHBoxLayout(io_header)
        ioh_layout.setContentsMargins(0, 0, 0, 0)
        ioh_layout.addWidget(QLabel("不透明度:"))
        self.img_opacity_value = QLabel("50%")
        ioh_layout.addWidget(self.img_opacity_value)
        ioh_layout.addStretch()
        img_opacity_layout.addWidget(io_header)

        self.img_opacity_slider = QSlider(Qt.Horizontal)
        self.img_opacity_slider.setRange(5, 100)
        self.img_opacity_slider.setValue(50)
        self.img_opacity_slider.valueChanged.connect(
            lambda v: self.img_opacity_value.setText(f"{v}%")
        )
        img_opacity_layout.addWidget(self.img_opacity_slider)
        img_layout.addWidget(img_opacity_group)

        self.add_widget(self._image_widget)
        self._image_widget.setVisible(False)

        # === Common Settings ===
        # Position
        pos_group = QGroupBox("水印位置")
        pos_layout = QVBoxLayout(pos_group)

        self.pos_combo = QComboBox()
        self.pos_combo.addItems(list(WatermarkModule.POSITIONS.keys()))
        pos_layout.addWidget(self.pos_combo)
        self.add_widget(pos_group)

        # Rotation (text only - shown/hidden by mode switch)
        self._rotation_widget = QWidget()
        rot_layout = QHBoxLayout(self._rotation_widget)
        rot_layout.setContentsMargins(0, 0, 0, 0)
        rot_layout.addWidget(QLabel("旋转角度:"))
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(-180, 180)
        self.rotation_spin.setValue(45)
        self.rotation_spin.setSuffix("°")
        rot_layout.addWidget(self.rotation_spin)
        rot_layout.addStretch()
        self.add_widget(self._rotation_widget)

        # Connect signals
        self.btn_text.toggled.connect(lambda checked: self._on_mode_changed())
        self.btn_image.toggled.connect(lambda checked: self._on_mode_changed())

    def _on_mode_changed(self):
        is_text = self.btn_text.isChecked()
        self._text_widget.setVisible(is_text)
        self._image_widget.setVisible(not is_text)
        self._rotation_widget.setVisible(is_text)

    def _pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self._current_color, self, "选择水印颜色")
        if color.isValid():
            self._current_color = color
            self._update_color_btn()

    def _update_color_btn(self):
        """Update the color button appearance."""
        c = self._current_color
        self.color_btn.setStyleSheet(
            f"background-color: {c.name()}; "
            f"border: 1px solid #555; border-radius: 4px;"
        )

    def _browse_image(self):
        """Open file dialog to select watermark image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择水印图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
        )
        if file_path:
            self.image_path_label.setText(file_path)
            self.image_path_label.setStyleSheet(
                "color: #4a9eff; font-size: 11px; padding: 4px;"
            )

    def get_settings(self) -> dict:
        """Collect current settings."""
        pos = self.pos_combo.currentText()

        if self.btn_text.isChecked():
            return {
                "mode": "text",
                "watermark_text": self.text_input.text(),
                "font_size": self.size_spin.value(),
                "color": self._current_color.name(),
                "opacity": self.opacity_slider.value(),
                "rotation": self.rotation_spin.value(),
                "position": pos,
            }
        else:
            return {
                "mode": "image",
                "image_path": (
                    self.image_path_label.text()
                    if "未选择" not in self.image_path_label.text()
                    else ""
                ),
                "opacity": self.img_opacity_slider.value(),
                "scale": self.scale_slider.value(),
                "position": pos,
            }

