#!/usr/bin/env python3
"""
daemon-archon 初始化向导
支持 conda 环境检测、自动/手动安装、国内镜像源
"""

import subprocess
import sys
import os
from pathlib import Path


# 国内镜像源
PYPI_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"

# 必需的包
REQUIRED_PACKAGES = ["fastapi", "uvicorn", "apscheduler", "psutil", "anthropic", "croniter"]


def run_command(cmd, capture=True, check=False):
    """运行命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True,
            timeout=300
        )
        if check and result.returncode != 0:
            return None
        return result
    except Exception as e:
        return None


def check_conda():
    """检测 conda 环境"""
    result = run_command("conda --version")
    if result and result.returncode == 0:
        return True, result.stdout.strip()
    return False, None


def get_conda_envs():
    """获取 conda 环境列表"""
    result = run_command("conda env list --json")
    if result and result.returncode == 0:
        import json
        try:
            data = json.loads(result.stdout)
            return data.get("envs", [])
        except:
            pass
    return []


def get_current_conda_env():
    """获取当前激活的 conda 环境"""
    env_name = os.environ.get("CONDA_DEFAULT_ENV", "")
    env_path = os.environ.get("CONDA_PREFIX", "")
    if env_name:
        return env_name, env_path
    return None, None


def get_python_version(python_path="python3"):
    """获取 Python 版本"""
    result = run_command(f"{python_path} --version")
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def check_claude_cli():
    """检查 Claude CLI"""
    result = run_command("claude --version")
    if result and result.returncode == 0:
        return True, result.stdout.strip()
    return False, "未安装"


def check_python_package(package, python_path="python3"):
    """检查 Python 包"""
    result = run_command(f'{python_path} -c "import {package}; print(getattr({package}, \'__version__\', \'已安装\'))"')
    if result and result.returncode == 0:
        version = result.stdout.strip()
        return True, f"已安装 ({version})"
    return False, "未安装"


def check_work_dir():
    """检查工作目录"""
    work_dir = Path.home() / ".claude" / "daemon-archon"
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
        test_file = work_dir / ".test"
        test_file.write_text("test")
        test_file.unlink()
        return True, str(work_dir)
    except Exception as e:
        return False, str(e)


def create_conda_env(env_name="daemon-archon", python_version="3.10"):
    """创建 conda 环境"""
    print(f"\n正在创建 conda 环境 {env_name}...")
    cmd = f"conda create -n {env_name} python={python_version} -y"
    print(f"  {cmd}")
    result = run_command(cmd, capture=False)
    if result and result.returncode == 0:
        print("环境创建成功！")
        return True
    else:
        print("环境创建失败")
        return False


def install_packages(packages, python_path="python3", use_mirror=True):
    """安装 Python 包"""
    pkg_str = " ".join(packages)
    if use_mirror:
        cmd = f"{python_path} -m pip install -i {PYPI_MIRROR} {pkg_str}"
    else:
        cmd = f"{python_path} -m pip install {pkg_str}"

    print(f"\n正在安装依赖...")
    print(f"  {cmd}")
    result = run_command(cmd, capture=False)
    return result and result.returncode == 0


def get_user_choice(prompt, options):
    """获取用户选择"""
    while True:
        try:
            choice = input(prompt).strip()
            if choice in options:
                return choice
            print(f"无效选项，请输入 {'/'.join(options)}")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            sys.exit(1)


def step1_environment():
    """第一步：环境选择"""
    print("\n[1/3] 环境检测")
    print("-" * 40)

    has_conda, conda_version = check_conda()

    if has_conda:
        print(f"检测到 conda ({conda_version})")
        current_env, current_path = get_current_conda_env()

        if current_env:
            py_version = get_python_version()
            print(f"当前环境: {current_env} ({py_version})")

        print("\n请选择 Python 环境：")
        if current_env:
            print(f"  1. 使用当前环境: {current_env}")
        else:
            print("  1. 使用 base 环境")
        print("  2. 新建 daemon-archon 专用环境")
        print("  3. 使用系统 Python")

        choice = get_user_choice("\n请输入选项 [1/2/3]: ", ["1", "2", "3"])

        if choice == "1":
            # 使用当前 conda 环境
            if current_path:
                python_path = os.path.join(current_path, "bin", "python")
            else:
                python_path = "python"
            return python_path, current_env or "base"

        elif choice == "2":
            # 新建环境
            if create_conda_env("daemon-archon"):
                # 获取新环境的 python 路径
                result = run_command("conda info --base")
                if result and result.returncode == 0:
                    conda_base = result.stdout.strip()
                    python_path = os.path.join(conda_base, "envs", "daemon-archon", "bin", "python")
                    return python_path, "daemon-archon"
            print("创建环境失败，将使用系统 Python")
            return "python3", "system"

        else:
            # 使用系统 Python
            return "python3", "system"

    else:
        print("未检测到 conda，将使用系统 Python")
        py_version = get_python_version()
        if py_version:
            print(f"系统 Python: {py_version}")
        return "python3", "system"


def step2_check_dependencies(python_path):
    """第二步：依赖检查"""
    print("\n[2/3] 依赖检查")
    print("-" * 40)

    print(f"\n{'检查项':<30} {'状态':<6} {'详情'}")
    print("-" * 60)

    checks = []
    missing_packages = []

    # Claude CLI
    ok, detail = check_claude_cli()
    checks.append(("Claude CLI", ok, detail))

    # Python 版本
    py_version = get_python_version(python_path)
    if py_version:
        checks.append(("Python 版本", True, py_version))
    else:
        checks.append(("Python 版本", False, "无法获取"))

    # Python 包
    for pkg in REQUIRED_PACKAGES:
        ok, detail = check_python_package(pkg, python_path)
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

    return all_ok, missing_packages


def step3_install(python_path, missing_packages):
    """第三步：安装依赖"""
    print("\n[3/3] 安装依赖")
    print("-" * 40)

    if not missing_packages:
        print("所有依赖已安装")
        return True

    print(f"\n检测到 {len(missing_packages)} 个缺失的依赖包: {', '.join(missing_packages)}")

    print("\n请选择安装方式：")
    print("  1. 自动安装（使用清华镜像源）")
    print("  2. 手动安装（显示安装命令）")

    choice = get_user_choice("\n请输入选项 [1/2]: ", ["1", "2"])

    if choice == "1":
        # 自动安装
        success = install_packages(missing_packages, python_path, use_mirror=True)
        if success:
            print("\n安装完成！")
            return True
        else:
            print("\n安装失败，请尝试手动安装")
            return False
    else:
        # 手动安装
        pkg_str = " ".join(missing_packages)
        print("\n请手动运行以下命令安装依赖：")
        print(f"\n  {python_path} -m pip install -i {PYPI_MIRROR} {pkg_str}")
        print("\n或者安装所有依赖：")
        script_dir = Path(__file__).parent
        req_file = script_dir / "server" / "requirements.txt"
        print(f"\n  {python_path} -m pip install -i {PYPI_MIRROR} -r {req_file}")
        return False


def save_env_config(python_path, env_name):
    """保存环境配置"""
    config_dir = Path.home() / ".claude" / "daemon-archon"
    config_dir.mkdir(parents=True, exist_ok=True)

    env_config = config_dir / "env.conf"
    env_config.write_text(f"PYTHON_PATH={python_path}\nENV_NAME={env_name}\n")
    print(f"\n环境配置已保存到: {env_config}")


def main():
    print("daemon-archon 初始化向导")
    print("=" * 40)

    # 第一步：环境选择
    python_path, env_name = step1_environment()

    # 第二步：依赖检查
    all_ok, missing_packages = step2_check_dependencies(python_path)

    # 第三步：安装依赖
    if missing_packages:
        install_ok = step3_install(python_path, missing_packages)
    else:
        install_ok = True

    # 保存环境配置
    save_env_config(python_path, env_name)

    print()
    if all_ok or install_ok:
        print("✓ 初始化完成，可以运行 /archon-start 启动服务")
        return 0
    else:
        print("✗ 初始化未完成，请先安装缺失的依赖")
        return 1


if __name__ == "__main__":
    sys.exit(main())
