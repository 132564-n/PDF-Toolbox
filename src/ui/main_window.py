"""
Main application window for PDF Toolbox.

Layout:
┌──────────────────────────────────────────────────────────────┐
│ Menu Bar                                                      │
├──────────────────────────────────────────────────────────────┤
│ Toolbar                                                       │
├──────────┬──────────────────────────────┬────────────────────┤
│          │                              │                    │
│ Module   │   Drop Zone + File List      │   Settings Panel   │
│ Tabs     │                              │   (per-module)     │
│          │                              │                    │
├──────────┴──────────────────────────────┴────────────────────┤
│ Status Bar                                                    │
└──────────────────────────────────────────────────────────────┘
"""

import os
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar,
    QLabel, QPushButton, QMessageBox, QFileDialog,
    QTabWidget, QStackedWidget, QProgressBar,
    QApplication, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QKeySequence

from src import __app_name__, __version__
from src.utils.logger import logger
from src.utils.thread import ThreadManager
from src.license import check_activation, get_machine_id
from src.license.validator import validate_license, save_activation
from src.modules import MODULES
from src.modules.base import BaseModule
from src.ui.widgets import DropZone, FileListWidget


class MainWindow(QMainWindow):
    """Main application window."""

    MIN_WIDTH = 1050
    MIN_HEIGHT = 650

    def __init__(self):
        super().__init__()
        self._thread_manager = ThreadManager()
        self._current_module: BaseModule = None
        self._settings_panel: QWidget = None
        self._is_activated = False

        # Show activation dialog first
        if not check_activation():
            self._show_activation_dialog()

        self._init_modules()
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._connect_signals()

        # Select first module by default
        if self._modules:
            first_name = list(self._modules.keys())[0]
            self._select_module(first_name)

        logger.info(f"{__app_name__} v{__version__} started")

    # ================================================================
    # Initialization
    # ================================================================

    def _init_modules(self):
        """Initialize all available processing modules."""
        self._modules: dict[str, BaseModule] = {}
        for key, module_cls in MODULES.items():
            try:
                self._modules[key] = module_cls()
                logger.debug(f"Module loaded: {module_cls.name}")
            except Exception as e:
                logger.error(f"Failed to load module {key}: {e}")

    def _setup_ui(self):
        """Build the main UI layout."""
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resize(1200, 750)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ============================================================
        # LEFT SIDEBAR — Module Tabs
        # ============================================================
        left_panel = QWidget()
        left_panel.setFixedWidth(90)
        left_panel.setStyleSheet("""
            QWidget#leftPanel {
                background-color: #181825;
                border-right: 1px solid #313244;
            }
        """)
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 12, 6, 12)
        left_layout.setSpacing(6)

        # Module buttons
        self._module_buttons: dict[str, QPushButton] = {}
        for key, module in self._modules.items():
            btn = QPushButton(f"{module.icon}\n{module.name}")
            btn.setToolTip(module.description)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    color: #a6adc8;
                    font-size: 11px;
                    padding: 12px 6px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #313244;
                    color: #cdd6f4;
                }
                QPushButton:checked {
                    background-color: #1e66f5;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(
                lambda checked, k=key: self._select_module(k)
            )
            self._module_buttons[key] = btn
            left_layout.addWidget(btn)

        left_layout.addStretch()

        # Version label at bottom
        version_label = QLabel(f"v{__version__}")
        version_label.setStyleSheet("color: #585b70; font-size: 10px;")
        version_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(version_label)

        main_layout.addWidget(left_panel)

        # ============================================================
        # CENTER — Drop Zone + File List
        # ============================================================
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(10)

        # Drop zone (shown when file list is empty or always visible)
        self.drop_zone = DropZone()
        center_layout.addWidget(self.drop_zone)

        # File list
        self.file_list = FileListWidget()
        center_layout.addWidget(self.file_list)

        # Action bar (below file list)
        action_bar = QWidget()
        action_bar_layout = QHBoxLayout(action_bar)
        action_bar_layout.setContentsMargins(0, 4, 0, 0)

        self.btn_add_files = QPushButton("📁 添加文件")
        self.btn_add_files.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """)
        action_bar_layout.addWidget(self.btn_add_files)

        action_bar_layout.addStretch()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        action_bar_layout.addWidget(self.progress_bar)

        # Output directory selector
        self.output_dir_label = QLabel("输出目录:")
        self.output_dir_label.setStyleSheet("font-size: 12px; color: #a6adc8;")
        action_bar_layout.addWidget(self.output_dir_label)

        self.output_dir_btn = QPushButton("📂 选择")
        self.output_dir_btn.setStyleSheet(self.btn_add_files.styleSheet())
        self.output_dir_btn.clicked.connect(self._select_output_dir)
        action_bar_layout.addWidget(self.output_dir_btn)

        self._output_dir = os.path.expanduser("~\\Documents\\PDFToolbox_Output")
        os.makedirs(self._output_dir, exist_ok=True)

        # Start button
        self.btn_start = QPushButton("🚀 开始处理")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setMinimumWidth(120)
        action_bar_layout.addWidget(self.btn_start)

        center_layout.addWidget(action_bar)
        main_layout.addWidget(center_panel, stretch=1)

        # ============================================================
        # RIGHT PANEL — Module Settings
        # ============================================================
        self.right_panel = QWidget()
        self.right_panel.setMinimumWidth(290)
        self.right_panel.setMaximumWidth(340)
        self.right_panel.setStyleSheet("""
            QWidget#rightPanel {
                background-color: #181825;
                border-left: 1px solid #313244;
            }
        """)
        self.right_panel.setObjectName("rightPanel")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for different module settings
        self._settings_stack = QStackedWidget()
        self.right_layout.addWidget(self._settings_stack)

        main_layout.addWidget(self.right_panel)

    def _setup_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("添加文件(&A)...\tCtrl+O", self._on_add_files)
        file_menu.addSeparator()
        file_menu.addAction("退出(&X)\tAlt+F4", self.close)

        # Edit menu
        edit_menu = menubar.addMenu("编辑(&E)")
        edit_menu.addAction("清空列表(&C)", self.file_list.clear_files)
        edit_menu.addAction("移除选中(&R)\tDel",
                            self.file_list.remove_selected)

        # Tools menu
        tools_menu = menubar.addMenu("工具(&T)")
        for key, module in self._modules.items():
            action = QAction(f"{module.icon} {module.name}", self)
            action.triggered.connect(
                lambda checked, k=key: self._select_module(k)
            )
            tools_menu.addAction(action)

        # Help menu
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("使用教程(&H)", self._show_help)
        help_menu.addAction("关于(&A)", self._show_about)

    def _setup_toolbar(self):
        """Create the toolbar with quick actions."""
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))

        toolbar.addAction("📁 添加", self._on_add_files)
        toolbar.addAction("🗑️ 清空", self.file_list.clear_files)
        toolbar.addSeparator()
        toolbar.addAction("📂 输出", self._select_output_dir)
        toolbar.addSeparator()

        # Module quick-switch
        for key, module in self._modules.items():
            action = QAction(f"{module.icon} {module.name}", self)
            action.triggered.connect(
                lambda checked, k=key: self._select_module(k)
            )
            toolbar.addAction(action)

    def _setup_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

    def _connect_signals(self):
        """Connect all widget signals."""
        # Drop zone
        self.drop_zone.files_dropped.connect(self._on_files_dropped)

        # File list
        self.btn_add_files.clicked.connect(self._on_add_files)

        # Start button
        self.btn_start.clicked.connect(self._on_start_processing)

        # File count change
        self.file_list.files_changed.connect(self._on_file_count_changed)

    # ================================================================
    # Module Selection
    # ================================================================

    def _select_module(self, module_key: str):
        """Switch to a different processing module."""
        if module_key not in self._modules:
            logger.warning(f"Unknown module: {module_key}")
            return

        # Update button states
        for key, btn in self._module_buttons.items():
            btn.setChecked(key == module_key)

        # Set current module
        self._current_module = self._modules[module_key]
        logger.info(f"Switched to module: {self._current_module.name}")

        # Update settings panel
        if self._settings_panel:
            self._settings_stack.removeWidget(self._settings_panel)

        self._settings_panel = self._current_module.create_settings_panel()
        if self._settings_panel:
            self._settings_stack.addWidget(self._settings_panel)

        # Update start button text
        self.btn_start.setText(f"🚀 {self._current_module.name}")

        # Update status
        self.status_label.setText(
            f"当前模式: {self._current_module.name} | "
            f"{self._current_module.description}"
        )

    # ================================================================
    # File Management
    # ================================================================

    def _on_files_dropped(self, files: list[str]):
        """Handle files dropped or selected via drop zone."""
        added = self.file_list.add_files(files)
        if added > 0:
            self.status_label.setText(
                f"已添加 {added} 个文件，"
                f"共 {self.file_list.file_count} 个"
            )

    def _on_add_files(self):
        """Open file dialog to add files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文件",
            os.path.expanduser("~\\Desktop"),
            "支持的文件 (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp);;"
            "PDF 文件 (*.pdf);;"
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);;"
            "所有文件 (*.*)",
        )
        if files:
            self._on_files_dropped(files)

    def _on_file_count_changed(self, count: int):
        """Update UI when file count changes."""
        self.btn_start.setEnabled(count > 0)
        self.drop_zone.setVisible(count == 0)

    def _select_output_dir(self):
        """Select output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self._output_dir
        )
        if dir_path:
            self._output_dir = dir_path
            self.status_label.setText(
                f"输出目录: {self._output_dir}"
            )

    # ================================================================
    # Processing
    # ================================================================

    def _on_start_processing(self):
        """Start PDF processing with current module."""
        if not self._current_module:
            QMessageBox.warning(self, "提示", "请先选择一个处理模块")
            return

        files = self.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "提示", "请先添加要处理的文件")
            return

        # Ensure output directory exists
        os.makedirs(self._output_dir, exist_ok=True)

        # Get settings from the settings panel
        settings = {}
        if hasattr(self._settings_panel, 'get_settings'):
            settings = self._settings_panel.get_settings()

        # Disable start button during processing
        self.btn_start.setEnabled(False)
        self.btn_start.setText("⏳ 处理中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在处理...")

        # Run in background thread
        self._thread_manager.run(
            target=self._current_module.process,
            args=(files, self._output_dir),
            kwargs=settings,
            on_finished=self._on_processing_finished,
            on_error=self._on_processing_error,
            on_progress=self._on_processing_progress,
            on_status=self._on_processing_status,
        )

    def _on_processing_progress(self, progress: int):
        """Update progress bar."""
        self.progress_bar.setValue(progress)

    def _on_processing_status(self, status: str):
        """Update status label."""
        self.status_label.setText(status)

    def _on_processing_finished(self, result: dict):
        """Handle processing completion."""
        self.btn_start.setEnabled(True)
        self.btn_start.setText(f"🚀 {self._current_module.name}")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(100)

        if result.get("success"):
            output_files = result.get("output_files", [])
            stats = result.get("stats", {})
            count = len(output_files)

            msg = f"处理完成！\n\n"
            msg += f"生成文件: {count} 个\n"
            if stats:
                for key, val in stats.items():
                    if isinstance(val, int) and key.endswith("size"):
                        msg += f"{key}: {self._format_size(val)}\n"
                    else:
                        msg += f"{key}: {val}\n"
            msg += f"\n输出目录: {self._output_dir}"

            reply = QMessageBox.information(
                self, "处理完成", msg,
                QMessageBox.Ok | QMessageBox.Open
            )
            if reply == QMessageBox.Open:
                os.startfile(self._output_dir)

            self.status_label.setText(
                f"处理完成 — 生成 {count} 个文件"
            )
            logger.info(f"Processing completed: {count} files generated")
        else:
            errors = result.get("errors", [])
            error_msg = "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... 还有 {len(errors) - 5} 个错误"

            QMessageBox.critical(
                self, "处理出错",
                f"处理过程中出现错误:\n\n{error_msg}"
            )
            self.status_label.setText("处理出错")
            logger.error(f"Processing failed: {error_msg}")

    def _on_processing_error(self, error_info: tuple):
        """Handle processing errors."""
        self.btn_start.setEnabled(True)
        self.btn_start.setText(f"🚀 {self._current_module.name}")
        self.progress_bar.setVisible(False)

        exc_type, exc_value, traceback_str = error_info
        QMessageBox.critical(
            self, "严重错误",
            f"发生未预期的错误:\n\n{exc_value}\n\n"
            f"请查看日志获取详细信息。"
        )
        self.status_label.setText("发生错误")
        logger.error(f"Unexpected error: {exc_value}\n{traceback_str}")

    # ================================================================
    # Activation
    # ================================================================

    def _show_activation_dialog(self):
        """Show the activation/license dialog."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout,
            QLabel, QLineEdit, QPushButton,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("激活 PDF Toolbox")
        dialog.setFixedSize(480, 360)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        # Title
        title = QLabel("🔐 激活 PDF Toolbox")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Machine ID
        machine_id = get_machine_id()
        mid_label = QLabel("您的机器码：")
        mid_label.setStyleSheet("font-size: 12px; color: #a6adc8;")
        layout.addWidget(mid_label)

        mid_value = QLineEdit(machine_id)
        mid_value.setReadOnly(True)
        mid_value.setStyleSheet("""
            QLineEdit {
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        layout.addWidget(mid_value)

        # Copy button
        copy_btn = QPushButton("📋 复制机器码")
        copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(machine_id)
        )
        layout.addWidget(copy_btn)

        # Activation code input
        layout.addWidget(QLabel("输入激活码："))
        license_input = QLineEdit()
        license_input.setPlaceholderText("PDFTB-XXXXX-XXXXX-XXXXX-XXXXX")
        license_input.setStyleSheet("""
            QLineEdit {
                font-family: 'Consolas', monospace;
                font-size: 13px;
                padding: 10px;
            }
        """)
        layout.addWidget(license_input)

        # Message label
        msg_label = QLabel("")
        msg_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
        layout.addWidget(msg_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        trial_btn = QPushButton("免费试用")
        trial_btn.clicked.connect(dialog.accept)  # Allow trial without activation
        btn_layout.addWidget(trial_btn)

        activate_btn = QPushButton("激活")
        activate_btn.setObjectName("primaryBtn")

        def do_activate():
            code = license_input.text().strip()
            if not code:
                msg_label.setText("请输入激活码")
                return

            result = validate_license(code)
            if result["valid"]:
                save_activation(code)
                self._is_activated = True
                dialog.accept()
                QMessageBox.information(
                    self, "激活成功",
                    "🎉 激活成功！感谢您的支持！\n\n"
                    "PDF Toolbox 全部功能已解锁。"
                )
            else:
                msg_label.setText(f"❌ {result['message']}")

        activate_btn.clicked.connect(do_activate)
        btn_layout.addWidget(activate_btn)
        layout.addLayout(btn_layout)

        # Tip
        tip = QLabel(
            "💡 购买激活码后，将机器码发送给客服即可获取激活码。\n"
            "   未激活状态下可免费试用部分功能。"
        )
        tip.setStyleSheet("color: #6c7086; font-size: 11px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        dialog.exec()

    # ================================================================
    # Help / About
    # ================================================================

    def _show_help(self):
        """Show help/tutorial."""
        QMessageBox.information(
            self, "使用教程",
            "📖 PDF Toolbox 使用教程\n\n"
            "1. 从左侧选择处理模式\n"
            "2. 拖拽或点击添加文件\n"
            "3. 在右侧调整处理参数\n"
            "4. 选择输出目录\n"
            "5. 点击「开始处理」\n\n"
            "💡 提示：支持批量处理多个文件，\n"
            "       也支持直接拖拽文件夹。"
        )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, f"关于 {__app_name__}",
            f"<h3>{__app_name__}</h3>"
            f"<p>版本: {__version__}</p>"
            f"<p>一款功能全面的 PDF 处理工具。</p>"
            f"<p>支持 PDF 编辑、转换、压缩、加密、水印等功能。</p>"
            f"<br>"
            f"<p>© 2026 PDFToolbox. All rights reserved.</p>"
        )

    # ================================================================
    # Utilities
    # ================================================================

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def closeEvent(self, event):
        """Handle window close event."""
        self._thread_manager.cancel_all()
        logger.info(f"{__app_name__} shutting down")
        event.accept()

