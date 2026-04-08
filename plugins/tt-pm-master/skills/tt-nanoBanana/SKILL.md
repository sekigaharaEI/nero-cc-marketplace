---
name: tt-nanoBanana
description: AI 图像生成工具。使用 NanoBanana API 根据文字描述生成图片，支持参考图片风格迁移。当用户需要生成图片、AI绘图、文生图时触发。
---

# nanoBanana - AI 图像生成工具

脚本位置：`~/.claude/skills/nanoBanana/nano_banana.py`
虚拟环境：`~/.claude/skills/nanoBanana/.venv`

## 执行前检查

### 1. 检查 uv 是否安装

```bash
uv --version
```

如果未安装，提示用户安装 uv：
- Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Linux/macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. 初始化虚拟环境（首次使用）

Windows:
```bash
uv venv %USERPROFILE%\.claude\skills\nanoBanana\.venv
uv pip install --python %USERPROFILE%\.claude\skills\nanoBanana\.venv\Scripts\python.exe requests python-dotenv
```

Linux/macOS:
```bash
uv venv ~/.claude/skills/nanoBanana/.venv
uv pip install --python ~/.claude/skills/nanoBanana/.venv/bin/python requests python-dotenv
```

### 3. 配置 API 密钥

确保 `~/.claude/skills/nanoBanana/.env` 文件存在并配置：

```env
# 海外: https://grsaiapi.com | 国内: https://grsai.dakka.com.cn
NANO_BANANA_HOST=https://grsai.dakka.com.cn
NANO_BANANA_API_KEY=your_api_key_here
```

## 智能 Prompt 扩写（重要）

在调用脚本之前，你必须根据用户的绘图意图，将简短描述扩写为详细的绘图提示词。

### 第一步：识别场景类型

根据用户的描述和上下文，判断属于哪种场景：

| 场景类型 | 触发关键词/上下文 |
|---------|------------------|
| **科研配图** | 论文、期刊、学术、研究、实验、数据可视化、流程图、机制图 |
| **商务汇报** | PPT、汇报、演示、报告、会议、提案、商业计划 |
| **教育说明** | 教学、课件、说明、示意图、教程、培训 |
| **艺术创作** | 插画、壁纸、头像、海报、概念艺术、其他未明确场景 |

### 第二步：按场景扩写 Prompt

#### 严肃场景（科研/商务/教育）

**扩写原则：**
- 风格：简洁、专业、清晰、现代
- 避免：过度装饰、复杂光影、艺术化渲染
- 强调：信息传达、逻辑清晰、视觉层次

**扩写模板：**
```
[主体内容描述]，[布局说明]，
专业信息图风格，扁平化设计，简洁干净的背景，
柔和的配色方案，清晰的视觉层次，
矢量图形风格，高对比度，无多余装饰，
适合学术/商务场景，白色或浅灰色背景
```

**示例：**
- 用户输入："画一个细胞分裂的过程"
- 扩写后："细胞有丝分裂的四个阶段（前期、中期、后期、末期）从左到右排列，每个阶段清晰标注，专业生物学插图风格，扁平化设计，简洁白色背景，柔和的蓝绿配色，清晰的视觉层次，矢量图形风格，适合学术论文配图"

#### 艺术创作场景

**扩写原则：**
- 丰富画面细节和氛围
- 添加光影、材质、构图描述
- 指定艺术风格和情绪基调

**扩写模板：**
```
[主体内容]，[姿态/动作/状态]，
[环境/场景描述]，[光影效果]，
[艺术风格]，[色调/氛围]，
[构图方式]，[画面质量描述]
```

**示例：**
- 用户输入："画一只猫"
- 扩写后："一只橘色的猫咪慵懒地躺在窗台上，阳光透过窗帘洒落形成斑驳光影，温暖的午后氛围，柔和的暖色调，日系治愈插画风格，细腻的毛发质感，浅景深效果，画面温馨惬意，高质量细节渲染"

### 第三步：确认宽高比

根据场景自动推荐宽高比：
- **科研配图**：通常 `16:9` 或 `4:3`（横向，适合论文插图）
- **PPT配图**：`16:9`（适配演示文稿）
- **流程图/机制图**：`16:9` 或 `auto`
- **头像/图标**：`1:1`
- **海报/壁纸**：`9:16`（竖向）或 `16:9`（横向）
- **一般创作**：`auto` 或根据内容判断

### 扩写示例对照

| 用户输入 | 场景 | 扩写后的 Prompt |
|---------|------|----------------|
| "神经网络结构图" | 科研 | "深度神经网络架构示意图，展示输入层、多个隐藏层和输出层，节点之间用连线表示权重连接，专业技术插图风格，扁平化设计，深蓝和白色配色，简洁白色背景，清晰的层次结构，矢量图形风格，适合学术论文" |
| "数字化转型" | 商务 | "企业数字化转型概念图，中心是现代化办公楼，周围环绕云计算、数据分析、AI等图标元素，专业商务信息图风格，扁平化设计，蓝色科技感配色，简洁干净背景，现代感，适合商务PPT演示" |
| "一个女孩在雨中" | 艺术 | "一个长发少女撑着透明雨伞站在雨中的街道上，细密的雨丝飘落，地面倒映着霓虹灯光，城市夜景背景，电影感光影，日系动漫插画风格，忧郁而唯美的氛围，冷暖色调对比，浅景深效果，高质量细节" |

## 功能

- **纯文本生图**: 根据文字描述生成图片
- **单图参考编辑**: 基于参考图进行风格转换
- **多图风格迁移**: 将内容图转换为风格图的风格
- 默认输出 2K 分辨率

## 使用方法

### 纯文本生图

Windows:
```bash
%USERPROFILE%\.claude\skills\nanoBanana\.venv\Scripts\python.exe %USERPROFILE%\.claude\skills\nanoBanana\nano_banana.py "提示词"
```

Linux/macOS:
```bash
~/.claude/skills/nanoBanana/.venv/bin/python ~/.claude/skills/nanoBanana/nano_banana.py "提示词"
```

### 带参考图生成

```bash
# 单图参考
python nano_banana.py "将图片转为水彩画风格" -i reference.png

# 多图风格迁移（第一张为内容图，第二张为风格图）
python nano_banana.py "将第一张图转为第二张图的风格" -i content.png style.png
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `prompt` | 提示词（必填） | - |
| `-i, --images` | 参考图片路径（支持多张） | - |
| `-s, --size` | 图片尺寸 (1K, 2K, 4K) | `2K` |
| `-r, --ratio` | 宽高比 (auto, 1:1, 4:3, 3:4, 16:9, 9:16) | `auto` |
| `-m, --model` | 模型名称 | `nano-banana-pro` |
| `-o, --output` | 输出目录 | `./output` |

### 输出

- 生成的图片保存在 `./output` 目录（或指定的输出目录）
- 文件名格式：`{task_id}_{index}.png`

## 实际输出尺寸参考

| 设置 | 16:9 | 9:16 | 1:1 |
|------|------|------|-----|
| 1K | 1408x768 | 768x1408 | ~1024x1024 |
| 2K | 2752x1536 | 1536x2752 | ~2048x2048 |

## 注意事项

- 4K 分辨率需要 VIP 账户，使用模型 `nano-banana-pro-4k-vip`
- 支持图片格式：JPG、JPEG、PNG、WEBP
- 生成过程约 30-60 秒
