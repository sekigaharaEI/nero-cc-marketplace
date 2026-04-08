# 环境准备

## 1. 网络环境检查

**NotebookLM 是 Google 服务，中国大陆用户需要 VPN 才能访问。**

在开始前提示用户：

```
注意：NotebookLM 是 Google 的服务。
- 如果你在中国大陆，需要先开启 VPN/代理 才能正常使用
- 如果你在海外或已开启 VPN，可以继续

请确认网络环境已准备好。
```

## 2. 运行环境检查脚本

```bash
python scripts/check_env.py
```

脚本输出 JSON，包含以下字段：

| 字段 | 含义 | 用途 |
|------|------|------|
| `notebooklm_found` | notebooklm CLI 是否已安装 | false 时进入步骤3安装 |
| `notebooklm_cmd` | notebooklm 命令路径 | 后续所有命令使用此路径 |
| `playwright_found` | Playwright chromium 是否可用 | false 时单独安装 |
| `auth_ok` | notebooklm 是否已认证 | false 时提示登录 |
| `python_found` | Python 是否可用 | false 时安装 Python |
| `python_version` | Python 版本号 | 信息展示 |
| `pymupdf_found` | PyMuPDF 是否已安装 | false 时安装 |
| `pymupdf_version` | PyMuPDF 版本号 | 信息展示 |
| `platform` | 操作系统 | 选择对应平台的安装命令 |

**`notebooklm_found`、`playwright_found`、`auth_ok`、`pymupdf_found` 四项全部为 true → 环境就绪，直接进入步骤2（收集用户输入）。**

任一为 false → 按下方流程处理对应缺失项。多项为 false 时依次处理。

## 3. 安装 notebooklm（仅在 `notebooklm_found=false` 时执行）

### 3.1 检查 Python

如果 `python_found=false`，根据 `platform` 字段安装：

```bash
# windows
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements

# darwin (macOS)
brew install python3

# linux (Ubuntu/Debian)
sudo apt update && sudo apt install -y python3 python3-pip
```

### 3.2 安装 notebooklm

```bash
# Windows
pip install "notebooklm-py[browser]"

# macOS/Linux
pip3 install "notebooklm-py[browser]"
```

### 3.3 安装 Playwright（仅在 `playwright_found=false` 时执行）

```bash
pip install playwright && playwright install chromium
```

### 3.4 登录认证（仅在 `auth_ok=false` 时执行）

提示用户运行 `notebooklm login` 登录。

**⚠️ 重要提醒：浏览器登录成功后，必须回到终端按 Enter 键确认。不按 Enter 认证信息不会写入持久化文件，下次仍需重新登录。**

## 4. 安装 PyMuPDF（仅在 `pymupdf_found=false` 时执行）

```bash
# 所有平台通用
pip install PyMuPDF
```

PyMuPDF 是纯 Python 包，无需额外的系统依赖，所有平台安装方式一致。
