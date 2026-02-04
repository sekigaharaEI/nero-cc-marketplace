#!/usr/bin/env python3
"""
daemon-archon 环境检查脚本
"""

import subprocess
import sys
import os
from pathlib import Path


def check_claude_cli():
    """检查 Claude CLI"""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        return False, "未安装"
    except FileNotFoundError:
        return False, "未安装"
    except Exception as e:
        return False, str(e)


def check_python_version():
    """检查 Python 版本"""
    version = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 8):
        return True, version
    return False, f"{version} (需要 >= 3.8)"


def check_python_package(package):
    """检查 Python 包"""
    try:
        module = __import__(package)
        version = getattr(module, "__version__", "已安装")
        return True, f"已安装 ({version})"
    except ImportError:
        return False, "未安装"


def check_work_dir():
    """检查工作目录"""
    work_dir = Path.home() / ".claude" / "daemon-archon"
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
        # 测试写入权限
        test_file = work_dir / ".test"
        test_file.write_text("test")
        test_file.unlink()
        return True, str(work_dir)
    except Exception as e:
        return False, str(e)


def main():
    print("daemon-archon 环境检查")
    print("======================")
    print()
    print(f"{'检查项':<30} {'状态':<6} {'详情'}")
    print("-" * 60)

    checks = []
    missing_packages = []

    # Claude CLI
    ok, detail = check_claude_cli()
    checks.append(("Claude CLI", ok, detail))

    # Python 版本
    ok, detail = check_python_version()
    checks.append(("Python 版本", ok, detail))

    # Python 包
    packages = ["fastapi", "uvicorn", "apscheduler", "psutil"]
    for pkg in packages:
        ok, detail = check_python_package(pkg)
        checks.append((f"Python 包: {pkg}", ok, detail))
        if not ok:
            missing_packages.append(pkg)

    # 工作目录
    ok, detail = check_work_dir()
    checks.append(("工作目录权限", ok, detail))

    # 输出结果
    all_ok = True
    for name, ok, detail in checks:
        status = "✓" if ok else "✗"
        print(f"{name:<30} {status:<6} {detail}")
        if not ok:
            all_ok = False

    print()

    if not all_ok:
        print("修复建议")
        print("--------")
        if missing_packages:
            print("请运行以下命令安装缺失的依赖：")
            print(f"  pip3 install {' '.join(missing_packages)}")
            print()
            script_dir = Path(__file__).parent
            req_file = script_dir / "server" / "requirements.txt"
            print("或者一次性安装所有依赖：")
            print(f"  pip3 install -r {req_file}")
        return 1
    else:
        print("✓ 环境检查通过，可以启动 Archon 服务")
        print()
        print("运行以下命令启动服务：")
        script_dir = Path(__file__).parent
        print(f"  bash {script_dir}/start_server.sh")
        return 0


if __name__ == "__main__":
    sys.exit(main())
