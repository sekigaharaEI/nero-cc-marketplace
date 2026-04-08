#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


PLACEHOLDER_MARKERS = {"[步骤]", "[结果]", "[期望]"}
STATUS_LABELS = {
    "active": "激活",
    "closed": "已关闭",
    "draft": "草稿",
    "reviewing": "评审中",
    "changing": "变更中",
    "launched": "已发布",
    "developing": "研发中",
    "planned": "已计划",
}
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "table", "tr", "section", "article", "h1", "h2", "h3", "h4"}


class DescriptionParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.parts.append("\n")
            return
        if tag != "img":
            return
        attr_map = dict(attrs)
        src = (attr_map.get("src") or "").strip()
        if src:
            self.images.append(normalize_asset_url(src, self.base_url))

    def handle_endtag(self, tag: str) -> None:
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export ZenTao stories into Markdown with screenshots.")
    parser.add_argument("--browse-url", help="ZenTao product browse URL. Product ID is parsed from this URL.")
    parser.add_argument("--product-id", type=int, help="ZenTao product ID.")
    parser.add_argument("--output", help="Output Markdown path.")
    parser.add_argument("--output-dir", help="Output directory. The script will generate a default Markdown filename in this folder.")
    parser.add_argument("--page-size", type=int, default=50, help="Stories per page. Default: 50.")
    parser.add_argument("--max-items", type=int, default=0, help="Export only the first N stories for sampling.")
    parser.add_argument("--base-url", help="ZenTao base URL, e.g. http://host/zentao/")
    parser.add_argument("--account", help="ZenTao account.")
    parser.add_argument("--password", help="ZenTao password.")
    return parser.parse_args()


def parse_product_id(browse_url: str) -> int:
    match = re.search(r"product-browse-(\d+)-", browse_url)
    if not match:
        raise SystemExit(f"Could not parse product ID from browse URL: {browse_url}")
    return int(match.group(1))


def ensure_trailing_slash(url: str) -> str:
    return url if url.endswith("/") else f"{url}/"


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def config_candidates() -> list[Path]:
    paths: list[Path] = []
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        paths.extend([Path(codex_home) / "config.toml", Path(codex_home) / "config_api.toml"])
    home_codex = Path.home() / ".codex"
    paths.extend([home_codex / "config.toml", home_codex / "config_api.toml"])
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def load_zentao_settings() -> tuple[dict[str, str], str | None]:
    settings = {
        "base_url": os.environ.get("ZENTAO_BASE_URL", ""),
        "account": os.environ.get("ZENTAO_ACCOUNT", ""),
        "password": os.environ.get("ZENTAO_PASSWORD", ""),
    }
    source: str | None = None

    for config_path in config_candidates():
        if not config_path.exists():
            continue
        try:
            data = load_toml(config_path)
        except Exception:
            continue
        env = (((data.get("mcp_servers") or {}).get("zentao") or {}).get("env") or {})
        if not isinstance(env, dict):
            continue
        if not source and env:
            source = str(config_path)
        settings["base_url"] = settings["base_url"] or str(env.get("ZENTAO_BASE_URL", ""))
        settings["account"] = settings["account"] or str(env.get("ZENTAO_ACCOUNT", ""))
        settings["password"] = settings["password"] or str(env.get("ZENTAO_PASSWORD", ""))

    return settings, source


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str, str, str | None]:
    settings, source = load_zentao_settings()
    base_url = args.base_url or settings["base_url"]
    account = args.account or settings["account"]
    password = args.password or settings["password"]

    missing = [name for name, value in (("ZENTAO_BASE_URL", base_url), ("ZENTAO_ACCOUNT", account), ("ZENTAO_PASSWORD", password)) if not value]
    if missing:
        hint = "Fill them in shell env or in ~/.codex/config.toml under [mcp_servers.zentao.env]."
        if source:
            hint = f"Fill them in shell env or in {source} under [mcp_servers.zentao.env]."
        raise SystemExit(f"Missing ZenTao settings: {', '.join(missing)}. {hint}")

    return ensure_trailing_slash(base_url), account, password, source


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_root = urljoin(ensure_trailing_slash(base_url), "api.php/v1/")
    url = urljoin(api_root, path.lstrip("/"))
    if query:
        url = f"{url}?{urlencode(query, doseq=True)}"

    headers = {"Accept": "application/json"}
    data: bytes | None = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Token"] = token

    request = Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:  # pragma: no cover
        payload = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"ZenTao API error {exc.code} for {url}: {payload}") from exc
    except URLError as exc:  # pragma: no cover
        raise SystemExit(f"Could not reach ZenTao API at {url}: {exc}") from exc

    parsed = json.loads(raw)
    return parsed.get("data", parsed)


def get_token(base_url: str, account: str, password: str) -> str:
    data = request_json(base_url, "/tokens", method="POST", body={"account": account, "password": password})
    token = data.get("token")
    if not token:
        raise SystemExit("ZenTao token response did not contain a token.")
    return str(token)


def normalize_asset_url(src: str, base_url: str) -> str:
    if src.startswith("{") and src.endswith("}"):
        return urljoin(base_url, f"file-read-{src.strip('{}')}")
    return urljoin(base_url, src)


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def clean_text(text: str) -> str:
    lines: list[str] = []
    previous_blank = False
    for raw_line in text.splitlines():
        line = raw_line.replace("\xa0", " ").strip()
        if line in PLACEHOLDER_MARKERS:
            continue
        if not line:
            if lines and not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        lines.append(line)
        previous_blank = False
    return "\n".join(lines).strip()


