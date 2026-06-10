"""
Drag-and-drop zone widget.
Accepts file drops and click-to-browse.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent

from src.utils.logger import logger


class DropZone(QWidget):
    """
    A drop zone that accepts PDF files via drag-and-drop or click-to-browse.

    Emits files_dropped signal with list of file paths.
    """

    # Signal emitted when files are dropped or selected
    files_dropped = Signal(list)

    # Supported file extensions
    PDF_EXTENSIONS = {".pdf"}
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif",
                         ".tiff", ".tif", ".webp"}
    ALL_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self._setup_ui()

    def _setup_ui(self):
        """Build the drop zone UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Icon
        self.icon_label = QLabel("📁")
        self.icon_label.setStyleSheet("font-size: 48px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        # Main text
        self.text_label = QLabel("拖拽 PDF 或图片文件到此处")
        self.text_label.setStyleSheet(
            "font-size: 16px; color: #aaaaaa;"
        )
        self.text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.text_label)

        # Sub text
        self.sub_text = QLabel("或点击选择文件")
        self.sub_text.setStyleSheet("font-size: 13px; color: #666666;")
        self.sub_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.sub_text)

        # File count
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("font-size: 12px; color: #4a9eff;")
        self.count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.count_label)

        # Dashed border style (set via stylesheet)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #555555;
                border-radius: 12px;
                background-color: #1e1e2e;
                padding: 20px;
            }
            DropZone:hover {
                border-color: #4a9eff;
                background-color: #252535;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drag if it contains files."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    border: 2px solid #4a9eff;
                    border-radius: 12px;
                    background-color: #252540;
                    padding: 20px;
                }
            """)

    def dragLeaveEvent(self, event):
        """Reset border style when drag leaves."""
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #555555;
                border-radius: 12px;
                background-color: #1e1e2e;
                padding: 20px;
            }
            DropZone:hover {
                border-color: #4a9eff;
                background-color: #252535;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        """Handle file drop."""
        self.dragLeaveEvent(None)  # Reset style

        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            ext = os.path.splitext(file_path)[1].lower()
            if ext in self.ALL_EXTENSIONS:
                files.append(file_path)

        if files:
            logger.info(f"Dropped {len(files)} file(s)")
            self.files_dropped.emit(files)
            self.count_label.setText(
                f"已添加 {len(files)} 个文件"
            )

    def mousePressEvent(self, event: QMouseEvent):
        """Click to browse files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文件",
            "",
            "支持的文件 (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp);;"
            "PDF 文件 (*.pdf);;"
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);;"
            "所有文件 (*.*)",
        )
        if files:
            logger.info(f"Selected {len(files)} file(s)")
            self.files_dropped.emit(files)
            self.count_label.setText(
                f"已添加 {len(files)} 个文件"
            )

