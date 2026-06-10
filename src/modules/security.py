"""
PDF Security Module — Encrypt and decrypt PDF files.
"""

import os
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QCheckBox, QGroupBox, QRadioButton, QButtonGroup,
    QMessageBox,
)
from PySide6.QtCore import Signal

from .base import BaseModule, ModuleSettingsPanel
from src.utils.logger import logger


class SecurityModule(BaseModule):
    """PDF encryption and decryption."""

    name = "PDF 安全"
    icon = "🔒"
    description = "设置PDF打开密码、权限密码，移除PDF密码保护"

    MODE_ENCRYPT = "encrypt"
    MODE_DECRYPT = "decrypt"

    def process(self, input_files: list[str], output_dir: str,
                **settings) -> dict:
        """Encrypt or decrypt PDF files."""
        mode = settings.get("mode", self.MODE_ENCRYPT)
        output_files = []
        errors = []
        stats = {"total_pages": 0}

        try:
            if mode == self.MODE_ENCRYPT:
                result = self._encrypt_pdfs(input_files, output_dir, settings)
            elif mode == self.MODE_DECRYPT:
                result = self._decrypt_pdfs(input_files, output_dir, settings)
            else:
                return {"success": False,
                        "errors": [f"未知模式: {mode}"], "stats": stats}

            output_files = result.get("output_files", [])
            errors = result.get("errors", [])
            stats = result.get("stats", stats)
        except Exception as e:
            logger.error(f"Security process error: {e}")
            errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "output_files": output_files,
            "errors": errors,
            "stats": stats,
        }

    def _encrypt_pdfs(self, input_files: list[str], output_dir: str,
                      settings: dict) -> dict:
        """Encrypt PDFs with password protection."""
        output_files = []
        errors = []
        total_pages = 0

        user_pwd = settings.get("user_password", "")
        owner_pwd = settings.get("owner_password", "") or None
        allow_print = settings.get("allow_print", True)
        allow_copy = settings.get("allow_copy", True)
        allow_edit = settings.get("allow_edit", True)

        if not user_pwd:
            return {"output_files": [], "errors": ["请设置用户密码"],
                    "stats": {}}

        # Build permissions flags for pypdf
        from pypdf import PasswordType
        # We'll use user_password and owner_password directly
        # pypdf handles permissions through encrypt parameters

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)
                total = len(reader.pages)
                total_pages += total

                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

                # Encrypt — pypdf's encrypt takes user_pwd, owner_pwd
                # and uses permissions flags
                writer.encrypt(user_pwd, owner_pwd)

                base_name = Path(file_path).stem
                out_path = os.path.join(
                    output_dir, f"{base_name}_encrypted.pdf"
                )
                out_path = self._unique_path(out_path)

                with open(out_path, "wb") as f:
                    writer.write(f)

                output_files.append(out_path)
                logger.info(
                    f"Encrypted: {os.path.basename(file_path)} "
                    f"({total} pages)"
                )

            except Exception as e:
                msg = (f"加密失败 {os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
        }

    def _decrypt_pdfs(self, input_files: list[str], output_dir: str,
                      settings: dict) -> dict:
        """Remove password protection from PDFs."""
        output_files = []
        errors = []
        total_pages = 0

        password = settings.get("password", "")

        if not password:
            return {"output_files": [], "errors": ["请输入PDF密码"],
                    "stats": {}}

        for file_path in input_files:
            try:
                reader = PdfReader(file_path)

                # Check if PDF is encrypted
                if reader.is_encrypted:
                    result = reader.decrypt(password)
                    if result == 0:
                        errors.append(
                            f"密码错误: {os.path.basename(file_path)}"
                        )
                        continue
                else:
                    # Not encrypted, just copy
                    pass

                total = len(reader.pages)
                total_pages += total

                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

                base_name = Path(file_path).stem
                out_path = os.path.join(
                    output_dir, f"{base_name}_decrypted.pdf"
                )
                out_path = self._unique_path(out_path)

                with open(out_path, "wb") as f:
                    writer.write(f)

                output_files.append(out_path)
                logger.info(
                    f"Decrypted: {os.path.basename(file_path)} "
                    f"({total} pages)"
                )

            except Exception as e:
                msg = (f"解密失败 {os.path.basename(file_path)}: {e}")
                logger.error(msg)
                errors.append(msg)

        return {
            "output_files": output_files,
            "errors": errors,
            "stats": {"total_pages": total_pages},
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
        return SecuritySettingsPanel(self)


class SecuritySettingsPanel(ModuleSettingsPanel):
    """Settings panel for PDF security operations."""

    def __init__(self, module: SecurityModule):
        super().__init__("PDF 安全")
        self.module = module

        # Mode selector
        mode_group = QGroupBox("操作模式")
        mode_layout = QVBoxLayout(mode_group)

        self.btn_encrypt = QRadioButton("加密 PDF")
        self.btn_decrypt = QRadioButton("解密 PDF")
        self.btn_encrypt.setChecked(True)

        self._mode_buttons = QButtonGroup(self)
        self._mode_buttons.addButton(self.btn_encrypt, 0)
        self._mode_buttons.addButton(self.btn_decrypt, 1)

        mode_layout.addWidget(self.btn_encrypt)
        mode_layout.addWidget(self.btn_decrypt)
        self.add_widget(mode_group)

        # === Encrypt Settings ===
        self._encrypt_widget = QWidget()
        enc_layout = QVBoxLayout(self._encrypt_widget)
        enc_layout.setContentsMargins(0, 0, 0, 0)

        # User password
        pwd_group = QGroupBox("密码设置")
        pwd_layout = QVBoxLayout(pwd_group)

        pwd_layout.addWidget(QLabel("打开密码:"))
        self.user_pwd_input = QLineEdit()
        self.user_pwd_input.setPlaceholderText("设置PDF打开密码")
        self.user_pwd_input.setEchoMode(QLineEdit.Password)
        pwd_layout.addWidget(self.user_pwd_input)

        pwd_layout.addWidget(QLabel("权限密码 (可选):"))
        self.owner_pwd_input = QLineEdit()
        self.owner_pwd_input.setPlaceholderText("留空则与打开密码相同")
        self.owner_pwd_input.setEchoMode(QLineEdit.Password)
        pwd_layout.addWidget(self.owner_pwd_input)

        enc_layout.addWidget(pwd_group)

        # Permissions
        perm_group = QGroupBox("权限设置")
        perm_layout = QVBoxLayout(perm_group)

        self.chk_print = QCheckBox("允许打印")
        self.chk_print.setChecked(True)
        perm_layout.addWidget(self.chk_print)

        self.chk_copy = QCheckBox("允许复制内容")
        self.chk_copy.setChecked(True)
        perm_layout.addWidget(self.chk_copy)

        self.chk_edit = QCheckBox("允许编辑修改")
        self.chk_edit.setChecked(True)
        perm_layout.addWidget(self.chk_edit)

        enc_layout.addWidget(perm_group)

        # Tip
        tip = QLabel("💡 加密后的PDF需要输入密码才能打开")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #888; font-size: 12px;")
        enc_layout.addWidget(tip)

        self.add_widget(self._encrypt_widget)

        # === Decrypt Settings ===
        self._decrypt_widget = QWidget()
        dec_layout = QVBoxLayout(self._decrypt_widget)
        dec_layout.setContentsMargins(0, 0, 0, 0)

        dec_pwd_group = QGroupBox("输入密码")
        dec_pwd_layout = QVBoxLayout(dec_pwd_group)
        dec_pwd_layout.addWidget(QLabel("PDF密码:"))
        self.decrypt_pwd_input = QLineEdit()
        self.decrypt_pwd_input.setPlaceholderText("输入PDF的打开密码")
        self.decrypt_pwd_input.setEchoMode(QLineEdit.Password)
        dec_pwd_layout.addWidget(self.decrypt_pwd_input)
        dec_layout.addWidget(dec_pwd_group)

        dec_tip = QLabel("💡 解密后会生成一个无密码的新PDF文件")
        dec_tip.setWordWrap(True)
        dec_tip.setStyleSheet("color: #888; font-size: 12px;")
        dec_layout.addWidget(dec_tip)

        self.add_widget(self._decrypt_widget)
        self._decrypt_widget.setVisible(False)

        # Connect signals
        self.btn_encrypt.toggled.connect(
            lambda checked: self._on_mode_changed()
        )
        self.btn_decrypt.toggled.connect(
            lambda checked: self._on_mode_changed()
        )

    def _on_mode_changed(self):
        is_encrypt = self.btn_encrypt.isChecked()
        self._encrypt_widget.setVisible(is_encrypt)
        self._decrypt_widget.setVisible(not is_encrypt)

    def get_settings(self) -> dict:
        if self.btn_encrypt.isChecked():
            return {
                "mode": "encrypt",
                "user_password": self.user_pwd_input.text(),
                "owner_password": self.owner_pwd_input.text(),
                "allow_print": self.chk_print.isChecked(),
                "allow_copy": self.chk_copy.isChecked(),
                "allow_edit": self.chk_edit.isChecked(),
            }
        else:
            return {
                "mode": "decrypt",
                "password": self.decrypt_pwd_input.text(),
            }

