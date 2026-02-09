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

## 工作流程概览

```
步骤1 环境准备 → 步骤2 收集用户输入 → 步骤3 构建提示词 → 步骤4 执行自动化
```

| 步骤 | 说明 | 详细文档 |
|------|------|----------|
| 1. 环境准备 | 网络检查 → 依赖安装 → 认证 | [env-setup.md](references/env-setup.md) |
| 2. 收集用户输入 | 大纲 → 素材 → 风格 → 页数 → 确认 | [user-input-flow.md](references/user-input-flow.md) |
| 3. 构建提示词 | 根据用户输入动态拼接提示词 | [prompt-builder.md](references/prompt-builder.md) |
| 4. 执行自动化 | 创建笔记本 → 上传 → 生成 → 下载 | [automation-flow.md](references/automation-flow.md) |

## 步骤1：环境准备

> 详细流程见 [references/env-setup.md](references/env-setup.md)

1. **网络检查**：提示用户 NotebookLM 是 Google 服务，中国大陆需 VPN
2. **依赖检测**：检测 notebooklm 是否已安装（全局 + 虚拟环境），平台差异见 [platform-reference.md](references/platform-reference.md) 的"平台兼容性"和"虚拟环境支持"
3. **安装依赖**：未安装时自动安装 `notebooklm-py[browser]` + Playwright
4. **认证检查**：运行 `notebooklm auth check --json`，未认证则提示 `notebooklm login`（可配置免登录，见 [platform-reference.md](references/platform-reference.md) 的"免登录配置"）
5. **出错时**：查阅 [platform-reference.md](references/platform-reference.md) 的"错误处理"表格

## 步骤2：收集用户输入

> 详细流程见 [references/user-input-flow.md](references/user-input-flow.md)

**必须按顺序逐个询问，每个维度确认完再问下一个：**

1. **PPT大纲**：询问是否有大纲，没有可帮助生成
2. **素材文档**：扫描目录，支持多选。支持的文件类型和 Glob 模式见 [platform-reference.md](references/platform-reference.md) 的"支持的文件格式"
3. **风格选择**：商务汇报/技术分享/产品演示/参考PDF风格
4. **页数设置**：自动决定/精简版/自定义（最多20页，限制说明见 [platform-reference.md](references/platform-reference.md)）
5. **额外要求**：预设选项或自定义输入
6. **确认信息**：展示汇总表格，等待用户确认（禁止弹窗）

## 步骤3：构建提示词

> 详细逻辑见 [references/prompt-builder.md](references/prompt-builder.md)

根据大纲、风格、页数、额外要求动态拼接 `final_prompt`，传给 NotebookLM 生成命令。

## 步骤4：执行自动化

> 详细流程见 [references/automation-flow.md](references/automation-flow.md)

```bash
notebooklm create "幻灯片: {主文档名}" --json       # 创建笔记本
notebooklm source add "{文件路径}" --json            # 上传文档（大纲优先，然后素材）
notebooklm source list --json                        # 等待处理完成（轮询）
notebooklm generate slide-deck "{prompt}" \
  --format detailed --language zh_Hans --json         # 生成幻灯片
notebooklm artifact list --json                      # 等待生成完成（轮询）
notebooklm download slide-deck "{输出路径}"           # 下载PDF
```

**固定参数**：`--format detailed`（详细版）、`--language zh_Hans`（中文简体）

## 参考信息

> 详见 [references/platform-reference.md](references/platform-reference.md)

- **支持格式**：PDF/Word/Markdown/音视频/图片等 20+ 种格式
- **平台兼容**：Windows / macOS / Linux，支持 venv/conda 虚拟环境
- **页数限制**：NotebookLM 最多生成 20 页
- **免登录配置**：可将认证状态写入环境变量
- **错误处理**：自动安装依赖、认证引导、超时检查
