---
description: 将本地文档自动上传到 Google NotebookLM 并生成幻灯片 PDF。当用户说"生成幻灯片"、"文档转PPT"、"做个演示文档"时触发。支持 PDF、Word、Markdown、文本文件等格式。开箱即用，自动检查并安装依赖。支持 Windows/macOS/Linux。
---

# 文档转幻灯片

将本地文档上传到 NotebookLM，自动生成详细版幻灯片 PDF（中文简体）。

## 触发方式

- `/doc-to-slides`
- "帮我把文档生成幻灯片"
- "文档转 PPT"
- "生成演示文档"

## 工作流程

### 0. 网络环境检查（重要）

**NotebookLM 是 Google 服务，中国大陆用户需要 VPN 才能访问。**

在开始前提示用户：
```
注意：NotebookLM 是 Google 的服务。
- 如果你在中国大陆，需要先开启 VPN/代理 才能正常使用
- 如果你在海外或已开启 VPN，可以继续

请确认网络环境已准备好。
```

### 1. 检查并安装依赖（开箱即用）

#### 第一步：检测 notebooklm 是否已安装

**先检测 notebooklm 是否已存在（全局 + 虚拟环境都检测）**：

```bash
# Windows PowerShell - 多位置检测
$NOTEBOOKLM_PATH = $null

# 1. 检查全局
if (Get-Command notebooklm -ErrorAction SilentlyContinue) {
    $NOTEBOOKLM_PATH = "global"
}

# 2. 如果在虚拟环境中，也检查虚拟环境
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

# macOS/Linux - 多位置检测
NOTEBOOKLM_PATH=""

# 1. 检查全局
if command -v notebooklm &>/dev/null; then
    NOTEBOOKLM_PATH="global"
fi

# 2. 如果在虚拟环境中，也检查虚拟环境
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

- **如果找到 notebooklm** → 直接跳到"检查认证状态"，无需安装
- **如果未找到** → 先询问用户是否之前已安装到虚拟环境

#### 第 1.5 步：询问是否已安装到虚拟环境（仅在未检测到时执行）

**如果第一步未检测到 notebooklm，先询问用户**：

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

**根据用户回答处理**：

- **选择"是，装在虚拟环境"** → 询问虚拟环境路径：

直接在对话中询问用户：`请输入虚拟环境的路径（例如 /Users/xxx/myenv 或 C:\Users\xxx\myenv）：`

用户输入路径后，**验证路径有效性**：

```bash
# macOS/Linux 验证
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

# Windows 验证
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

**验证结果处理**：
- **验证成功** → 记录 `NOTEBOOKLM_CMD`，后续所有 notebooklm 命令都使用这个绝对路径，跳到"检查认证状态"
- **验证失败** → 提示用户路径无效，重新询问或选择安装

**后续命令使用绝对路径**：
```bash
# 不需要激活虚拟环境，直接用绝对路径调用
# macOS/Linux
/Users/xxx/myenv/bin/notebooklm auth check --json
/Users/xxx/myenv/bin/notebooklm create "笔记本名" --json
/Users/xxx/myenv/bin/notebooklm source add "文件路径" --json

# Windows
C:\Users\xxx\myenv\Scripts\notebooklm.exe auth check --json
C:\Users\xxx\myenv\Scripts\notebooklm.exe create "笔记本名" --json
C:\Users\xxx\myenv\Scripts\notebooklm.exe source add "文件路径" --json
```

- **选择"否，需要安装"** → 继续下一步，进入安装流程

#### 第二步：确定安装位置（仅在需要安装时执行）

**检测当前是否在虚拟环境中**：

```bash
# Windows PowerShell
if ($env:VIRTUAL_ENV) {
    $DETECTED_VENV = $env:VIRTUAL_ENV
    $VENV_TYPE = "venv"
} elseif ($env:CONDA_PREFIX) {
    $DETECTED_VENV = $env:CONDA_PREFIX
    $VENV_TYPE = "conda"
} else {
    $DETECTED_VENV = $null
}

# macOS/Linux
if [ -n "$VIRTUAL_ENV" ]; then
    DETECTED_VENV="$VIRTUAL_ENV"
    VENV_TYPE="venv"
elif [ -n "$CONDA_PREFIX" ]; then
    DETECTED_VENV="$CONDA_PREFIX"
    VENV_TYPE="conda"
else
    DETECTED_VENV=""
fi
```

**如果检测到虚拟环境，询问用户安装位置**：

