# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "python-dotenv",
# ]
# ///

"""
NanoBanana API 调用脚本
支持纯文本生图和图片参考编辑
API 使用 SSE 流式响应
"""
import os
import json
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API 配置
API_HOST = os.getenv("NANO_BANANA_HOST", "https://grsaiapi.com")
API_KEY = os.getenv("NANO_BANANA_API_KEY", "")

# 接口地址
DRAW_URL = f"{API_HOST}/v1/draw/nano-banana"

# 默认参数
DEFAULT_MODEL = "nano-banana-pro"
DEFAULT_SIZE = "2K"  # 1K, 2K, 4K
DEFAULT_RATIO = "auto"  # auto, 1:1, 4:3, 3:4, 16:9, 9:16


def encode_image(image_path: str) -> str:
    """将图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime(image_path: str) -> str:
    """获取图片 MIME 类型"""
    ext = Path(image_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp"}
    return mime_map.get(ext, "image/jpeg")


def draw(prompt: str, images: list = None, model: str = DEFAULT_MODEL,
         size: str = DEFAULT_SIZE, ratio: str = DEFAULT_RATIO) -> dict:
    """
    调用绘画接口（SSE 流式响应）
    :param prompt: 提示词
    :param images: 参考图片路径列表（可选，支持多图）
    :param model: 模型名称
    :param size: 图片尺寸 (1K, 2K, 4K)
    :param ratio: 宽高比 (auto, 1:1, 4:3, 3:4, 16:9, 9:16)
    :return: 最终结果
    """
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "prompt": prompt,
        "imageSize": size,
        "aspectRatio": ratio
    }

    # 如果有参考图片，添加到请求中（支持多图）
    if images:
        urls = []
        for img_path in images:
            if img_path and os.path.exists(img_path):
                mime = get_image_mime(img_path)
                b64 = encode_image(img_path)
                urls.append(f"data:{mime};base64,{b64}")
        if urls:
            payload["urls"] = urls

    # 使用流式请求处理 SSE
    resp = requests.post(DRAW_URL, json=payload, headers=headers, timeout=300, stream=True)
    resp.raise_for_status()

    result = None
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data_str = line[5:].strip()  # 去掉 "data:" 前缀
        if not data_str:
            continue
        try:
            data = json.loads(data_str)
            status = data.get("status", "")
            progress = data.get("progress", 0)
            print(f"\r进度: {progress}% - {status}", end="", flush=True)
            result = data
        except json.JSONDecodeError:
            continue

    print()  # 换行
    return result


def download_image(url: str, save_path: str) -> str:
    """下载图片到本地"""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(resp.content)
    return save_path


def generate(prompt: str, images: list = None, output_dir: str = "./output",
             model: str = DEFAULT_MODEL, size: str = DEFAULT_SIZE,
             ratio: str = DEFAULT_RATIO) -> list:
    """完整的生成流程：提交任务 -> 等待完成 -> 下载图片"""
    print(f"提交任务: {prompt[:50]}...")
    result = draw(prompt, images, model, size, ratio)

    if not result:
        raise Exception("未获取到结果")

    status = result.get("status", "")
    if status == "failed":
        raise Exception(f"任务失败: {result.get('failure_reason', result.get('error', '未知错误'))}")

    # 下载生成的图片
    images = result.get("results") or []
    task_id = result.get("id", "unknown")
    saved = []
    for i, img_info in enumerate(images):
        # results 可能是 URL 字符串或包含 url 字段的对象
        if isinstance(img_info, dict):
            img_url = img_info.get("url", "")
        else:
            img_url = img_info
        if not img_url:
            continue
        filename = f"{task_id}_{i}.png"
        path = download_image(img_url, os.path.join(output_dir, filename))
        saved.append(path)
        print(f"已保存: {path}")

    return saved


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NanoBanana 绘图 API")
    parser.add_argument("prompt", help="提示词")
    parser.add_argument("-i", "--images", nargs="+", help="参考图片路径（支持多张）")
    parser.add_argument("-o", "--output", default="./output", help="输出目录")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="模型名称")
    parser.add_argument("-s", "--size", default=DEFAULT_SIZE,
                        choices=["1K", "2K", "4K"], help="图片尺寸")
    parser.add_argument("-r", "--ratio", default=DEFAULT_RATIO,
                        choices=["auto", "1:1", "4:3", "3:4", "16:9", "9:16"],
                        help="宽高比")
    args = parser.parse_args()

    if not API_KEY:
        print("错误: 请设置 NANO_BANANA_API_KEY 环境变量")
        exit(1)

    paths = generate(args.prompt, args.images, args.output,
                     args.model, args.size, args.ratio)
    print(f"\n生成完成，共 {len(paths)} 张图片")
