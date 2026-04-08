#!/usr/bin/env python3
"""
PDF 转图片脚本
将 PDF 的每一页导出为单独的 PNG 图片文件。

用法:
  python pdf_to_images.py <pdf_path> <output_dir> [--dpi 300] [--format png]

输出:
  JSON 格式的执行结果，供 Claude 读取。
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="PDF 转图片")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--dpi", type=int, default=300, help="输出 DPI（默认300）")
    parser.add_argument("--format", default="png", choices=["png", "jpg"], help="输出格式")
    args = parser.parse_args()

    result = {
        "success": False,
        "total_pages": 0,
        "output_dir": args.output_dir,
        "files": [],
        "error": ""
    }

    try:
        import fitz  # PyMuPDF
    except ImportError:
        result["error"] = "PyMuPDF 未安装，请运行: pip install PyMuPDF"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not os.path.exists(args.pdf_path):
        result["error"] = f"PDF 文件不存在: {args.pdf_path}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        doc = fitz.open(args.pdf_path)
        result["total_pages"] = len(doc)

        zoom = args.dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)

            filename = f"pic-{page_num + 1:02d}.{args.format}"
            filepath = os.path.join(args.output_dir, filename)

            if args.format == "jpg":
                pix.save(filepath, jpg_quality=95)
            else:
                pix.save(filepath)

            result["files"].append(filepath)

        doc.close()
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