```
检测到你当前在虚拟环境中：
- 类型：{venv/conda}
- 路径：{环境路径}

请选择 notebooklm 的安装位置：
```

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

**根据用户选择设置安装目标**：
- 选择"当前虚拟环境" → `INSTALL_TO_VENV=true`
- 选择"全局环境" → `INSTALL_TO_VENV=false`
- 未检测到虚拟环境 → 自动 `INSTALL_TO_VENV=false`

**环境变量说明**：
| 环境变量 | 含义 |
|----------|------|
| `$VIRTUAL_ENV` | Python venv/virtualenv 虚拟环境路径 |
| `$CONDA_PREFIX` | Conda/Miniconda/Anaconda 环境路径 |

#### 第三步：检查 Python 环境（仅在需要安装时执行）

**根据安装目标，检测对应的 Python**：

```bash
# Windows
if ($INSTALL_TO_VENV) {
    # 检查虚拟环境的 python
    & "$DETECTED_VENV\Scripts\python.exe" --version
} else {
    # 检查全局 python
    python --version
}

# macOS/Linux
if [ "$INSTALL_TO_VENV" = true ]; then
    # 检查虚拟环境的 python
    "$DETECTED_VENV/bin/python" --version
else
    # 检查全局 python
    python3 --version 2>/dev/null || python --version 2>/dev/null
fi
```

**如果 Python 不存在**：

- **目标是虚拟环境但 Python 不存在**，提示用户：
```
虚拟环境已激活，但未找到 Python。请检查虚拟环境是否正确配置：
- venv: 确保虚拟环境目录下有 Scripts/python.exe (Windows) 或 bin/python (Unix)
- conda: 运行 `conda install python` 安装 Python
```

- **目标是全局环境但 Python 不存在**，根据操作系统自动安装：

```bash
# Windows（使用 winget）
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements

# macOS（使用 Homebrew）
brew install python3

# Linux Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-pip

# Linux CentOS/RHEL
sudo yum install -y python3 python3-pip
```

**如果自动安装失败**，提示用户手动安装：
```
自动安装失败。请手动安装 Python 3.10+：
- Windows: 访问 https://www.python.org/downloads/
- macOS: 运行 `brew install python3`（需先安装 Homebrew）
- Linux: 运行 `sudo apt install python3 python3-pip`
```

#### 第四步：安装 notebooklm（仅在需要安装时执行）

**根据安装目标，检测 notebooklm**：

```bash
# Windows
if ($INSTALL_TO_VENV) {
    # 检查虚拟环境
    $venvNotebooklm = "$DETECTED_VENV\Scripts\notebooklm.exe"
    if (Test-Path $venvNotebooklm) {
        & $venvNotebooklm --version
    } else {
        & "$DETECTED_VENV\Scripts\python.exe" -m notebooklm --version
    }
} else {
    # 检查全局
    notebooklm --version
}

# macOS/Linux
if [ "$INSTALL_TO_VENV" = true ]; then
    VENV_BIN="$DETECTED_VENV/bin"
    if [ -x "$VENV_BIN/notebooklm" ]; then
        "$VENV_BIN/notebooklm" --version
    else
        "$VENV_BIN/python" -m notebooklm --version 2>/dev/null
    fi
else
    notebooklm --version
fi
```

**如果命令不存在**，根据安装目标安装：

```bash
# 安装到虚拟环境
# Windows
if ($INSTALL_TO_VENV) {
    & "$DETECTED_VENV\Scripts\pip.exe" install "notebooklm-py[browser]"
    & "$DETECTED_VENV\Scripts\pip.exe" install playwright
    & "$DETECTED_VENV\Scripts\playwright.exe" install chromium
}

# macOS/Linux
if [ "$INSTALL_TO_VENV" = true ]; then
    "$DETECTED_VENV/bin/pip" install "notebooklm-py[browser]"
    "$DETECTED_VENV/bin/pip" install playwright
    "$DETECTED_VENV/bin/playwright" install chromium
fi

# 安装到全局环境
# macOS/Linux
pip3 install "notebooklm-py[browser]"
pip3 install playwright && playwright install chromium

# Windows
pip install "notebooklm-py[browser]"
pip install playwright && playwright install chromium
```

