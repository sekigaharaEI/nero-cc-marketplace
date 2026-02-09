# 平台参考信息

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

## 页数限制

NotebookLM 有内置限制，最多生成 **20 页**。如需更多页数，可将文档拆分后分别生成再合并。

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

**Claude**: 是否已有PPT大纲文档？ → [弹窗选择]

**用户**: 有大纲 → 选择大纲文件 → 选择素材 → 选择风格 → 选择页数 → 确认额外要求

**Claude**: 展示确认信息表格，等待用户确认

**用户**: 确认

**Claude**:
1. ✓ 创建笔记本
2. ✓ 上传大纲文件
3. ✓ 上传素材文档（2个）
4. ✓ 文档处理完成
5. ⏳ 生成幻灯片...
6. ✓ 下载完成：~/Documents/大纲-幻灯片.pdf
