---
name: tt-notebooklm-img
description: 利用 Google NotebookLM 免费生成 AI 图片。支持纯文生图（描述生成图片）、改图（原图+修改意见）和批量导入已有描述文件。当用户说"生成图片"、"画图"、"AI画图"、"改图"、"修改图片"时触发。最多一次生成20张。支持 Windows/macOS/Linux。
---

# AI 图片生成（NotebookLM）

利用 NotebookLM 的演示文稿生成功能，免费生成 AI 图片。

## 触发方式

- `/notebooklm-img`
- "帮我生成图片"
- "AI画图"
- "画一张/几张图"
- "帮我改图"
- "修改这张图片"

## 工作流程

**按步骤 1→2→3→4→5 顺序执行。每个步骤开始前，必须先读取对应的参考文档，严格按照文档中的指令操作。**

### 步骤1：环境准备

先运行环境检查脚本：

```bash
python scripts/check_env.py
```

根据 JSON 输出判断：

- `notebooklm_found=true` 且 `playwright_found=true` 且 `auth_ok=true` 且 `pymupdf_found=true` → 环境就绪，直接进入步骤2
- 其他情况 → **读取** [references/env-setup.md](references/env-setup.md) 按流程排查和安装

### 步骤2：收集用户输入

确定模式（批量导入 / 文生图 / 改图 / 混合），收集每张图片的描述信息。

**执行前必须读取** [references/user-input-flow.md](references/user-input-flow.md)，按其中的交互流程逐步询问。

- **批量导入**：用户已有 picture-set.md，选择文件后直接跳到步骤4
- **其他模式**：按交互流程收集描述，进入步骤3

### 步骤3：构建 picture-set.md

根据用户输入自动组装 picture-set.md 文件。

**执行前必须读取** [references/picture-set-builder.md](references/picture-set-builder.md)，按其中的格式规范生成文件。

### 步骤4：执行自动化

创建笔记本 → 上传 picture-set.md（和原图）→ 等待处理 → 生成幻灯片 → 等待完成 → 下载 PDF。

**执行前必须读取** [references/automation-flow.md](references/automation-flow.md)，严格按步骤顺序执行。

### 步骤5：PDF 转图片

将下载的 PDF 每页导出为单独的图片文件：

```bash
python scripts/pdf_to_images.py "{pdf路径}" "{输出目录}"
```

完成后告知用户图片保存位置，并列出所有生成的图片文件。
