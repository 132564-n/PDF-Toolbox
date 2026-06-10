"""
PDF Converter Module — Convert PDF to/from various formats.

Supported conversions:
- PDF → Word (.docx)
- PDF → Excel (.xlsx)
- PDF → Image (.png / .jpg)
- PDF → HTML
- Image → PDF
"""

import os
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QButtonGroup, QRadioButton, QComboBox,
    QGroupBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal

from .base import BaseModule, ModuleSettingsPanel
from src.utils.logger import logger


class ConverterModule(BaseModule):
    """Convert between PDF and other document formats."""

    name = "PDF 转换"
    icon = "🔄"
    description = "PDF转Word/Excel/图片/HTML，图片转PDF"

    CONVERT_PDF_TO_WORD = "pdf_to_word"
    CONVERT_PDF_TO_EXCEL = "pdf_to_excel"
    CONVERT_PDF_TO_IMAGE = "pdf_to_image"
    CONVERT_PDF_TO_HTML = "pdf_to_html"
    CONVERT_IMAGE_TO_PDF = "image_to_pdf"

    def process(
        self,
        input_files: list[str],
        output_dir: str,
        **settings
    ) -> dict:
        """Convert files based on selected conversion type."""
        conv_type = settings.get("conversion_type", self.CONVERT_PDF_TO_WORD)
        output_files = []
        errors = []
        stats = {"total_pages": 0}

        signals = settings.get("_signals")

        try:
            if conv_type == self.CONVERT_PDF_TO_WORD:
                result = self._pdf_to_word(
                    input_files, output_dir, signals
                )
            elif conv_type == self.CONVERT_PDF_TO_EXCEL:
                result = self._pdf_to_excel(
                    input_files, output_dir, signals
                )
            elif conv_type == self.CONVERT_PDF_TO_IMAGE:
                result = self._pdf_to_image(
                    input_files, output_dir, settings, signals
                )
            elif conv_type == self.CONVERT_PDF_TO_HTML:
                result = self._pdf_to_html(
                    input_files, output_dir, signals
                )
            elif conv_type == self.CONVERT_IMAGE_TO_PDF:
                result = self._image_to_pdf(
                    input_files, output_dir, settings, signals
                )
            else:
                return {"success": False, "errors": [f"未知转换类型: {conv_type}"],
                        "stats": stats}

            output_files = result.get("output_files", [])
            errors = result.get("errors", [])
            stats = result.get("stats", stats)
        except Exception as e:
            logger.error(f"Converter error: {e}")
            import traceback
            traceback.print_exc()
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "output_files": output_files,
            "errors": errors,
            "stats": stats,
        }

    def _pdf_to_word(
        self, input_files: list[str], output_dir: str, signals
    ) -> dict:
        """Convert PDF files to Word (.docx) format."""
        output_files = []
        errors = []
        total_pages = 0

        try:
            from pdf2docx import Converter as DocxConverter
        except ImportError:
            return {
                "output_files": [],
                "errors": ["pdf2docx 库未安装，请运行: pip install pdf2docx"],
                "stats": {"total_pages": 0},
            }

        for i, file_path in enumerate(input_files):
            try:
                base_name = Path(file_path).stem
                out_path = os.path.join(output_dir, f"{base_name}.docx")
                out_path = self._unique_path(out_path)

                if signals:
                    signals.status.emit(
                        f"正在转换: {os.path.basename(file_path)} → Word"
                    )
                    signals.progress.emit(
                        int((i + 0.2) / len(input_files) * 100)
                    )

                # Convert using pdf2docx
                cv = DocxConverter(file_path)
                cv.convert(out_path, start=0, end=None)
                cv.close()

                # Count pages
                reader = PdfReader(file_path)
                total_pages += len(reader.pages)

                output_files.append(out_path)
                logger.info(
                    f"Converted: {os.path.basename(file_path)} → {out_path}"
                )

                if signals:
                    signals.progress.emit(
                        int((i + 1) / len(input_files) * 100)
                    )

            except Exception as e:
                msg = (f"PDF→Word 转换失败 "
                       f"{os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
        }

    def _pdf_to_excel(
        self, input_files: list[str], output_dir: str, signals
    ) -> dict:
        """Extract tables from PDF to Excel (.xlsx) format."""
        output_files = []
        errors = []
        total_pages = 0

        try:
            import pdfplumber
            from openpyxl import Workbook
        except ImportError:
            missing = []
            try:
                import pdfplumber
            except ImportError:
                missing.append("pdfplumber")
            try:
                import openpyxl
            except ImportError:
                missing.append("openpyxl")
            return {
                "output_files": [],
                "errors": [f"缺少库: {', '.join(missing)}，"
                          f"请运行: pip install {' '.join(missing)}"],
                "stats": {"total_pages": 0},
            }

        for i, file_path in enumerate(input_files):
            try:
                if signals:
                    signals.status.emit(
                        f"正在提取表格: {os.path.basename(file_path)}"
                    )

                with pdfplumber.open(file_path) as pdf:
                    total_pages += len(pdf.pages)

                    # Create workbook
                    wb = Workbook()
                    # Remove default sheet
                    wb.remove(wb.active)

                    table_count = 0

                    for page_num, page in enumerate(pdf.pages, 1):
                        tables = page.extract_tables()
                        for t_idx, table in enumerate(tables):
                            table_count += 1
                            sheet_name = (f"Page{page_num}_Table{t_idx+1}"
                                          if len(tables) > 1
                                          else f"Page{page_num}")
                            ws = wb.create_sheet(title=sheet_name[:31])

                            for row in table:
                                ws.append(row)

                        if signals:
                            signals.progress.emit(
                                int(page_num / len(pdf.pages) * 100)
                            )

                    if table_count == 0:
                        errors.append(
                            f"{os.path.basename(file_path)} 中未检测到表格"
                        )
                        continue

                    base_name = Path(file_path).stem
                    out_path = self._unique_path(
                        os.path.join(output_dir, f"{base_name}_tables.xlsx")
                    )
                    wb.save(out_path)
                    output_files.append(out_path)
                    logger.info(
                        f"Extracted {table_count} tables: "
                        f"{os.path.basename(file_path)} → {out_path}"
                    )

            except Exception as e:
                msg = (f"PDF→Excel 转换失败 "
                       f"{os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
        }

    def _pdf_to_image(
        self, input_files: list[str], output_dir: str,
        settings: dict, signals
    ) -> dict:
        """Convert PDF pages to images using pdfplumber."""
        output_files = []
        errors = []
        total_pages = 0

        image_format = settings.get("image_format", "png").lower()
        dpi = int(settings.get("dpi", 150))

        try:
            import pdfplumber
        except ImportError:
            return {
                "output_files": [],
                "errors": ["pdfplumber 库未安装，请运行: pip install pdfplumber"],
                "stats": {"total_pages": 0},
            }

        for file_path in input_files:
            try:
                base_name = Path(file_path).stem
                base_dir = os.path.join(output_dir, f"{base_name}_images")
                os.makedirs(base_dir, exist_ok=True)

                if signals:
                    signals.status.emit(
                        f"正在渲染: {os.path.basename(file_path)}"
                    )

                with pdfplumber.open(file_path) as pdf:
                    total_pages += len(pdf.pages)

                    for page_num, page in enumerate(pdf.pages, 1):
                        # Render page to image
                        img = page.to_image(resolution=dpi)
                        out_path = os.path.join(
                            base_dir,
                            f"{base_name}_p{page_num:03d}.{image_format}"
                        )
                        img.save(out_path, format=image_format.upper())
                        output_files.append(out_path)

                        if signals and len(pdf.pages) > 1:
                            signals.progress.emit(
                                int(page_num / len(pdf.pages) * 100)
                            )

                logger.info(
                    f"Rendered {len(pdf.pages)} pages to "
                    f"{image_format.upper()}: {base_dir}"
                )

            except Exception as e:
                msg = (f"PDF→图片 转换失败 "
                       f"{os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
        }

    def _pdf_to_html(
        self, input_files: list[str], output_dir: str, signals
    ) -> dict:
        """Convert PDF to HTML using pdfminer (basic conversion)."""
        output_files = []
        errors = []
        total_pages = 0

        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams
        except ImportError:
            return {
                "output_files": [],
                "errors": ["pdfminer.six 库未安装，"
                          "请运行: pip install pdfminer.six"],
                "stats": {"total_pages": 0},
            }

        for i, file_path in enumerate(input_files):
            try:
                base_name = Path(file_path).stem
                out_path = self._unique_path(
                    os.path.join(output_dir, f"{base_name}.html")
                )

                if signals:
                    signals.status.emit(
                        f"正在转换: {os.path.basename(file_path)} → HTML"
                    )

                reader = PdfReader(file_path)
                total_pages += len(reader.pages)

                # Generate simple HTML with extracted text
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                    f.write('<meta charset="utf-8">\n')
                    f.write(f"<title>{base_name}</title>\n")
                    f.write("<style>body{font-family:Arial,sans-serif;"
                            "max-width:800px;margin:40px auto;"
                            "line-height:1.6;}</style>\n")
                    f.write("</head>\n<body>\n")
                    f.write(f"<h1>{base_name}</h1>\n<hr>\n")

                    for page_num, page in enumerate(reader.pages, 1):
                        text = page.extract_text()
                        if text:
                            f.write(
                                f'<div class="page">\n'
                                f'<p>{text.replace(chr(10), "<br>")}</p>\n'
                                f'</div>\n'
                            )
                        if page_num < len(reader.pages):
                            f.write("<hr>\n")

                        if signals and len(reader.pages) > 1:
                            signals.progress.emit(
                                int(page_num / len(reader.pages) * 100)
                            )

                    f.write("</body>\n</html>")

                output_files.append(out_path)
                logger.info(f"HTML saved: {out_path}")

            except Exception as e:
                msg = (f"PDF→HTML 转换失败 "
                       f"{os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
        }

    def _image_to_pdf(
        self, input_files: list[str], output_dir: str,
        settings: dict, signals
    ) -> dict:
        """Convert images to PDF."""
        output_files = []
        errors = []

        merge_to_one = settings.get("merge_images", True)
        page_size = settings.get("page_size", "A4")

        try:
            from PIL import Image as PILImage
        except ImportError:
            return {
                "output_files": [],
                "errors": ["Pillow 库未安装，请运行: pip install Pillow"],
                "stats": {},
            }

        if merge_to_one:
            # Merge all images into a single PDF
            pil_images = []
            for i, file_path in enumerate(input_files):
                try:
                    img = PILImage.open(file_path)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    pil_images.append(img)
                    if signals:
                        signals.progress.emit(
                            int((i + 1) * 0.8 / len(input_files) * 100)
                        )
                except Exception as e:
                    errors.append(
                        f"无法读取图片 {os.path.basename(file_path)}: {e}"
                    )

            if pil_images:
                base_name = Path(input_files[0]).stem if input_files \
                    else "images"
                out_path = self._unique_path(
                    os.path.join(output_dir, f"{base_name}_to_pdf.pdf")
                )
                pil_images[0].save(
                    out_path, "PDF", save_all=True,
                    append_images=pil_images[1:],
                    resolution=100.0,
                )
                output_files.append(out_path)
                logger.info(f"Created PDF from {len(pil_images)} images")
        else:
            # Each image → separate PDF
            for i, file_path in enumerate(input_files):
                try:
                    img = PILImage.open(file_path)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    base_name = Path(file_path).stem
                    out_path = self._unique_path(
                        os.path.join(output_dir, f"{base_name}.pdf")
                    )
                    img.save(out_path, "PDF", resolution=100.0)
                    output_files.append(out_path)

                    if signals:
                        signals.progress.emit(
                            int((i + 1) / len(input_files) * 100)
                        )
                except Exception as e:
                    errors.append(
                        f"图片转PDF失败 {os.path.basename(file_path)}: {e}"
                    )

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"image_count": len(input_files)},
        }

    def _unique_path(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return filepath
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def create_settings_panel(self) -> QWidget:
        return ConverterSettingsPanel(self)


class ConverterSettingsPanel(ModuleSettingsPanel):
    """Settings panel for PDF conversion."""

    conversion_changed = Signal(str)

    def __init__(self, module: ConverterModule):
        super().__init__("PDF 转换")
        self.module = module

        # Conversion type selector
        type_group = QGroupBox("转换类型")
        type_layout = QVBoxLayout(type_group)

        self.btn_to_word = QRadioButton("PDF → Word (.docx)")
        self.btn_to_excel = QRadioButton("PDF → Excel (.xlsx)")
        self.btn_to_image = QRadioButton("PDF → 图片 (.png/.jpg)")
        self.btn_to_html = QRadioButton("PDF → HTML")
        self.btn_to_pdf = QRadioButton("图片 → PDF")
        self.btn_to_word.setChecked(True)

        self._type_buttons = QButtonGroup(self)
        self._type_buttons.addButton(self.btn_to_word, 0)
        self._type_buttons.addButton(self.btn_to_excel, 1)
        self._type_buttons.addButton(self.btn_to_image, 2)
        self._type_buttons.addButton(self.btn_to_html, 3)
        self._type_buttons.addButton(self.btn_to_pdf, 4)

        type_layout.addWidget(self.btn_to_word)
        type_layout.addWidget(self.btn_to_excel)
        type_layout.addWidget(self.btn_to_image)
        type_layout.addWidget(self.btn_to_html)
        type_layout.addWidget(self.btn_to_pdf)
        self.add_widget(type_group)

        # Options area (changes based on conversion type)
        self._options_stack = QWidget()
        self._options_layout = QVBoxLayout(self._options_stack)
        self._options_layout.setContentsMargins(0, 0, 0, 0)
        self.add_widget(self._options_stack)

        # Image format options (for PDF → Image)
        self._build_image_options()

        # Connect signals
        for btn in [self.btn_to_word, self.btn_to_excel,
                     self.btn_to_image, self.btn_to_html, self.btn_to_pdf]:
            btn.toggled.connect(self._on_type_changed)

    def _on_type_changed(self):
        conversion_type = self.get_conversion_type()
        self.module._current_conversion = conversion_type
        self.conversion_changed.emit(conversion_type)
        self._image_options.setVisible(
            conversion_type == self.module.CONVERT_PDF_TO_IMAGE
        )

    def _build_image_options(self):
        """Build options for PDF → Image conversion."""
        self._image_options = QWidget()
        layout = QVBoxLayout(self._image_options)

        # Format selection
        format_group = QGroupBox("图片格式")
        format_layout = QHBoxLayout(format_group)
        format_layout.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPG"])
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addWidget(format_group)

        # DPI selector
        dpi_group = QGroupBox("分辨率 (DPI)")
        dpi_layout = QHBoxLayout(dpi_group)
        dpi_layout.addWidget(QLabel("DPI:"))
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["72", "150", "200", "300"])
        self.dpi_combo.setCurrentIndex(1)  # Default 150
        dpi_layout.addWidget(self.dpi_combo)
        dpi_layout.addStretch()
        layout.addWidget(dpi_group)

        self._image_options.setVisible(False)
        self._options_layout.addWidget(self._image_options)

        # Image→PDF options
        self._img_to_pdf_options = QWidget()
        img_layout = QVBoxLayout(self._img_to_pdf_options)

        merge_group = QGroupBox("合并设置")
        merge_layout = QVBoxLayout(merge_group)
        self.chk_merge = QCheckBox("所有图片合并为一个PDF")
        self.chk_merge.setChecked(True)
        merge_layout.addWidget(self.chk_merge)
        img_layout.addWidget(merge_group)

        self._img_to_pdf_options.setVisible(False)
        self._options_layout.addWidget(self._img_to_pdf_options)

    def get_conversion_type(self) -> str:
        """Get currently selected conversion type."""
        if self.btn_to_word.isChecked():
            return self.module.CONVERT_PDF_TO_WORD
        elif self.btn_to_excel.isChecked():
            return self.module.CONVERT_PDF_TO_EXCEL
        elif self.btn_to_image.isChecked():
            return self.module.CONVERT_PDF_TO_IMAGE
        elif self.btn_to_html.isChecked():
            return self.module.CONVERT_PDF_TO_HTML
        elif self.btn_to_pdf.isChecked():
            return self.module.CONVERT_IMAGE_TO_PDF
        return self.module.CONVERT_PDF_TO_WORD

    def get_settings(self) -> dict:
        """Collect current settings."""
        settings = {
            "conversion_type": self.get_conversion_type(),
        }

        if self.get_conversion_type() == "pdf_to_image":
            settings["image_format"] = self.format_combo.currentText().lower()
            settings["dpi"] = int(self.dpi_combo.currentText())

        if self.get_conversion_type() == "image_to_pdf":
            settings["merge_images"] = self.chk_merge.isChecked()

        return settings