def parse_description(html: str | None, base_url: str) -> tuple[str, list[str]]:
    if not html:
        return "", []
    parser = DescriptionParser(base_url)
    parser.feed(html)
    text = clean_text("".join(parser.parts))
    return text, dedupe(parser.images)


def status_label(status: str | None) -> str:
    if not status:
        return "未知"
    return STATUS_LABELS.get(status, status)


def format_date(value: str | None) -> str:
    if not value or value.startswith("0000-00-00"):
        return "未知"
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).astimezone().strftime("%Y-%m-%d")
    except ValueError:
        return value[:10]


def build_record(story: dict[str, Any], bug: dict[str, Any] | None, base_url: str) -> dict[str, Any]:
    description, images = parse_description(story.get("spec"), base_url)
    bug_payload = bug or {}

    if (not description or not story.get("moduleTitle")) and bug_payload:
        bug_description, bug_images = parse_description(bug_payload.get("steps"), base_url)
        if not description and bug_description:
            description = bug_description
        if not images and bug_images:
            images = bug_images

    if not description:
        description = "需求正文主要通过截图说明。" if images else "无文本描述，需结合禅道原单或附件进一步确认。"

    return {
        "id": story.get("id", ""),
        "title": story.get("title", ""),
        "description": description,
        "images": images,
        "module": story.get("moduleTitle") or bug_payload.get("moduleTitle") or "未设置",
        "status": status_label(story.get("status")),
        "created_date": format_date(story.get("openedDate") or bug_payload.get("openedDate")),
        "product_name": story.get("productName") or bug_payload.get("productName") or f"产品{story.get('product', '')}",
    }


def render_markdown(records: list[dict[str, Any]], product_id: int, product_name: str, source_ref: str, total: int) -> str:
    lines = [
        "# 禅道字段提取",
        "",
        f"- 来源页面：`{source_ref}`",
        f"- 范围：产品 `{product_id}`「{product_name}」研发需求，共 `{total}` 条",
        "- 提取字段：研发需求名称、需求描述、所属模块、当前状态、创建日期",
        "- 说明：所属模块优先取研发需求详情；若研发需求未挂模块，则补用源 Bug 模块；仍无法判断时标记为“未设置”",
        "- 说明：需求描述中的截图按原禅道图片地址保留",
    ]

    for record in records:
        lines.extend(
            [
                "",
                f"## {record['id']}",
                "",
                f"- 研发需求名称：{record['title']}",
                "- 需求描述：",
                record["description"],
                "- 需求描述截图：",
            ]
        )
        if record["images"]:
            lines.extend(f"![]({image})" for image in record["images"])
        else:
            lines.append("无")
        lines.extend(
            [
                f"- 所属模块：{record['module']}",
                f"- 当前状态：{record['status']}",
                f"- 创建日期：{record['created_date']}",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def default_output_path(product_name: str, product_id: int) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    safe_name = re.sub(r'[<>:"/\\\\|?*]+', "_", product_name).strip() or f"产品{product_id}"
    filename = f"禅道_{safe_name}_研发需求_字段提取_{today}.md"
    return Path.cwd() / filename


def resolve_output_path(args: argparse.Namespace, product_name: str, product_id: int) -> Path:
    if args.output and args.output_dir:
        raise SystemExit("Use either --output or --output-dir, not both.")

    default_name = default_output_path(product_name, product_id).name
    if args.output_dir:
        return Path(args.output_dir) / default_name

    if args.output:
        output_path = Path(args.output)
        if output_path.exists() and output_path.is_dir():
            return output_path / default_name
        return output_path

    return default_output_path(product_name, product_id)


def main() -> int:
    args = parse_args()
    product_id = args.product_id or (parse_product_id(args.browse_url) if args.browse_url else None)
    if not product_id:
        raise SystemExit("Provide either --product-id or --browse-url.")

    base_url, account, password, credential_source = resolve_credentials(args)
    token = get_token(base_url, account, password)

    page = 1
    total = 0
    records: list[dict[str, Any]] = []
    product_name = f"产品{product_id}"
    page_size = max(args.page_size, 1)

    while True:
        page_data = request_json(base_url, "/stories", token=token, query={"product": product_id, "page": page, "limit": page_size})
        stories = page_data.get("stories", [])
        total = int(page_data.get("total", total or 0))
        if not stories:
            break

        for story_stub in stories:
            story_id = story_stub.get("id")
            story_detail = request_json(base_url, f"/stories/{story_id}", token=token)
            bug_payload: dict[str, Any] | None = None
            from_bug = story_detail.get("fromBug")
            if from_bug:
                bug_payload = request_json(base_url, f"/bugs/{from_bug}", token=token)
            record = build_record(story_detail, bug_payload, base_url)
            product_name = record["product_name"] or product_name
            records.append(record)
            if args.max_items and len(records) >= args.max_items:
                break

        if args.max_items and len(records) >= args.max_items:
            break
        if len(stories) < page_size:
            break
        page += 1

    total_for_header = total or len(records)
    output_path = resolve_output_path(args, product_name, product_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_ref = args.browse_url or f"product={product_id}"
    markdown = render_markdown(records, product_id, product_name, source_ref, total_for_header)
    output_path.write_text(markdown, encoding="utf-8")

    if credential_source:
        print(f"Using ZenTao credentials from {credential_source}", file=sys.stderr)
    print(f"Wrote {len(records)} stories to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
