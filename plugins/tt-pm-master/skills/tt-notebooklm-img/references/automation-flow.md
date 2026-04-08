# 自动化执行流程

## 重要：笔记本 ID 隔离

**每次执行必须创建新笔记本，并在后续所有命令中通过 `--notebook {NOTEBOOK_ID}` 指定该笔记本。** 不传 `--notebook` 会操作上次活跃的笔记本，导致新旧文件混在一起。

## 固定提示词

本 skill 使用固定提示词，**不可修改**（已验证效果满意）：

```
FIXED_PROMPT = "这是一个图片集的描述文档，每个描述代表一张完全不同的图片。生成演示文稿时请严格遵守：1.每页只有一张全屏插图，无文字 2.如果有"参照原图"关键字，则在原图的基础上按"修改意见"进行修改 3.插图内容和风格严格按照对应描述生成 4.不加任何额外页面 5.禁止跨页合并内容 6.禁止添加"总结"或"概述"页 7.禁止统一风格或添加连贯叙事"
```

## 执行步骤

```bash
# Step 1: 创建笔记本
# 笔记本名称格式: "图片集 (YYYY-MM-DD HHmm)"
notebooklm create "图片集 (2026-02-10 1430)" --json
# 返回示例: {"notebook_id": "abc123", ...}
# 记录 NOTEBOOK_ID=abc123，后续所有命令都必须带上 --notebook {NOTEBOOK_ID}

# Step 2: 上传 picture-set.md
notebooklm source add "{picture-set.md路径}" --notebook {NOTEBOOK_ID} --json

# Step 3: 上传原图（仅改图模式需要）
# 逐个上传所有原图文件
for image_file in original_images:
    notebooklm source add "{image_file路径}" --notebook {NOTEBOOK_ID} --json

# Step 4: 等待文档处理完成（轮询）
notebooklm source list --notebook {NOTEBOOK_ID} --json
# 每10秒检查，直到所有 source 的 status 变为 "ready"

# Step 5: 生成幻灯片（使用固定提示词）
notebooklm generate slide-deck "{FIXED_PROMPT}" --notebook {NOTEBOOK_ID} --format presenter --language zh_Hans --json

# Step 6: 等待生成完成（轮询）
notebooklm artifact list --notebook {NOTEBOOK_ID} --json
# 每15秒检查，直到 status 变为 "completed"

# Step 7: 下载 PDF
# 输出路径: {工作目录}/generated-images.pdf
notebooklm download slide-deck "{输出路径}" --notebook {NOTEBOOK_ID}

# Step 8: PDF 转图片
python scripts/pdf_to_images.py "{pdf路径}" "{输出目录}"
# 输出目录: {工作目录}/generated-images/
```

## 固定参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 幻灯片格式 | `--format presenter` | 简洁版（演示者模式） |
| 语言 | `--language zh_Hans` | 中文简体 |
| 提示词 | 固定（见上方） | 已验证效果满意，不可修改 |

## 输出路径规范

| 文件 | 路径 | 说明 |
|------|------|------|
| picture-set.md | `{工作目录}/picture-set.md` | 中间产物，保留供用户查看 |
| PDF | `{工作目录}/generated-images.pdf` | 中间产物，保留 |
| 图片 | `{工作目录}/generated-images/pic-01.png` | 最终产物 |
| 图片 | `{工作目录}/generated-images/pic-02.png` | 最终产物 |
| ... | ... | 按页数递增 |

## 错误处理

| 错误 | 处理 |
|------|------|
| source 处理超时（>5分钟） | 提示用户检查网络，重试 |
| 幻灯片生成超时（>10分钟） | 提示用 `notebooklm artifact list` 检查状态 |
| 下载失败 | 重试一次，仍失败则提示手动下载 |
| PDF 转图片失败 | 检查 PyMuPDF 安装，提示用户 |