**安装位置说明**：
| 用户选择 | 安装位置 | pip 命令 | 后续使用要求 |
|----------|----------|----------|--------------|
| 当前虚拟环境 | 虚拟环境内 | `$DETECTED_VENV/bin/pip` | 需激活同一虚拟环境 |
| 全局环境 | 系统 Python | `pip3` (Unix) / `pip` (Windows) | 无特殊要求 |

安装完成后，提示用户运行 `notebooklm login` 登录。

**重要提示**：
- 如果选择安装到虚拟环境，后续每次使用都需要先激活该虚拟环境
- 如果选择全局安装，在任何目录下都可以直接使用

### 2. 检查认证状态

```bash
notebooklm auth check --json
```

如果未认证，提示用户运行 `notebooklm login`。

### 3. 串行收集用户输入（重要）

**必须按顺序逐个询问，每个维度确认完（包括追问）再问下一个。**

#### 第零步：询问是否有PPT大纲

**在选择素材前，先询问用户是否已有PPT大纲**：

```
提示：建议先准备一个PPT大纲文档，这样生成的幻灯片结构会更清晰。
大纲可以是简单的文本文件，包含标题和要点即可。
```

```json
{
  "questions": [{
    "question": "是否已有PPT大纲文档？\n\n有大纲时，幻灯片将以大纲为主体结构，其他文档作为补充素材",
    "header": "PPT大纲",
    "options": [
      {"label": "有大纲", "description": "已准备好大纲文档，将作为幻灯片主体结构"},
      {"label": "没有大纲", "description": "直接从素材文档生成幻灯片"}
    ],
    "multiSelect": false
  }]
}
```

**注意**：此问题只有"有大纲"和"没有大纲"两个选项。如果用户选择 Other，视为"没有大纲"处理。

**如果选择"没有大纲"，建议用户先生成大纲**：

```
建议：有大纲的幻灯片结构更清晰。我可以帮你先生成一份大纲。
```

```json
{
  "questions": [{
    "question": "是否先生成大纲？",
    "header": "生成大纲",
    "options": [
      {"label": "先生成大纲", "description": "我来帮你生成大纲，然后继续"},
      {"label": "直接继续", "description": "不用大纲，直接选择素材生成幻灯片"}
    ],
    "multiSelect": false
  }]
}
```

**用户选择说明**：
- 选择"先生成大纲" → Claude 直接帮用户生成大纲（见下方流程）
- 选择"直接继续" → 跳过大纲，进入第一步选择素材

**如果选择"先生成大纲"，执行以下流程**：

1. 先询问用户素材文档（同第一步）
2. 读取素材文档内容
3. 根据素材生成 PPT 大纲（Markdown 格式），使用以下提示词：

```
根据素材文档生成 PPT 大纲：

要求：
1. 页数：根据内容复杂度自动调整（最多20页，内容丰富时，每页可多填充要点，避免页数超出20）
2. 自动识别文档类型和核心章节，重组为适合演示的逻辑结构
3. 每页包含：
   - 清晰标题
   - 3-5个核心要点
   - 引用原文关键数据/案例作为支撑
4. 结构原则：
   - 开篇点题（背景/目的/核心观点）
   - 主体展开（按文档逻辑分章节，重点内容多分页）
   - 收尾总结（结论/行动建议/下一步）
5. 风格：简洁有力，每页聚焦一个核心信息点
```

4. 将大纲保存为 `PPT大纲.md` 文件到当前目录
5. 提示用户：`大纲已生成并保存为 PPT大纲.md，请查看是否需要修改。`
6. 等待用户确认后，自动将此大纲作为 PPT 主体结构，继续后续流程

**如果选择"有大纲"，立即追问选择大纲文件**：

```json
{
  "questions": [{
    "question": "请选择PPT大纲文件（只能选一个）",
    "header": "选择大纲",
    "options": [
      {"label": "大纲.md", "description": "从目录中找到的文档"},
      {"label": "outline.txt", "description": "从目录中找到的文档"}
    ],
    "multiSelect": false
  }]
}
```

**用户输入说明**：
- 大纲文件只能选择一个
- 选择 Other 时，输入文件名（带后缀）
- 大纲文件会作为幻灯片的主体结构

#### 第一步：询问素材文档（支持多选）

**先扫描当前目录下的可用文件**，使用 Glob 工具搜索所有 NotebookLM 支持的文件类型：

```bash
# Glob 搜索模式（包含所有 NotebookLM 支持的类型）
**/*.{pdf, txt, md,markdown, docx, doc,csv, avif, bmp, gif, ico, jp2, png, webp, tif, tiff, heic, heif, jpeg, jpg, jpe, 3g2, 3gp, aac, aif, aifc, aiff, amr, au, avi, cda, m4a, mid, mp3, mp4, mpeg, ogg, opus, ra, ram, snd, wav, wma}
```

