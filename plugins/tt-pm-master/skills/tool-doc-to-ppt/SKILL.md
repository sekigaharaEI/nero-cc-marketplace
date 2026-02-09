---
name: tool-doc-to-ppt
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

**按步骤1→2→3→4 顺序执行。每个步骤开始前，必须先读取对应的参考文档，严格按照文档中的指令操作。**

### 步骤1：环境准备

先运行环境检查脚本：

```bash
python scripts/check_env.py
```

根据 JSON 输出判断：

- `notebooklm_found=true` 且 `playwright_found=true` 且 `auth_ok=true` → 环境就绪，直接进入步骤2
- 其他情况 → **读取** [references/env-setup.md](references/env-setup.md) 按流程排查和安装。遇到平台差异或报错时查阅 [references/platform-reference.md](references/platform-reference.md)

### 步骤2：收集用户输入

串行收集：大纲 → 素材 → 风格 → 页数 → 额外要求 → 确认。

**执行前必须读取** [references/user-input-flow.md](references/user-input-flow.md)，按其中的交互流程逐步询问。文件类型和 Glob 模式见 [references/platform-reference.md](references/platform-reference.md)。

### 步骤3：构建提示词

根据用户输入动态拼接 `final_prompt`。

**执行前必须读取** [references/prompt-builder.md](references/prompt-builder.md)，按其中的 Python 逻辑构建提示词。

### 步骤4：执行自动化

创建笔记本 → 上传文档 → 等待处理 → 生成幻灯片 → 等待完成 → 下载 PDF。

**执行前必须读取** [references/automation-flow.md](references/automation-flow.md)，严格按其中的 8 个步骤顺序执行，不能跳过任何一步。

固定参数：`--format detailed`（详细版）、`--language zh_Hans`（中文简体）。
