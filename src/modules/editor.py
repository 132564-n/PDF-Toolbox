"""
PDF Editor Module — Merge, Split, Rotate, Extract, Delete, Reorder pages.
"""

import os
from pathlib import Path
from typing import Optional
from pypdf import PdfWriter, PdfReader
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QSpinBox, QCheckBox,
    QGroupBox, QLineEdit, QComboBox,
)
from PySide6.QtCore import Qt, Signal

from .base import BaseModule, ModuleSettingsPanel
from src.utils.logger import logger


class EditorModule(BaseModule):
    """Merge, split, and reorder PDF pages."""

    name = "PDF 编辑"
    icon = "✂️"
    description = "合并多个PDF、拆分PDF、旋转/删除/提取页面"

    # Operation modes
    MODE_MERGE = "merge"
    MODE_SPLIT = "split"
    MODE_EXTRACT = "extract"
    MODE_DELETE = "delete"
    MODE_ROTATE = "rotate"

    def process(
        self,
        input_files: list[str],
        output_dir: str,
        **settings
    ) -> dict:
        """Process PDF files based on selected mode."""
        mode = settings.get("mode", self.MODE_MERGE)
        output_files = []
        errors = []
        stats = {"total_pages": 0, "output_pages": 0}

        try:
            if mode == self.MODE_MERGE:
                result = self._merge_pdfs(input_files, output_dir, settings)
            elif mode == self.MODE_SPLIT:
                result = self._split_pdfs(input_files, output_dir, settings)
            elif mode == self.MODE_EXTRACT:
                result = self._extract_pages(input_files, output_dir, settings)
            elif mode == self.MODE_DELETE:
                result = self._delete_pages(input_files, output_dir, settings)
            elif mode == self.MODE_ROTATE:
                result = self._rotate_pages(input_files, output_dir, settings)
            else:
                return {"success": False, "errors": [f"未知模式: {mode}"]}

            output_files = result.get("output_files", [])
            errors = result.get("errors", [])
            stats = result.get("stats", stats)
        except Exception as e:
            logger.error(f"Editor process error: {e}")
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "output_files": output_files,
            "errors": errors,
            "stats": stats,
        }

    def _merge_pdfs(
        self, input_files: list[str], output_dir: str, settings: dict
    ) -> dict:
        """Merge multiple PDFs into one."""
        writer = PdfWriter()
        total_pages = 0
        errors = []

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)
                for page in reader.pages:
                    writer.add_page(page)
                total_pages += len(reader.pages)
                logger.info(f"Added: {os.path.basename(file_path)} "
                            f"({len(reader.pages)} pages)")
            except Exception as e:
                msg = f"Failed to read {os.path.basename(file_path)}: {e}"
                logger.error(msg)
                errors.append(msg)

        if total_pages == 0:
            return {"output_files": [], "errors": errors,
                    "stats": {"total_pages": 0, "output_pages": 0}}

        # Generate output filename
        base_name = Path(input_files[0]).stem if input_files else "merged"
        output_path = os.path.join(output_dir, f"{base_name}_merged.pdf")
        # Avoid overwrite
        output_path = self._unique_path(output_path)

        try:
            writer.write(output_path)
            writer.close()
            logger.info(f"Merged PDF saved: {output_path}")
        except Exception as e:
            errors.append(f"Failed to write merged PDF: {e}")
            return {"output_files": [], "errors": errors,
                    "stats": {"total_pages": total_pages, "output_pages": 0}}

        return {
            "output_files": [output_path],
            "errors": errors,
            "stats": {
                "total_pages": total_pages,
                "output_pages": total_pages,
                "input_count": len(input_files),
            },
        }

    def _split_pdfs(
        self, input_files: list[str], output_dir: str, settings: dict
    ) -> dict:
        """Split PDF into individual pages or page ranges."""
        output_files = []
        errors = []
        total_pages = 0
        output_pages = 0

        split_mode = settings.get("split_mode", "every_page")
        page_range = settings.get("page_range", "")

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)
                total = len(reader.pages)
                total_pages += total
                base_name = Path(file_path).stem

                if split_mode == "every_page":
                    # Split every page
                    for i in range(total):
                        writer = PdfWriter()
                        writer.add_page(reader.pages[i])
                        out_path = self._unique_path(
                            os.path.join(output_dir,
                                         f"{base_name}_p{i+1:03d}.pdf")
                        )
                        writer.write(out_path)
                        writer.close()
                        output_files.append(out_path)
                        output_pages += 1
                        logger.info(f"Extracted page {i+1}: {out_path}")

                elif split_mode == "range":
                    # Split by page ranges (e.g., "1-3,5,7-10")
                    ranges = self._parse_ranges(page_range, total)
                    for r_start, r_end in ranges:
                        writer = PdfWriter()
                        for p in range(r_start - 1, r_end):
                            writer.add_page(reader.pages[p])
                        out_path = self._unique_path(
                            os.path.join(output_dir,
                                         f"{base_name}_p{r_start}-{r_end}.pdf")
                        )
                        writer.write(out_path)
                        writer.close()
                        output_files.append(out_path)
                        output_pages += (r_end - r_start + 1)

            except Exception as e:
                msg = f"Failed to split {os.path.basename(file_path)}: {e}"
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages, "output_pages": output_pages},
        }

    def _extract_pages(
        self, input_files: list[str], output_dir: str, settings: dict
    ) -> dict:
        """Extract selected page range to a new PDF."""
        # Reuse split logic with "range" mode
        settings["split_mode"] = "range"
        return self._split_pdfs(input_files, output_dir, settings)

    def _delete_pages(
        self, input_files: list[str], output_dir: str, settings: dict
    ) -> dict:
        """Delete specified pages from PDF."""
        output_files = []
        errors = []
        total_pages = 0
        output_pages = 0

        pages_to_delete = settings.get("delete_pages", "")

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)
                total = len(reader.pages)
                total_pages += total
                base_name = Path(file_path).stem

                # Parse pages to delete
                delete_set = self._parse_delete_pages(pages_to_delete, total)

                writer = PdfWriter()
                for i in range(total):
                    if (i + 1) not in delete_set:
                        writer.add_page(reader.pages[i])
                        output_pages += 1

                if len(writer.pages) == 0:
                    errors.append(f"No pages remain in "
                                  f"{os.path.basename(file_path)}")
                    continue

                out_path = self._unique_path(
                    os.path.join(output_dir, f"{base_name}_deleted.pdf")
                )
                writer.write(out_path)
                writer.close()
                output_files.append(out_path)
                logger.info(f"Deleted pages {sorted(delete_set)} "
                            f"from {os.path.basename(file_path)}")

            except Exception as e:
                msg = f"Failed to delete pages: {e}"
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages, "output_pages": output_pages},
        }

    def _rotate_pages(
        self, input_files: list[str], output_dir: str, settings: dict
    ) -> dict:
        """Rotate pages by specified angle."""
        output_files = []
        errors = []
        total_pages = 0

        angle = int(settings.get("rotation_angle", 90))
        pages_spec = settings.get("rotate_pages", "all")  # "all" or "1,3,5"

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)
                total = len(reader.pages)
                total_pages += total
                base_name = Path(file_path).stem

                # Determine which pages to rotate
                if pages_spec == "all":
                    pages_to_rotate = set(range(total))
                else:
                    pages_to_rotate = self._parse_delete_pages(
                        pages_spec, total
                    )
                    pages_to_rotate = {p - 1 for p in pages_to_rotate}

                writer = PdfWriter()
                for i in range(total):
                    page = reader.pages[i]
                    if i in pages_to_rotate:
                        page.rotate(angle)
                    writer.add_page(page)

                out_path = self._unique_path(
                    os.path.join(output_dir,
                                 f"{base_name}_rotated_{angle}.pdf")
                )
                writer.write(out_path)
                writer.close()
                output_files.append(out_path)
                logger.info(f"Rotated {len(pages_to_rotate)} pages "
                            f"by {angle}° in {os.path.basename(file_path)}")

            except Exception as e:
                msg = f"Failed to rotate: {e}"
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages,
                      "output_pages": total_pages},
        }

    def _parse_ranges(
        self, range_str: str, max_page: int
    ) -> list[tuple[int, int]]:
        """Parse page range string like '1-3,5,7-10' into [(1,3),(5,5),(7,10)]."""
        ranges = []
        for part in range_str.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                a, b = int(a), int(b)
                ranges.append((max(1, a), min(max_page, b)))
            else:
                p = int(part)
                p = max(1, min(max_page, p))
                ranges.append((p, p))
        return ranges

    def _parse_delete_pages(self, pages_str: str, max_page: int) -> set[int]:
        """Parse page numbers like '1,3,5-7' into a set of page numbers."""
        result = set()
        for part in pages_str.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                for p in range(int(a), int(b) + 1):
                    if 1 <= p <= max_page:
                        result.add(p)
            else:
                p = int(part)
                if 1 <= p <= max_page:
                    result.add(p)
        return result

    def _unique_path(self, filepath: str) -> str:
        """Generate a unique file path to avoid overwriting."""
        if not os.path.exists(filepath):
            return filepath
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def create_settings_panel(self) -> QWidget:
        """Create settings panel for PDF editing operations."""
        panel = EditorSettingsPanel(self)
        return panel


