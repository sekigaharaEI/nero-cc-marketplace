# 平台参考信息

## 支持的文件格式

NotebookLM 支持以下所有文件类型作为素材来源：

| 类别          | 扩展名                                                                        | 说明             |
| ------------- | ----------------------------------------------------------------------------- | ---------------- |
| **文档**      | `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.markdown`, `.html`, `.htm`, `.epub` | 主要素材类型     |
| **演示/表格** | `.pptx`, `.xlsx`, `.csv`                                                      | 会提取文本内容   |
| **音频**      | `.mp3`, `.wav`, `.m4a`                                                        | 会转录为文本     |
| **视频**      | `.mp4`, `.mov`, `.avi`, `.webm`                                               | 会提取音频并转录 |
| **图片**      | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`                                      | 会进行 OCR 识别  |

**Glob 搜索模式**：
```
**/*.{pdf,docx,doc,txt,md,markdown,html,htm,epub,pptx,xlsx,csv,mp3,wav,m4a,mp4,mov,avi,webm,jpg,jpeg,png,gif,webp}
```

## 页数限制

NotebookLM 有内置限制，最多生成 **20 页**。如需更多页数，可将文档拆分后分别生成再合并。

## 平台兼容性

| 平台    | 状态 | pip 命令  |
| ------- | ---- | --------- |
| Windows | ✅    | pip       |
| macOS   | ✅    | pip3 优先 |
| Linux   | ✅    | pip3 优先 |

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

| 错误              | 处理                                   |
| ----------------- | -------------------------------------- |
| notebooklm 不存在 | 自动安装                               |
| pip/pip3 不存在   | 提示安装 Python 3.10+                  |
| 认证失败          | 提示 `notebooklm login`                |
| 文件不存在        | 提示检查路径                           |
| 生成超时          | 提示用 `notebooklm artifact list` 检查 |
