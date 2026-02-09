# 提示词构建逻辑

根据用户输入的各项参数，动态构建最终提示词。

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