**NotebookLM 支持的文件类型**：

| 类别 | 扩展名 |
|------|--------|
| 文档 | `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.markdown`, `.html`, `.htm`, `.epub` |
| 演示/表格 | `.pptx`, `.xlsx`, `.csv` |
| 音频 | `.mp3`, `.wav`, `.m4a` |
| 视频 | `.mp4`, `.mov`, `.avi`, `.webm` |
| 图片 | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` |

**展示文件列表后询问（支持多选）**：

```
当前目录下有以下可用文档：

| 序号 | 文档名 | 类型 |
|------|--------|------|
| 1 | 产品规划.pdf | PDF |
| 2 | 会议记录.docx | Word |
| 3 | 演示视频.mp4 | 视频 |
...

请选择要作为素材的文档（可多选），或输入文件名：
```

```json
{
  "questions": [{
    "question": "请选择要作为素材的文档（可多选）\n\n选择 Other 时请输入文件名，多个用逗号分隔",
    "header": "选择素材",
    "options": [
      {"label": "产品规划.pdf", "description": "PDF 文档"},
      {"label": "会议记录.docx", "description": "Word 文档"},
      {"label": "演示视频.mp4", "description": "视频文件"}
    ],
    "multiSelect": true
  }]
}
```

**用户输入说明**：
- 可从列表中多选文件
- 选择 "Other" 时，输入文件名（带后缀），多个用逗号分隔
- **提示语**：`请输入文件名，多个用逗号分隔`

用户选择后，**验证每个文件是否存在**，不存在则提示重新输入。系统会自动在当前目录及子目录中查找匹配的文件。

#### 第二步：询问风格

```json
{
  "questions": [{
    "question": "选择幻灯片风格",
    "header": "风格",
    "options": [
      {"label": "商务汇报（推荐）", "description": "适合向领导/客户汇报，突出核心结论和数据"},
      {"label": "技术分享", "description": "适合技术交流，包含详细的技术细节"},
      {"label": "产品演示", "description": "适合产品发布，突出功能亮点和用户价值"},
      {"label": "参考PDF风格", "description": "上传一个参考PDF，模仿其风格"}
    ],
    "multiSelect": false
  }]
}
```

**如果选择"参考PDF风格"，立即追问（只能选一个）**：

```json
{
  "questions": [{
    "question": "请输入参考PDF的文件名（只能选一个）\n\n选择 Other 时请输入文件名",
    "header": "参考PDF",
    "options": [
      {"label": "优秀案例.pdf", "description": "从目录中找到的PDF文件"},
      {"label": "模板样式.pdf", "description": "从目录中找到的PDF文件"}
    ],
    "multiSelect": false
  }]
}
```

**用户输入说明**：
- 参考PDF只能选择一个
- 选择 "Other" 时，输入文件名

验证参考PDF存在后，再进入下一步。

#### 第三步：询问页数

```json
{
  "questions": [{
    "question": "幻灯片页数要求",
    "header": "页数",
    "options": [
      {"label": "自动决定（推荐）", "description": "让AI根据内容自动决定，通常10-15页"},
      {"label": "精简版（5-8页）", "description": "只保留最核心的内容"},
      {"label": "Other", "description": "输入自定义页数（整数），NotebookLM 最多支持20页"}
    ],
    "multiSelect": false
  }]
}
```

**用户输入说明**：
- 选择预设选项，或选择 "Other" 直接输入自定义页数
- **注意**：NotebookLM 最多支持生成 20 页，超出范围可能无法完全满足

#### 第四步：询问额外要求

```json
{
  "questions": [{
    "question": "对幻灯片有什么特殊要求？",
    "header": "额外要求",
    "options": [
      {"label": "无特殊要求", "description": "使用默认设置生成"},
      {"label": "突出数据和图表", "description": "强调数据可视化"},
      {"label": "适合演讲使用", "description": "简洁大字，便于讲解"},
      {"label": "自定义要求", "description": "通过对话框输入详细要求（支持长文本）"}
    ],
    "multiSelect": false
  }]
}
```

**如果选择"自定义要求"，通过对话框追问**：

直接在对话中询问用户：`请输入你的具体要求（支持长文本）：`

用户在对话框中输入后，继续下一步。

**用户输入说明**：
- 选择预设选项，或选择"自定义要求"通过对话框输入详细内容

#### 第五步：确认所有信息

**重要：此步骤禁止使用 AskUserQuestion 弹窗！**

收集完所有信息后，直接在对话中展示确认信息，然后等待用户打字回复：

```
即将生成幻灯片，请确认以下信息：

