# 自动化执行流程

## 执行步骤

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

# Step 6: 生成幻灯片
notebooklm generate slide-deck "{final_prompt}" --format detailed --language zh_Hans --json

# Step 7: 等待生成完成（轮询）
notebooklm artifact list --json
# 每15秒检查，直到 status 变为 "completed"

# Step 8: 下载到文档同目录
notebooklm download slide-deck "{输出路径}"
```

## 固定参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 幻灯片格式 | `--format detailed` | 详细版 |
| 语言 | `--language zh_Hans` | 中文简体 |
