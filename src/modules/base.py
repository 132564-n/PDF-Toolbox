"""
Base class for all PDF processing modules.
Each module (Converter, Editor, Compressor, etc.) inherits from this.
"""

from abc import ABC, abstractmethod
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt


class BaseModule(ABC):
    """
    Abstract base class for PDF processing modules.

    Each module must implement:
    - name: Display name of the module
    - icon: Icon identifier (emoji or path)
    - description: Short description for tooltip
    - process(): Core processing logic
    - create_settings_panel(): Returns a QWidget with module-specific settings
    """

    name: str = "Base Module"
    icon: str = "📄"
    description: str = ""

    def __init__(self):
        self._is_running = False

    @abstractmethod
    def process(
        self,
        input_files: list[str],
        output_dir: str,
        **settings
    ) -> dict:
        """
        Core processing logic.

        Args:
            input_files: List of input file paths
            output_dir: Output directory
            **settings: Module-specific settings

        Returns:
            dict with 'success': bool, 'output_files': list[str],
            'errors': list[str], 'stats': dict
        """
        pass

    @abstractmethod
    def create_settings_panel(self) -> QWidget:
        """
        Create the settings panel widget shown in the right sidebar.

        Returns:
            QWidget with module-specific controls (dropdowns, sliders, etc.)
        """
        pass

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool):
        self._is_running = value

    def get_default_output_dir(self) -> str:
        """Get default output directory (same as input by default)."""
        import os
        return os.path.expanduser("~\\Documents\\PDFToolbox_Output")


class ModuleSettingsPanel(QWidget):
    """
    Reusable settings panel base with common UI patterns.

    Wraps content in a scroll area so no controls get cut off.
    """

    def __init__(self, title: str, parent: QWidget = None):
        super().__init__(parent)

        # Outer layout for this widget
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        # Inner widget
        inner = QWidget()
        self._layout = QVBoxLayout(inner)
        self._layout.setContentsMargins(10, 12, 10, 12)
        self._layout.setSpacing(8)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; padding-bottom: 4px;"
        )
        self._layout.addWidget(self.title_label)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #3a3a3a;")
        self._layout.addWidget(sep)

        # Settings content area (subclasses add widgets here)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        self._layout.addLayout(self.content_layout)

        # Stretch to push everything to the top
        self._layout.addStretch()

        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

    def add_widget(self, widget: QWidget):
        """Add a widget to the settings panel."""
        self.content_layout.addWidget(widget)

    def add_row(self, *widgets: QWidget):
        """Add widgets in a horizontal row."""
        from PySide6.QtWidgets import QHBoxLayout
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        for w in widgets:
            row_layout.addWidget(w)
        self.content_layout.addWidget(row)