| 项目 | 内容 |
|------|------|
| PPT大纲 | 大纲.md（作为主体结构） |
| 素材文档 | 产品规划.pdf, 数据分析.xlsx（共2个，作为补充素材） |
| 风格 | 商务汇报 |
| 页数 | 自动决定 |
| 额外要求 | 无 |

请回复"确认"开始生成，或回复"取消"重新配置：
```

**等待用户在对话框中打字确认（不要弹窗）**：
- 用户回复"确认"、"开始"、"ok"、"好"等 → 开始生成
- 用户回复"取消"、"重新"等 → 返回第零步重新收集信息

### 4. 构建提示词

```python
import os

prompt_parts = []

# 大纲（如果有）
if outline_file:
    outline_filename = os.path.basename(outline_file)
    prompt_parts.append(f"以 {outline_filename} 为PPT主体结构和框架，严格按照大纲的章节和要点组织幻灯片")
    prompt_parts.append("其他素材文档作为补充材料，大纲中未描述清楚的内容可以从素材中提取")

# 风格
style_prompts = {
    "商务汇报（推荐）": "采用商务风格，突出核心结论和关键数据，每页一个核心观点",
    "技术分享": "采用技术分享风格，包含架构图说明，代码示例用代码块展示",
    "产品演示": "采用产品演示风格，突出功能亮点和用户价值，配合使用场景"
}

if style == "参考PDF风格" and reference_pdf_path:
    ref_filename = os.path.basename(reference_pdf_path)
    prompt_parts.append(f"参考 {ref_filename} 的风格、排版和设计，模仿其视觉呈现方式")
else:
    prompt_parts.append(style_prompts.get(style, style))

# 页数
if pages == "自动决定（推荐）":
    prompt_parts.append("根据内容自动决定页数，确保信息完整")
elif pages == "精简版（5-8页）":
    prompt_parts.append("控制在5-8页，只保留最核心内容")
else:
    page_num = ''.join(filter(str.isdigit, str(pages)))
    if page_num:
        prompt_parts.append(f"生成约{page_num}页幻灯片，合理分配内容")

# 额外要求
if extra_prompt and extra_prompt != "无特殊要求":
    prompt_parts.append(extra_prompt)

final_prompt = "。".join(prompt_parts)
```

### 5. 执行自动化流程

```bash
# Step 1: 创建笔记本
notebooklm create "幻灯片: {主文档名}" --json

# Step 2: 如有大纲文件，优先上传（作为主体结构）
if outline_file:
    notebooklm source add "{outline_file}" --json

# Step 3: 上传所有素材文档（支持多个，作为补充素材）
for file in source_files:
    notebooklm source add "{文件路径}" --json

# Step 4: 如有参考PDF，也上传（只能一个）
if reference_pdf_path:
    notebooklm source add "{reference_pdf_path}" --json

# Step 5: 等待文档处理完成（轮询）
notebooklm source list --json
# 每10秒检查，直到 status 变为 "ready"

# Step 5: 生成幻灯片
notebooklm generate slide-deck "{final_prompt}" --format detailed --language zh_Hans --json

# Step 6: 等待生成完成（轮询）
notebooklm artifact list --json
# 每15秒检查，直到 status 变为 "completed"

