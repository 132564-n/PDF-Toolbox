"""
File list widget for displaying and managing loaded files.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QBrush, QColor

from src.utils.logger import logger


class FileListWidget(QWidget):
    """
    Displays a list of loaded files with file info.
    Supports multi-select, remove, clear, and reorder.
    """

    files_changed = Signal(int)  # Emits total file count

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._files: list[str] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the file list UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header bar
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self.header_label = QLabel("文件列表")
        self.header_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #cccccc;"
        )
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        # Clear button
        self.btn_clear = QPushButton("清空")
        self.btn_clear.setMinimumWidth(52)
        self.btn_clear.setFixedHeight(26)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #ccc;
                font-size: 12px;
                padding: 2px 10px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_files)
        header_layout.addWidget(self.btn_clear)

        # Remove selected button
        self.btn_remove = QPushButton("移除选中")
        self.btn_remove.setMinimumWidth(72)
        self.btn_remove.setFixedHeight(26)
        self.btn_remove.setStyleSheet(self.btn_clear.styleSheet())
        self.btn_remove.clicked.connect(self.remove_selected)
        header_layout.addWidget(self.btn_remove)

        layout.addWidget(header)

        # File list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.list_widget.setDragDropMode(
            QAbstractItemView.InternalMove
        )
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1a1a2e;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                color: #cccccc;
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #2a2a3a;
            }
            QListWidget::item:selected {
                background-color: #2a4a6a;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #252540;
            }
            QListWidget::item:alternate {
                background-color: #1e1e32;
            }
        """)
        layout.addWidget(self.list_widget)

        # Footer stats
        self.footer_label = QLabel("就绪")
        self.footer_label.setStyleSheet(
            "font-size: 11px; color: #777; padding: 2px 8px;"
        )
        layout.addWidget(self.footer_label)

    def add_files(self, file_paths: list[str]):
        """Add files to the list (skips duplicates)."""
        added = 0
        for fp in file_paths:
            fp = os.path.normpath(fp)
            if fp not in self._files:
                self._files.append(fp)
                self._add_file_item(fp)
                added += 1
        self._update_footer()
        self.files_changed.emit(len(self._files))
        return added

    def _add_file_item(self, file_path: str):
        """Add a single file item to the list widget."""
        item = QListWidgetItem()
        basename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        # Icon based on file type
        if ext == ".pdf":
            icon_text = "📄"
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            icon_text = "🖼️"
        else:
            icon_text = "📎"

        # File size
        try:
            size = os.path.getsize(file_path)
            size_str = self._format_size(size)
        except OSError:
            size_str = "N/A"

        item.setText(f"  {icon_text}  {basename}")
        item.setToolTip(f"路径: {file_path}\n大小: {size_str}")
        item.setData(Qt.UserRole, file_path)

        self.list_widget.addItem(item)

    def remove_selected(self):
        """Remove selected files from the list."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            fp = item.data(Qt.UserRole)
            if fp in self._files:
                self._files.remove(fp)
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

        self._update_footer()
        self.files_changed.emit(len(self._files))

    def clear_files(self):
        """Remove all files from the list."""
        self._files.clear()
        self.list_widget.clear()
        self._update_footer()
        self.files_changed.emit(0)

    def get_files(self) -> list[str]:
        """Get current list of file paths."""
        return self._files.copy()

    @property
    def file_count(self) -> int:
        return len(self._files)

    def _update_footer(self):
        """Update footer with file stats."""
        count = len(self._files)
        if count == 0:
            self.footer_label.setText("就绪 — 请添加文件")
            return

        # Calculate total size
        total_size = 0
        for fp in self._files:
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                pass

        self.footer_label.setText(
            f"共 {count} 个文件 | "
            f"总大小: {self._format_size(total_size)}"
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size human-readably."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

