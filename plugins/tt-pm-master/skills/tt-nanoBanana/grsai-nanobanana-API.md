`# NanoBanana API 调用文档

## 概述

NanoBanana 是 GRSAI 提供的 AI 图像生成 API，支持纯文本生图、单图参考编辑、多图风格迁移。

## 环境配置

### 1. 安装依赖
```bash
pip install requests python-dotenv
```

### 2. 配置 `.env` 文件
```env
# 海外: https://grsaiapi.com | 国内: https://grsai.dakka.com.cn
NANO_BANANA_HOST=https://grsai.dakka.com.cn
NANO_BANANA_API_KEY=your_api_key_here
```

## API 参数

| 参数 | 类型 | 说明 | 可选值 |
|------|------|------|--------|
| `model` | string | 模型名称 | `nano-banana-pro`(默认), `nano-banana-pro-4k-vip`(4K需VIP) |
| `prompt` | string | 提示词 | - |
| `imageSize` | string | 图片尺寸 | `1K`, `2K`, `4K` |
| `aspectRatio` | string | 宽高比 | `auto`, `1:1`, `4:3`, `3:4`, `16:9`, `9:16` |
| `urls` | array | 参考图片(base64) | 支持多张图片 |

## 命令行使用

```bash
# 纯文本生图
python nano_banana.py "一只橘色的猫咪在阳光下打盹" -s 2K -r 16:9

# 单图参考编辑
python nano_banana.py "将图片转为水彩画风格" -i reference.png -s 2K

# 多图风格迁移（第一张为内容图，第二张为风格图）
python nano_banana.py "将第一张图转为第二张图的风格" -i content.png style.png -s 2K -r 9:16
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `prompt` | 提示词（必填） | - |
| `-i, --images` | 参考图片路径（支持多张） | - |
| `-s, --size` | 图片尺寸 | `2K` |
| `-r, --ratio` | 宽高比 | `auto` |
| `-m, --model` | 模型名称 | `nano-banana-pro` |
| `-o, --output` | 输出目录 | `./output` |

## 代码调用

```python
from nano_banana import generate, draw

# 完整流程（生成+下载）
paths = generate("一只猫咪", images=["ref.png"], size="2K", ratio="16:9")

# 仅调用 API（不下载）
result = draw("一只猫咪", images=["ref.png"], size="2K", ratio="16:9")
```

## API 响应

API 使用 SSE 流式响应，最终返回格式：
```json
{
  "id": "task-id",
  "status": "succeeded",
  "progress": 100,
  "results": [{"url": "https://...png", "content": ""}]
}
```

状态值：`running`(进行中) | `succeeded`(成功) | `failed`(失败)

## 实际输出尺寸参考

| 设置 | 16:9 | 9:16 | 1:1 |
|------|------|------|-----|
| 1K | 1408x768 | 768x1408 | ~1024x1024 |
| 2K | 2752x1536 | 1536x2752 | ~2048x2048 |

## 注意事项

1. **参数命名**：API 使用驼峰命名（`imageSize`、`aspectRatio`），非下划线
2. **4K 权限**：4K 分辨率需要 VIP 账户，使用模型 `nano-banana-pro-4k-vip`
3. **图片格式**：支持 JPG、JPEG、PNG、WEBP
4. **超时设置**：生成过程约 30-60 秒，脚本默认超时 300 秒
