# 技术选型分析

## 一、语言 & GUI 框架

### 方案对比

| 维度 | Python + PySide6 ✅ | C# + WPF | Electron + JS |
|------|---------------------|----------|---------------|
| 开发速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| PDF库成熟度 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 安装包大小 | ~80MB | ~5MB | ~180MB |
| 内存占用 | ~100MB | ~50MB | ~300MB |
| 代码保护难度 | 中（Cython可解决） | 低（.NET编译） | 高（JS易反编译） |
| 商业授权 | LGPL（友好） | MIT | MIT |
| 跨平台 | 可 | 仅Windows | 可 |
| 学习成本 | 低 | 中 | 中 |

### 最终选择：Python 3.11 + PySide6

> **决策核心**：
> - 你是个人开发者，**开发速度 > 一切**，Python 2周能搞定的，C#可能要1个月
> - PDF 处理库 Python 最丰富（pypdf、pdfplumber、reportlab、pdf2docx）
> - 安装包 80MB 在2026年完全可以接受
> - PySide6 是 Qt 官方支持的 Python 绑定，**LGPL 协议允许商业闭源**，不像 PyQt 的 GPL
> - 核心模块用 **Cython 编译成 .pyd**，保护代码不被反编译

---

## 二、核心依赖库

### PDF 处理引擎

| 库 | 用途 | 版本 | 备注 |
|-----|------|------|------|
| `pypdf` | PDF读写、合并、拆分、加密、元数据 | 5.x | 纯Python，零依赖 |
| `pdfplumber` | 提取文字、表格、图片 | 0.11+ | 基于pdfminer.six |
| `pdf2docx` | PDF → Word 转换 | 0.5.6+ | 转换质量最好的开源库 |
| `reportlab` | 生成PDF（图片转PDF等） | 4.x | 老牌稳定 |
| `Pillow` | 图片处理、格式转换 | 11.x | 图片转PDF、缩略图 |
| `pytesseract` | OCR文字识别 | 0.3+ | 需捆绑 Tesseract-OCR |

> ⚠️ **关于 pymupdf (fitz)**：它是工业级最强的PDF库，但是 **AGPL 协议**，商业闭源使用需要购买授权（约 $500/年）。
> **初期用 pdfplumber + pypdf 替代，后期赚到钱再买 pymupdf 授权提升体验**。

### GUI 相关

| 库 | 用途 |
|-----|------|
| `PySide6` | Qt GUI框架 |
| `qdarkstyle` | 现代化暗色主题 |

### 工程支撑

| 库 | 用途 |
|-----|------|
| `pyinstaller` | 打包成单个 exe |
| `Cython` | 核心代码编译成 .pyd 防反编译 |
| `cryptography` | RSA签名验证（激活系统） |
| `loguru` | 日志记录 |

---

## 三、最终依赖清单 (requirements.txt)

```
# PDF 核心
pypdf>=5.0
pdfplumber>=0.11.0
pdf2docx>=0.5.6
reportlab>=4.2
Pillow>=11.0
pytesseract>=0.3.13

# GUI
PySide6>=6.7
qdarkstyle>=3.2

# 工程
pyinstaller>=6.0
cryptography>=43.0
loguru>=0.7.0
Cython>=3.0
```

---

## 四、开发环境配置

| 项 | 配置 |
|-----|------|
| Python版本 | 3.11.x（兼容性最好） |
| 虚拟环境 | `venv` |
| IDE | VS Code + PyLance |
| 版本管理 | Git |
| 目标平台 | Windows 10/11 |
| 测试环境 | Windows Sandbox 沙盒 |

---

## 五、为什么不选其他方案？

| 被否决方案 | 原因 |
|-------------|------|
| PyQt6 | **GPL协议**，商用必须开源或购买 $550/年授权 |
| Tkinter | 界面太丑，2026年卖不出价格 |
| Flutter Desktop | PDF库不成熟，调用系统API受限 |
| WPF | 开发周期长，PDF库需付费(iTextSharp等) |
| Electron | 包太大、内存高、JS代码保护难 |
| 纯C++/Qt | 开发效率低，个人维护成本高 |
