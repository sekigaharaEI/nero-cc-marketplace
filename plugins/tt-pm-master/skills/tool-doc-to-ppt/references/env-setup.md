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

## 2. 检查并安装依赖

### 2.1 检测 notebooklm 是否已安装

**先检测 notebooklm 是否已存在（全局 + 虚拟环境都检测）**：

```powershell
# === Windows PowerShell ===
$NOTEBOOKLM_PATH = $null

# 1. 检查全局
if (Get-Command notebooklm -ErrorAction SilentlyContinue) {
    $NOTEBOOKLM_PATH = "global"
}

# 2. 检查虚拟环境
if ($env:VIRTUAL_ENV) {
    $venvCmd = "$env:VIRTUAL_ENV\Scripts\notebooklm.exe"
    if (Test-Path $venvCmd) {
        $NOTEBOOKLM_PATH = $venvCmd
    } elseif (& "$env:VIRTUAL_ENV\Scripts\python.exe" -m notebooklm --version 2>$null) {
        $NOTEBOOKLM_PATH = "venv-module"
    }
} elseif ($env:CONDA_PREFIX) {
    $condaCmd = "$env:CONDA_PREFIX\Scripts\notebooklm.exe"
    if (Test-Path $condaCmd) {
        $NOTEBOOKLM_PATH = $condaCmd
    }
}
```

```bash
# === macOS/Linux ===
NOTEBOOKLM_PATH=""

# 1. 检查全局
if command -v notebooklm &>/dev/null; then
    NOTEBOOKLM_PATH="global"
fi

# 2. 检查虚拟环境
if [ -n "$VIRTUAL_ENV" ]; then
    if [ -x "$VIRTUAL_ENV/bin/notebooklm" ]; then
        NOTEBOOKLM_PATH="$VIRTUAL_ENV/bin/notebooklm"
    elif "$VIRTUAL_ENV/bin/python" -m notebooklm --version &>/dev/null; then
        NOTEBOOKLM_PATH="venv-module"
    fi
elif [ -n "$CONDA_PREFIX" ]; then
    if [ -x "$CONDA_PREFIX/bin/notebooklm" ]; then
        NOTEBOOKLM_PATH="$CONDA_PREFIX/bin/notebooklm"
    fi
fi
```

**检测结果处理**：

- **找到 notebooklm** → 直接跳到"检查认证状态"（步骤3），无需安装
- **未找到** → 进入步骤 2.2

### 2.2 询问是否已安装到虚拟环境（仅在未检测到时执行）

```json
{
  "questions": [{
    "question": "未检测到 notebooklm，是否之前已安装到虚拟环境？",
    "header": "安装状态",
    "options": [
      {"label": "是，装在虚拟环境", "description": "之前安装到了虚拟环境，但当前未激活"},
      {"label": "否，需要安装", "description": "从未安装过，需要现在安装"}
    ],
    "multiSelect": false
  }]
}
```

**选择"是，装在虚拟环境"** → 询问虚拟环境路径：

直接在对话中询问用户：`请输入虚拟环境的路径（例如 /Users/xxx/myenv 或 C:\Users\xxx\myenv）：`

用户输入路径后，**验证路径有效性**：

```powershell
# === Windows ===
$VENV_PATH = "用户输入的路径"
$notebooklmExe = "$VENV_PATH\Scripts\notebooklm.exe"
if (Test-Path $notebooklmExe) {
    Write-Host "找到 notebooklm: $notebooklmExe"
    $NOTEBOOKLM_CMD = $notebooklmExe
} elseif (Test-Path "$VENV_PATH\Scripts\python.exe") {
    if (& "$VENV_PATH\Scripts\python.exe" -m notebooklm --version 2>$null) {
        Write-Host "找到 notebooklm (模块模式)"
        $NOTEBOOKLM_CMD = "$VENV_PATH\Scripts\python.exe -m notebooklm"
    }
}
```

```bash
# === macOS/Linux ===
VENV_PATH="用户输入的路径"
if [ -x "$VENV_PATH/bin/notebooklm" ]; then
    echo "找到 notebooklm: $VENV_PATH/bin/notebooklm"
    NOTEBOOKLM_CMD="$VENV_PATH/bin/notebooklm"
elif [ -x "$VENV_PATH/bin/python" ]; then
    if "$VENV_PATH/bin/python" -m notebooklm --version &>/dev/null; then
        echo "找到 notebooklm (模块模式)"
        NOTEBOOKLM_CMD="$VENV_PATH/bin/python -m notebooklm"
    fi
fi
```

