# 激活码系统设计（方案 A：离线校验）

## 一、激活流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   用户        │     │   你(开发者)  │     │   软件        │
├──────────────┤     ├──────────────┤     ├──────────────┤
│              │     │              │     │              │
│ 1.安装软件   │     │              │     │              │
│              │     │              │     │              │
│ 2.打开软件   │     │              │     │ 3.弹窗要求   │
│  看到机器码  │────→│              │     │  输入激活码  │
│  发给客服    │     │              │     │              │
│              │     │ 4.用私钥签名  │     │              │
│              │     │  生成激活码   │     │              │
│              │     │              │     │              │
│ 5.收到激活码 │←────│              │     │              │
│              │     │              │     │              │
│ 6.输入激活码 │     │              │     │ 7.公钥验签   │
│              │     │              │     │  比对机器码  │
│              │     │              │     │              │
│              │     │              │     │ 8.✅ 激活成功 │
│              │     │              │     │  写入本地文件 │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 二、激活码格式

```
PDFTB-XXXXX-XXXXX-XXXXX-XXXXX
  │      │      │      │      │
  │      └──────┴──────┴──────┘
  │           Base32 编码的签名数据
  │
  └── 产品前缀（PDF ToolBox）
```

**示例**：`PDFTB-3HK7M-NP9Q2-WR5XC-D8JVF`

> Base32 编码后 25 位 + 4 个分隔符，比 Base64 好看，不含容易混淆的字符(0/O/1/I/L)

---

## 三、激活码内容（签名前的原始数据）

```json
{
  "mid": "a1b2c3d4e5f6...",     // 机器码 MD5（32位）
  "ver": 1,                       // 激活码版本（方便后续升级算法）
  "feat": ["all"],                // 功能权限（预留分级）
  "iat": "2026-07-01T12:00:00",   // 签发时间
  "exp": null,                    // 过期时间（null=终身，否则按日期）
  "non": "x7k3m"                  // 随机数，确保同机器每次激活码不同
}
```

---

## 四、技术实现

### 4.1 生成 RSA 密钥对

```bash
# 在你的开发机上执行（做一次就行）
openssl genpkey -algorithm RSA -out private_key.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in private_key.pem -out public_key.pem

# private_key.pem  → 你自己保管，绝！对！不！能！泄！露！
# public_key.pem   → 跟软件打包在一起，用于验证
```

### 4.2 机器码生成 (machine.py)

```python
import hashlib
import subprocess
import uuid

def get_machine_id() -> str:
    """生成唯一机器码"""
    # 来源1: CPU序列号
    cpu = subprocess.getoutput(
        "wmic cpu get processorid"
    ).strip().split("\\n")[-1]

    # 来源2: 主板序列号
    board = subprocess.getoutput(
        "wmic baseboard get serialnumber"
    ).strip().split("\\n")[-1]

    # 来源3: MAC地址
    mac = hex(uuid.getnode())

    # 组合后MD5
    raw = f"{cpu}|{board}|{mac}"
    return hashlib.md5(raw.encode()).hexdigest()
```

> ⚠️ **容错设计**：如果某项获取失败（虚拟机环境），用另两项 + 硬盘序列号兜底，但至少匹配 2 项才算有效机器码。

### 4.3 激活码生成器 (gen_license.py) —— 你本地运行

```python
import json
import base64
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import secrets

def generate_license(machine_id: str) -> str:
    """用私钥签名，生成激活码"""

    # 1. 构建数据
    payload = {
        "mid": machine_id,
        "ver": 1,
        "feat": ["all"],
        "iat": datetime.utcnow().isoformat(),
        "exp": None,  # None = 终身
        "non": secrets.token_hex(3)
    }

    # 2. 序列化
    data = json.dumps(payload, separators=(',', ':')).encode()

    # 3. 用私钥签名
    with open("private_key.pem", "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None
        )

    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    # 4. 数据+签名合并，Base32编码
    combined = data + b"||" + signature
    encoded = base64.b32encode(combined).decode().rstrip("=")

    # 5. 每5位加分隔符
    formatted = "PDFTB-" + "-".join(
        encoded[i:i+5] for i in range(0, len(encoded), 5)
    )

    return formatted
```

### 4.4 激活验证 (validator.py) —— 打包进软件