# Step 7: 下载到文档同目录
notebooklm download slide-deck "{输出路径}"
```

### 6. 固定参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 幻灯片格式 | `--format detailed` | 详细版 |
| 语言 | `--language zh_Hans` | 中文简体 |

## 免登录配置（可选）

### Windows PowerShell

```powershell
[System.Environment]::SetEnvironmentVariable(
    "NOTEBOOKLM_AUTH_JSON",
    (Get-Content "$env:USERPROFILE\.notebooklm\storage_state.json" -Raw),
    "User"
)
```

### macOS (zsh)

```bash
echo 'export NOTEBOOKLM_AUTH_JSON=$(cat ~/.notebooklm/storage_state.json)' >> ~/.zshrc
source ~/.zshrc
```

### Linux (bash)

```bash
echo 'export NOTEBOOKLM_AUTH_JSON=$(cat ~/.notebooklm/storage_state.json)' >> ~/.bashrc
source ~/.bashrc
```

## 页数限制说明

NotebookLM 有内置限制，最多生成 **20 页**。如需更多页数，可将文档拆分后分别生成再合并。

## 支持的文件格式

NotebookLM 支持以下所有文件类型作为素材来源：

| 类别 | 扩展名 | 说明 |
|------|--------|------|
| **文档** | `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.markdown`, `.html`, `.htm`, `.epub` | 主要素材类型 |
| **演示/表格** | `.pptx`, `.xlsx`, `.csv` | 会提取文本内容 |
| **音频** | `.mp3`, `.wav`, `.m4a` | 会转录为文本 |
| **视频** | `.mp4`, `.mov`, `.avi`, `.webm` | 会提取音频并转录 |
| **图片** | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp` | 会进行 OCR 识别 |

**Glob 搜索模式**：
```
**/*.{pdf,docx,doc,txt,md,markdown,html,htm,epub,pptx,xlsx,csv,mp3,wav,m4a,mp4,mov,avi,webm,jpg,jpeg,png,gif,webp}
```

## 平台兼容性

| 平台 | 状态 | pip 命令 |
|------|------|----------|
| Windows | ✅ | pip |
| macOS | ✅ | pip3 优先 |
| Linux | ✅ | pip3 优先 |

### 虚拟环境支持

| 环境类型 | 检测方式 | 安装位置 |
|----------|----------|----------|
| venv/virtualenv | `$VIRTUAL_ENV` 环境变量 | `$VIRTUAL_ENV/bin/` 或 `$VIRTUAL_ENV\Scripts\` |
| Conda/Miniconda | `$CONDA_PREFIX` 环境变量 | `$CONDA_PREFIX/bin/` |
| 无虚拟环境 | 上述变量均为空 | 全局 Python 环境 |

**注意**：如果在虚拟环境中安装了 notebooklm，后续使用时需要激活同一虚拟环境。

## 错误处理

| 错误 | 处理 |
|------|------|
| notebooklm 不存在 | 自动安装 |
| pip/pip3 不存在 | 提示安装 Python 3.10+ |
| 认证失败 | 提示 `notebooklm login` |
| 文件不存在 | 提示检查路径 |
| 生成超时 | 提示用 `notebooklm artifact list` 检查 |

## 示例对话

**用户**: /doc-to-slides

**Claude**:
提示：建议先准备一个PPT大纲文档，这样生成的幻灯片结构会更清晰。

是否已有PPT大纲文档？
[弹窗：PPT大纲选择]

**用户**: 有大纲

**Claude**: 请选择PPT大纲文件：
[弹窗：选择大纲文件]

**用户**: 大纲.md

**Claude**: 当前目录下有以下可用文档：
| 序号 | 文档名 | 类型 |
|------|--------|------|
| 1 | 产品规划.pdf | PDF |
| 2 | 数据分析.xlsx | Excel |
| 3 | 会议录音.mp3 | 音频 |

请选择要作为素材的文档（可多选）：
[弹窗：素材选择，multiSelect=true]

**用户**: 产品规划.pdf, 数据分析.xlsx

**Claude**: 选择幻灯片风格：
[弹窗：风格选择]

**用户**: 自定义风格

**Claude**: 请在对话框中输入风格要求（支持长文本）：

**用户**: 以洁净的白色为背景主色，带有淡淡的浅灰色工程网格纹理。视觉风格采用深海军蓝作为文字、线条和图表轮廓的主色调...

**Claude**: 幻灯片页数要求：
[弹窗：页数选择]

**用户**: Other → 18

**Claude**: 对幻灯片有什么特殊要求？
[弹窗：额外要求]

**用户**: Other → 突出ROI数据，配合图表说明

**Claude**:
即将生成幻灯片，请确认：
- PPT大纲：大纲.md（作为主体结构）
- 素材文档：产品规划.pdf, 数据分析.xlsx（共2个，作为补充素材）
- 风格：自定义风格（已输入详细要求）
- 页数：18页
- 额外要求：突出ROI数据，配合图表说明

开始生成...
1. ✓ 创建笔记本
2. ✓ 上传大纲文件
3. ✓ 上传素材文档（2个）
4. ✓ 文档处理完成
5. ⏳ 生成幻灯片...
6. ✓ 下载完成：~/Documents/大纲-幻灯片.pdf