**验证结果处理**：
- **验证成功** → 记录 `NOTEBOOKLM_CMD`，后续所有命令都使用绝对路径，跳到"检查认证状态"
- **验证失败** → 提示用户路径无效，重新询问或选择安装

**后续命令使用绝对路径**（不需要激活虚拟环境）：
```bash
# macOS/Linux
/Users/xxx/myenv/bin/notebooklm auth check --json
/Users/xxx/myenv/bin/notebooklm create "笔记本名" --json

# Windows
C:\Users\xxx\myenv\Scripts\notebooklm.exe auth check --json
C:\Users\xxx\myenv\Scripts\notebooklm.exe create "笔记本名" --json
```

**选择"否，需要安装"** → 继续步骤 2.3

### 2.3 确定安装位置（仅在需要安装时执行）

**检测当前是否在虚拟环境中**：

```powershell
# === Windows ===
if ($env:VIRTUAL_ENV) {
    $DETECTED_VENV = $env:VIRTUAL_ENV; $VENV_TYPE = "venv"
} elseif ($env:CONDA_PREFIX) {
    $DETECTED_VENV = $env:CONDA_PREFIX; $VENV_TYPE = "conda"
} else {
    $DETECTED_VENV = $null
}
```

```bash
# === macOS/Linux ===
if [ -n "$VIRTUAL_ENV" ]; then
    DETECTED_VENV="$VIRTUAL_ENV"; VENV_TYPE="venv"
elif [ -n "$CONDA_PREFIX" ]; then
    DETECTED_VENV="$CONDA_PREFIX"; VENV_TYPE="conda"
else
    DETECTED_VENV=""
fi
```

**如果检测到虚拟环境，询问安装位置**：

```json
{
  "questions": [{
    "question": "检测到虚拟环境，notebooklm 安装到哪里？",
    "header": "安装位置",
    "options": [
      {"label": "当前虚拟环境（推荐）", "description": "安装到当前激活的虚拟环境，后续使用需激活此环境"},
      {"label": "全局环境", "description": "安装到系统全局 Python，任何地方都能用"}
    ],
    "multiSelect": false
  }]
}
```

- 选择"当前虚拟环境" → `INSTALL_TO_VENV=true`
- 选择"全局环境" → `INSTALL_TO_VENV=false`
- 未检测到虚拟环境 → 自动 `INSTALL_TO_VENV=false`

| 环境变量 | 含义 |
|----------|------|
| `$VIRTUAL_ENV` | Python venv/virtualenv 虚拟环境路径 |
| `$CONDA_PREFIX` | Conda/Miniconda/Anaconda 环境路径 |

### 2.4 检查 Python 环境（仅在需要安装时执行）

```powershell
# === Windows ===
if ($INSTALL_TO_VENV) {
    & "$DETECTED_VENV\Scripts\python.exe" --version
} else {
    python --version
}
```

```bash
# === macOS/Linux ===
if [ "$INSTALL_TO_VENV" = true ]; then
    "$DETECTED_VENV/bin/python" --version
else
    python3 --version 2>/dev/null || python --version 2>/dev/null
fi
```

**如果 Python 不存在**：

- **虚拟环境中无 Python**：提示检查虚拟环境配置
- **全局环境无 Python**：根据操作系统自动安装

```bash
# Windows（winget）
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements

# macOS（Homebrew）
brew install python3

# Linux Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-pip

# Linux CentOS/RHEL
sudo yum install -y python3 python3-pip
```

**自动安装失败时**提示用户手动安装 Python 3.10+。

### 2.5 安装 notebooklm（仅在需要安装时执行）

```bash
# 安装到虚拟环境
# Windows:  & "$DETECTED_VENV\Scripts\pip.exe" install "notebooklm-py[browser]"
# Unix:     "$DETECTED_VENV/bin/pip" install "notebooklm-py[browser]"

# 安装到全局环境
# Windows:  pip install "notebooklm-py[browser]"
# Unix:     pip3 install "notebooklm-py[browser]"

# 安装 Playwright（两种环境通用）
pip install playwright && playwright install chromium
```

| 用户选择 | 安装位置 | pip 命令 | 后续使用要求 |
|----------|----------|----------|--------------|
| 当前虚拟环境 | 虚拟环境内 | `$DETECTED_VENV/bin/pip` | 需激活同一虚拟环境 |
| 全局环境 | 系统 Python | `pip3` (Unix) / `pip` (Windows) | 无特殊要求 |

安装完成后，提示用户运行 `notebooklm login` 登录。

## 3. 检查认证状态

```bash
notebooklm auth check --json
```

如果未认证，提示用户运行 `notebooklm login`。