```python
import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

# 公钥（硬编码在代码中，Cython编译后更难提取）
_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""

def validate_license(license_key: str, machine_id: str) -> dict:
    """验证激活码，返回 {valid: bool, message: str}"""

    # 1. 去除前缀和分隔符
    code = license_key.replace("PDFTB-", "").replace("-", "")

    # 2. Base32解码（补齐缺失的等号）
    padding_len = 8 - len(code) % 8
    if padding_len != 8:
        code += "=" * padding_len

    try:
        combined = base64.b32decode(code)
    except Exception:
        return {"valid": False, "message": "激活码格式错误"}

    # 3. 分离数据和签名
    parts = combined.split(b"||")
    if len(parts) != 2:
        return {"valid": False, "message": "激活码格式错误"}

    data, signature = parts

    # 4. 验证签名
    public_key = serialization.load_pem_public_key(_PUBLIC_KEY_PEM)
    try:
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except InvalidSignature:
        return {"valid": False, "message": "激活码无效（签名验证失败）"}

    # 5. 解析数据，比对机器码
    payload = json.loads(data)
    if payload.get("mid") != machine_id:
        return {"valid": False, "message": "激活码与当前设备不匹配"}

    # 6. 检查过期
    if payload.get("exp"):
        exp_time = datetime.fromisoformat(payload["exp"])
        if datetime.utcnow() > exp_time:
            return {"valid": False, "message": "激活码已过期"}

    # 7. ✅ 全部通过
    return {"valid": True, "message": "激活成功", "payload": payload}
```

---

## 五、激活状态存储

```python
# 激活成功后，写入本地文件（加密存储）
import json
import base64
from pathlib import Path

def save_activation(license_key: str, machine_id: str):
    """激活成功后保存状态"""
    # 文件路径：%APPDATA%/PDFToolbox/activation.dat
    data_dir = Path.home() / "AppData" / "Roaming" / "PDFToolbox"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 简单混淆存储（不是强加密，只是防止一眼看到）
    data = json.dumps({
        "lk": license_key,
        "mi": machine_id
    })
    encoded = base64.b64encode(data.encode()).decode()

    with open(data_dir / "activation.dat", "w") as f:
        f.write(encoded)


def check_activation() -> bool:
    """软件启动时检查激活状态"""
    data_file = (
        Path.home() / "AppData" / "Roaming" /
        "PDFToolbox" / "activation.dat"
    )
    if not data_file.exists():
        return False

    try:
        with open(data_file) as f:
            encoded = f.read()
        data = json.loads(base64.b64decode(encoded))

        current_mid = get_machine_id()
        if data.get("mi") != current_mid:
            return False  # 换了机器

        # 重新验证激活码（防止篡改activation.dat）
        result = validate_license(data["lk"], current_mid)
        return result["valid"]
    except Exception:
        return False
```

---

## 六、激活码管理（你的工作流）

### 简易方案：CSV 记录

| 日期 | 买家昵称 | 机器码 | 激活码 | 平台 | 金额 |
|------|---------|--------|--------|------|------|
| 2026-07-01 | 张三*** | a1b2c3... | PDFTB-3HK7M-... | 淘宝 | 29.9 |
| 2026-07-02 | 李四*** | d4e5f6... | PDFTB-7XP2Q-... | 闲鱼 | 19.9 |

### 你的操作步骤

```
1. 用户购买后联系你，发送机器码
2. 你运行 gen_license.py，输入机器码
3. 复制生成的激活码，发给用户
4. 在 CSV 中记录一笔
```

> 后期可以做一个简单的网页管理后台（Flask 单文件），但初期 CSV 完全够用。

---

## 七、安全强化措施

| 层级 | 措施 | 说明 |
|------|------|------|
| 编译保护 | `validator.py` 用 Cython 编译成 `.pyd` | 核心验证逻辑不暴露 Python 源码 |
| 公钥隐藏 | 公钥拆分成多段存储在代码不同位置 | 增加提取难度 |
| 反调试 | 检测是否在调试器中运行 | 简单对抗 |
| 多处校验 | 除了启动时校验，每次执行功能时也校验一次 | 防止内存 patch |
| 激活文件加密 | 激活文件用机器码派生密钥 AES 加密存储 | 防止复制激活文件 |

---

## 八、用户换电脑怎么办？

**策略**：一个激活码允许解绑 2 次

```
1. 用户在旧电脑点击「解绑」，软件生成解绑码
2. 用户把解绑码发给你
3. 你验证后，为该用户生成新的激活码
4. 旧激活码在旧电脑上失效
```

> 解绑功能在 Phase 4 之后再实现，初期产品先不管，遇事手动处理。