class EditorSettingsPanel(ModuleSettingsPanel):
    """Settings panel for the Editor module."""

    mode_changed = Signal(str)

    def __init__(self, module: EditorModule):
        super().__init__("PDF 编辑")
        self.module = module

        # Operation mode selector
        mode_group = QGroupBox("操作模式")
        mode_layout = QVBoxLayout(mode_group)

        self.btn_merge = QRadioButton("合并 PDF")
        self.btn_split = QRadioButton("拆分 PDF")
        self.btn_extract = QRadioButton("提取页面")
        self.btn_delete = QRadioButton("删除页面")
        self.btn_rotate = QRadioButton("旋转页面")
        self.btn_merge.setChecked(True)

        self._mode_buttons = QButtonGroup(self)
        self._mode_buttons.addButton(self.btn_merge, 0)
        self._mode_buttons.addButton(self.btn_split, 1)
        self._mode_buttons.addButton(self.btn_extract, 2)
        self._mode_buttons.addButton(self.btn_delete, 3)
        self._mode_buttons.addButton(self.btn_rotate, 4)

        mode_layout.addWidget(self.btn_merge)
        mode_layout.addWidget(self.btn_split)
        mode_layout.addWidget(self.btn_extract)
        mode_layout.addWidget(self.btn_delete)
        mode_layout.addWidget(self.btn_rotate)

        self.add_widget(mode_group)

        # Settings area (stacked based on mode)
        self._settings_stack = QWidget()
        self._settings_layout = QVBoxLayout(self._settings_stack)
        self._settings_layout.setContentsMargins(0, 0, 0, 0)
        self.add_widget(self._settings_stack)

        # Build sub-panels
        self._build_merge_settings()
        self._build_split_settings()
        self._build_rotate_settings()

        # Connect signals
        self.btn_merge.toggled.connect(lambda: self._on_mode_change("merge"))
        self.btn_split.toggled.connect(lambda: self._on_mode_change("split"))
        self.btn_extract.toggled.connect(
            lambda: self._on_mode_change("extract")
        )
        self.btn_delete.toggled.connect(
            lambda: self._on_mode_change("delete")
        )
        self.btn_rotate.toggled.connect(
            lambda: self._on_mode_change("rotate")
        )

    def _on_mode_change(self, mode: str):
        self.module._current_mode = mode
        self.mode_changed.emit(mode)
        self._show_settings(mode)

    def _build_merge_settings(self):
        """Merge settings - just a label."""
        self._merge_widget = QWidget()
        layout = QVBoxLayout(self._merge_widget)
        tip = QLabel("将所有选中的PDF文件合并为一个PDF文档。\n"
                     "文件将按列表顺序合并。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(tip)
        self._settings_layout.addWidget(self._merge_widget)

    def _build_split_settings(self):
        """Split settings - every page or by range."""
        self._split_widget = QWidget()
        layout = QVBoxLayout(self._split_widget)

        split_group = QGroupBox("拆分方式")
        split_layout = QVBoxLayout(split_group)
        self.btn_every_page = QRadioButton("每一页单独拆分")
        self.btn_range = QRadioButton("按页码范围")
        self.btn_every_page.setChecked(True)
        split_layout.addWidget(self.btn_every_page)
        split_layout.addWidget(self.btn_range)
        layout.addWidget(split_group)

        # Page range input (visible only when range mode)
        range_widget = QWidget()
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.addWidget(QLabel("页码范围:"))
        self.range_input = QLineEdit()
        self.range_input.setPlaceholderText("如: 1-3,5,7-10")
        range_layout.addWidget(self.range_input)
        layout.addWidget(range_widget)

        self.btn_range.toggled.connect(
            lambda checked: range_widget.setVisible(checked)
        )
        range_widget.setVisible(False)

        self._settings_layout.addWidget(self._split_widget)

    def _build_rotate_settings(self):
        """Rotation settings."""
        self._rotate_widget = QWidget()
        layout = QVBoxLayout(self._rotate_widget)

        # Angle selector
        angle_group = QGroupBox("旋转角度")
        angle_layout = QHBoxLayout(angle_group)
        angle_layout.addWidget(QLabel("角度:"))
        self.angle_combo = QComboBox()
        self.angle_combo.addItems(["90°", "180°", "270°"])
        angle_layout.addWidget(self.angle_combo)
        angle_layout.addStretch()
        layout.addWidget(angle_group)

        # Page specification
        pages_group = QGroupBox("目标页面")
        pages_layout = QVBoxLayout(pages_group)
        self.btn_all_pages = QRadioButton("所有页面")
        self.btn_specific_pages = QRadioButton("指定页面")
        self.btn_all_pages.setChecked(True)
        pages_layout.addWidget(self.btn_all_pages)
        pages_layout.addWidget(self.btn_specific_pages)

        pages_input = QWidget()
        pages_input_layout = QHBoxLayout(pages_input)
        pages_input_layout.setContentsMargins(0, 0, 0, 0)
        pages_input_layout.addWidget(QLabel("页码:"))
        self.rotate_pages_input = QLineEdit()
        self.rotate_pages_input.setPlaceholderText("如: 1,3,5")
        pages_input_layout.addWidget(self.rotate_pages_input)
        pages_layout.addWidget(pages_input)

        self.btn_specific_pages.toggled.connect(
            lambda checked: pages_input.setVisible(checked)
        )
        pages_input.setVisible(False)

        layout.addWidget(pages_group)
        self._settings_layout.addWidget(self._rotate_widget)

    def _show_settings(self, mode: str):
        """Show/hide settings widgets based on mode."""
        self._merge_widget.setVisible(mode == "merge")
        self._split_widget.setVisible(
            mode in ("split", "extract", "delete")
        )
        self._rotate_widget.setVisible(mode == "rotate")

    def get_settings(self) -> dict:
        """Collect current settings as dict."""
        if self.btn_merge.isChecked():
            return {"mode": "merge"}
        elif self.btn_split.isChecked():
            split_mode = "every_page" if self.btn_every_page.isChecked() else "range"
            return {
                "mode": "split",
                "split_mode": split_mode,
                "page_range": self.range_input.text(),
            }
        elif self.btn_extract.isChecked():
            return {
                "mode": "extract",
                "split_mode": "range",
                "page_range": self.range_input.text(),
            }
        elif self.btn_delete.isChecked():
            return {
                "mode": "delete",
                "delete_pages": self.range_input.text(),
            }
        elif self.btn_rotate.isChecked():
            angle_text = self.angle_combo.currentText()
            angle = int(angle_text.replace("°", ""))
            pages = ("all" if self.btn_all_pages.isChecked()
                     else self.rotate_pages_input.text())
            return {
                "mode": "rotate",
                "rotation_angle": angle,
                "rotate_pages": pages,
            }
        return {"mode": "merge"}

