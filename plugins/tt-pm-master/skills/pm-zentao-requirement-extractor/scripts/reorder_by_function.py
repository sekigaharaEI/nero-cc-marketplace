#!/usr/bin/env python3
"""Reorder a ZenTao field-extraction Markdown by AI-decided functional groups.

The script does NOT make semantic decisions. The caller (an AI) supplies a
``groups.json`` describing how stories should be bucketed and ordered:

    [
      {"name": "<group title>", "ids": [<story_id>, ...]},
      ...
    ]

For each ``## <id>`` block in the source file the script looks up its group,
demotes it to ``### <id>``, and emits all blocks under their group's ``##``
heading in the order given by the JSON. The script validates that every source
ID appears in exactly one group (no missing, no duplicates, no extras) and
aborts otherwise so silent data loss cannot happen.

Story bodies, screenshots, and field values are copied verbatim -- only the
section ordering and heading levels change.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reorder ZenTao field-extraction Markdown by functional groups."
    )
    parser.add_argument("--src", required=True, help="Source Markdown produced by export_zentao_requirements.py.")
    parser.add_argument(
        "--groups",
        required=True,
        help='Groups JSON file. Format: [{"name": "<title>", "ids": [<id>, ...]}, ...]',
    )
    parser.add_argument("--output", help="Explicit output Markdown path.")
    parser.add_argument(
        "--output-dir",
        help="Output directory; the script auto-names the file as <src-stem>_按功能分组_<YYYY-MM-DD>.md.",
    )
    return parser.parse_args()


def load_groups(path: Path) -> list[tuple[str, list[int]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit(f"Groups JSON must be a list of objects; got {type(raw).__name__}.")
    groups: list[tuple[str, list[int]]] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise SystemExit(f"Group #{index} must be an object with 'name' and 'ids'.")
        name = entry.get("name")
        ids = entry.get("ids")
        if not isinstance(name, str) or not name.strip():
            raise SystemExit(f"Group #{index} is missing a non-empty 'name'.")
        if not isinstance(ids, list) or not ids:
            raise SystemExit(f"Group '{name}' must have a non-empty 'ids' list.")
        normalized_ids: list[int] = []
        for raw_id in ids:
            try:
                normalized_ids.append(int(raw_id))
            except (TypeError, ValueError) as exc:
                raise SystemExit(f"Group '{name}' has a non-integer id: {raw_id!r}") from exc
        groups.append((name.strip(), normalized_ids))
    return groups


def split_source(text: str) -> tuple[str, dict[int, str]]:
    parts = re.split(r"(?m)^## ", text)
    header = parts[0].rstrip()
    bodies: dict[int, str] = {}
    for raw in parts[1:]:
        match = re.match(r"(\d+)\b", raw)
        if not match:
            continue
        sid = int(match.group(1))
        if sid in bodies:
            raise SystemExit(f"Duplicate story id in source: {sid}")
        bodies[sid] = raw.rstrip()
    return header, bodies


def validate_coverage(bodies: dict[int, str], groups: list[tuple[str, list[int]]]) -> None:
    flat: list[int] = []
    for _, ids in groups:
        flat.extend(ids)
    duplicates = sorted({sid for sid in flat if flat.count(sid) > 1})
    missing = sorted(set(flat) - set(bodies.keys()))
    extra = sorted(set(bodies.keys()) - set(flat))
    issues: list[str] = []
    if duplicates:
        issues.append(f"duplicate ids in groups: {duplicates}")
    if missing:
        issues.append(f"ids in groups but not in source: {missing}")
    if extra:
        issues.append(f"ids in source but not assigned to any group: {extra}")
    if issues:
        raise SystemExit("Group coverage validation failed -- " + "; ".join(issues))


def render(header: str, bodies: dict[int, str], groups: list[tuple[str, list[int]]]) -> str:
    augmented_header = header + (
        '\n- 排序：按"功能"语义聚合（同一功能的需求归到同一节），'
        "组之间按组内最高优先级降序、同档按规模降序排；"
        "组内按优先级 1(最高) → 4(低) 排序"
    )
    chunks: list[str] = [augmented_header]
    for name, ids in groups:
        chunks.append(f"\n## {name}\n")
        for sid in ids:
            chunks.append("### " + bodies[sid])
    return "\n\n".join(chunks).rstrip() + "\n"


def resolve_output_path(args: argparse.Namespace, src: Path) -> Path:
    if args.output and args.output_dir:
        raise SystemExit("Use either --output or --output-dir, not both.")
    today = datetime.now().strftime("%Y-%m-%d")
    default_name = f"{src.stem}_按功能分组_{today}.md"
    if args.output_dir:
        return Path(args.output_dir) / default_name
    if args.output:
        path = Path(args.output)
        if path.exists() and path.is_dir():
            return path / default_name
        return path
    return src.parent / default_name


def main() -> int:
    args = parse_args()
    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"Source not found: {src}")
    groups_path = Path(args.groups)
    if not groups_path.exists():
        raise SystemExit(f"Groups JSON not found: {groups_path}")

    text = src.read_text(encoding="utf-8")
    header, bodies = split_source(text)
    groups = load_groups(groups_path)
    validate_coverage(bodies, groups)

    output_path = resolve_output_path(args, src)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(header, bodies, groups), encoding="utf-8")

    total = sum(len(ids) for _, ids in groups)
    print(f"Wrote {total} stories in {len(groups)} groups to {output_path}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
