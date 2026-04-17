#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import shutil
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize ZenTao settings for zxw-zentao-bug-fix.")
    parser.add_argument("--project-id", type=int, help="ZenTao project ID.")
    parser.add_argument("--human-owner", help="Human owner for confirmation and writeback.")
    parser.add_argument("--base-url", help="ZenTao base URL.")
    parser.add_argument("--account", help="ZenTao account.")
    parser.add_argument("--password", help="ZenTao password.")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Target project root where .codex/zentao-bug-fix.yaml will be written. Default: current directory.",
    )
    parser.add_argument(
        "--codex-home",
        help="Override Codex home directory. Default: CODEX_HOME or ~/.codex.",
    )
    return parser.parse_args()


def prompt_text(label: str, default: str | None = None, *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        prompt = f"{label}{suffix}: "
        value = getpass.getpass(prompt) if secret else input(prompt)
        value = value.strip()
        if value:
            return value
        if default:
            return default
        print(f"{label} is required.")


def prompt_int(label: str, default: int | None = None) -> int:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            print(f"{label} must be an integer.")


def normalize_base_url(value: str) -> str:
    cleaned = value.strip()
    return cleaned if cleaned.endswith("/") else f"{cleaned}/"


def toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def yaml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_zentao_block(base_url: str, account: str, password: str) -> str:
    return "\n".join(
        [
            "[mcp_servers.zentao]",
            'command = "npx"',
            'args = ["-y", "zentao-mcp"]',
            "",
            "[mcp_servers.zentao.env]",
            f'ZENTAO_BASE_URL = "{toml_string(normalize_base_url(base_url))}"',
            f'ZENTAO_ACCOUNT = "{toml_string(account)}"',
            f'ZENTAO_PASSWORD = "{toml_string(password)}"',
            'MCP_ENABLE_WRITE_TOOLS = "true"',
            "",
        ]
    )


def replace_or_append_block(text: str, block: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    end: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == "[mcp_servers.zentao]":
            start = idx
            break
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block.rstrip("\n").splitlines())
        return "\n".join(lines).rstrip("\n") + "\n"

    end = start + 1
    while end < len(lines):
        stripped = lines[end].strip()
        if stripped.startswith("[") and not stripped.startswith("[mcp_servers.zentao"):
            break
        end += 1

    new_lines = lines[:start] + block.rstrip("\n").splitlines() + lines[end:]
    return "\n".join(new_lines).rstrip("\n") + "\n"


def codex_home_dir(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser()
    env_value = os.environ.get("CODEX_HOME")
    if env_value:
        return Path(env_value).expanduser()
    return Path.home() / ".codex"


def config_targets(home: Path) -> list[Path]:
    candidates = [home / "config.toml", home / "config_api.toml"]
    existing = [path for path in candidates if path.exists()]
    if existing:
        return existing
    return [home / "config.toml"]


def backup_file(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup_file(path)
    path.write_text(content, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def format_yaml(project_id: int, human_owner: str) -> str:
    return "\n".join(
        [
            f"project_id: {project_id}",
            f'human_owner: "{yaml_string(human_owner)}"',
            "",
        ]
    )


def main() -> int:
    args = parse_args()

    project_id = args.project_id if args.project_id is not None else prompt_int("ZenTao project ID")
    human_owner = args.human_owner if args.human_owner else prompt_text("Human owner")
    base_url = args.base_url if args.base_url else prompt_text("ZenTao base URL")
    account = args.account if args.account else prompt_text("ZenTao account")
    password = args.password if args.password else prompt_text("ZenTao password", secret=True)

    project_root = Path(args.project_root).expanduser().resolve()
    project_config = project_root / ".codex" / "zentao-bug-fix.yaml"
    write_text(project_config, format_yaml(project_id, human_owner))

    block = render_zentao_block(base_url, account, password)
    home = codex_home_dir(args.codex_home)
    target_configs = config_targets(home)
    for config_path in target_configs:
        current = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        updated = replace_or_append_block(current, block)
        write_text(config_path, updated)

    print("ZenTao setup completed.")
    print(f"- project config: {project_config}")
    for config_path in target_configs:
        print(f"- codex config: {config_path}")
    print("- mcp server: zentao -> npx -y zentao-mcp")
    print("Next step: run zentao-bug-list-query or zentao-bug-fix-by-id inside the project repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
