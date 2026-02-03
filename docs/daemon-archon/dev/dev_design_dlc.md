# daemon-archon 开发设计补充文档 (DLC)

> 本文档是对 `dev_design.md` 的补充，记录在设计审查中发现的遗漏点和详细实现方案
>
> **创建日期**: 2026-02-03
> **基于文档**: design.md, dev_design.md
> **审查问题来源**: REBOOT.txt

---

## 文档说明

本文档针对以下 5 个关键实现问题提供详细的技术方案：

1. **Probe 模式监控机制** - 如何监控子 Probe、查看执行状态、日志位置、纠偏实现
2. **Cron 执行引擎选型** - 跨平台后台执行方案（Linux/Windows）
3. **系统通知机制** - 各种通知方式的具体实现
4. **人工纠偏介入** - 用户如何介入和接管任务
5. **其他落地问题** - Session ID 管理、并发安全、错误恢复等

---

## 一、Probe 模式监控机制详细设计（Linux）

> **核心架构**：
> - **Probe**：子 Claude Code CLI，通过 bash 后台启动，执行长期任务
> - **Archon**：父 Claude Code CLI，通过定时任务启动，监控和纠偏 Probe
> - **两步流程**：1) 启动 Probe 并获取参数 → 2) 启动定时任务让 Archon 监控

---

### 1.1 Probe 启动流程（两步法）

#### 1.1.1 第一步：Bash 后台启动 Probe

**启动脚本**: `scripts/start_probe.sh`

```bash
#!/bin/bash
# 启动 Probe（子 Claude Code CLI）并记录相关参数

# 参数
TASK_ID="$1"
PROJECT_PATH="$2"
INITIAL_PROMPT="$3"
LOG_DIR="$HOME/.claude/daemon-archon/${TASK_ID}"

# 创建任务目录
mkdir -p "$LOG_DIR"

# 后台启动 Claude Code CLI，输出重定向到日志
nohup claude -p "$INITIAL_PROMPT" \
    --session-id "$TASK_ID" \
    > "$LOG_DIR/probe_stdout.log" \
    2> "$LOG_DIR/probe_stderr.log" &

# 获取 PID
PROBE_PID=$!

# 等待一小段时间，确保进程启动
sleep 2

# 检查进程是否存活
if ps -p $PROBE_PID > /dev/null 2>&1; then
    echo "Probe 启动成功"
    echo "PID: $PROBE_PID"
    echo "Session ID: $TASK_ID"
    echo "日志目录: $LOG_DIR"

    # 输出 JSON 格式（供后续解析）
    echo "{\"pid\": $PROBE_PID, \"session_id\": \"$TASK_ID\", \"log_dir\": \"$LOG_DIR\"}"
else
    echo "Probe 启动失败"
    exit 1
fi
```

**使用方式**:
```bash
./start_probe.sh "20260203_143000_probe" "/home/user/project" "请重构 src/legacy 目录"
```

#### 1.1.2 第二步：获取参数并保存配置

**实现位置**: `scripts/probe_manager.py`

```python
import subprocess
import os
import json
import re
from datetime import datetime
from pathlib import Path

def start_probe(task_id, initial_prompt, project_path):
    """
    启动 Probe 并获取相关参数

    流程：
    1. 调用 bash 脚本后台启动 Probe
    2. 从输出中解析 PID 和 session_id
    3. 保存配置到 probe_config.json

    Args:
        task_id: 任务 ID（同时作为 session_id）
        initial_prompt: 初始提示词
        project_path: 项目路径

    Returns:
        dict: Probe 配置信息
    """
    # 1. 调用启动脚本
    script_path = Path(__file__).parent / "start_probe.sh"

    result = subprocess.run(
        ["bash", str(script_path), task_id, project_path, initial_prompt],
        capture_output=True,
        text=True,
        cwd=project_path
    )

    if result.returncode != 0:
        raise RuntimeError(f"启动 Probe 失败: {result.stderr}")

    # 2. 从输出中解析 JSON
    output = result.stdout

    # 查找 JSON 行
    json_match = re.search(r'\{.*\}', output)
    if not json_match:
        raise RuntimeError(f"无法解析 Probe 启动输出: {output}")

    probe_info = json.loads(json_match.group())

    # 3. 构造完整配置
    config = {
        "task_id": task_id,
        "mode": "probe",
        "name": f"Probe 任务 - {task_id}",
        "project_path": project_path,
        "created_at": datetime.utcnow().isoformat() + "Z",

        "probe": {
            "pid": probe_info["pid"],
            "session_id": probe_info["session_id"],
            "log_dir": probe_info["log_dir"],
            "initial_prompt": initial_prompt,
            "stdout_log": f"{probe_info['log_dir']}/probe_stdout.log",
            "stderr_log": f"{probe_info['log_dir']}/probe_stderr.log"
        },

        "schedule": {
            "check_interval_minutes": 5,
            "next_check": None  # 由定时任务管理
        },

        "correction": {
            "max_auto_corrections": 3,
            "current_count": 0,
            "escalate_after_failures": 2
        },

        "criteria": {
            "success_indicators": ["任务完成", "测试通过"],
            "failure_indicators": ["错误", "失败", "Error"],
            "completion_keywords": ["任务完成", "重构完成"]
        },

        "state": {
            "status": "active",
            "last_check": None,
            "last_correction": None
        }
    }

    # 4. 保存配置
    save_probe_config(task_id, config)

    return config

def save_probe_config(task_id, config):
    """
    保存 Probe 配置到 probe_config.json
    """
    task_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    config_file = task_dir / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # 同时创建 status 文件
    status_file = task_dir / "status"
    with open(status_file, 'w') as f:
        f.write("active")

    # 创建 destination.md（任务目标）
    destination_file = task_dir / "destination.md"
    with open(destination_file, 'w', encoding='utf-8') as f:
        f.write(f"""# 任务目标

## 核心目标
{config['probe']['initial_prompt']}

## 验收标准
- [ ] 任务按要求完成
- [ ] 无严重错误

## 完成标志
当 Probe 输出包含以下关键词时认为完成：
{', '.join(config['criteria']['completion_keywords'])}
""")

    return config_file
```

#### 1.1.3 第三步：启动 Archon 定时监控任务

**启动定时任务脚本**: `scripts/setup_archon_cron.sh`

```bash
#!/bin/bash
# 为指定的 Probe 任务设置 Archon 定时监控

TASK_ID="$1"
CHECK_INTERVAL="${2:-5}"  # 默认 5 分钟

# Archon 监控脚本路径
ARCHON_SCRIPT="$HOME/.claude/plugins/daemon-archon/scripts/archon_check.py"

# 日志文件
LOG_FILE="$HOME/.claude/daemon-archon/${TASK_ID}/archon.log"

# 生成 cron 条目
CRON_ENTRY="*/${CHECK_INTERVAL} * * * * python3 ${ARCHON_SCRIPT} ${TASK_ID} >> ${LOG_FILE} 2>&1"

# 添加到 crontab（避免重复）
(crontab -l 2>/dev/null | grep -v "archon_check.py ${TASK_ID}"; echo "$CRON_ENTRY") | crontab -

echo "已设置 Archon 定时监控任务"
echo "任务 ID: $TASK_ID"
echo "检查间隔: 每 ${CHECK_INTERVAL} 分钟"
echo "日志文件: $LOG_FILE"
```

---

### 1.2 Probe 进程管理

#### 1.2.1 检测 Probe 进程状态

```python
import psutil

def check_probe_process(pid):
    """
    检查 Probe 进程是否存活

    Args:
        pid: 进程 PID

    Returns:
        dict: {
            "alive": bool,
            "status": "running" | "zombie" | "stopped" | "dead",
            "cpu_percent": float,
            "memory_mb": float
        }
    """
    try:
        process = psutil.Process(pid)
        status = process.status()

        return {
            "alive": True,
            "status": status,
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_mb": process.memory_info().rss / 1024 / 1024
        }
    except psutil.NoSuchProcess:
        return {
            "alive": False,
            "status": "dead",
            "cpu_percent": 0,
            "memory_mb": 0
        }
```

#### 1.2.2 终止 Probe 进程

```python
import psutil

def stop_probe(pid, graceful=True, timeout=30):
    """
    终止 Probe 进程

    Args:
        pid: 进程 PID
        graceful: 是否优雅终止（SIGTERM vs SIGKILL）
        timeout: 优雅终止的超时时间（秒）

    Returns:
        bool: 是否成功终止
    """
    try:
        process = psutil.Process(pid)

        if graceful:
            process.terminate()
            try:
                process.wait(timeout=timeout)
                return True
            except psutil.TimeoutExpired:
                process.kill()
                return True
        else:
            process.kill()
            return True

    except psutil.NoSuchProcess:
        return True
    except Exception as e:
        logging.error(f"终止进程 {pid} 失败: {e}")
        return False
```

---

### 1.3 日志查看

**设计决策**：不需要额外命令，用户直接使用 `tail` 命令查看日志。

**日志文件位置**：
```
~/.claude/daemon-archon/{task_id}/
├── probe_stdout.log    # Probe 标准输出
├── probe_stderr.log    # Probe 错误输出
└── archon.log          # Archon 监控日志
```

**查看方式**：
```bash
# 查看 Probe 输出
tail -f ~/.claude/daemon-archon/20260203_143000_probe/probe_stdout.log

# 查看 Archon 监控日志
tail -f ~/.claude/daemon-archon/20260203_143000_probe/archon.log

# 查看最近 100 行
tail -n 100 ~/.claude/daemon-archon/20260203_143000_probe/probe_stdout.log
```

---

### 1.4 Transcript 读取与分析

#### 1.4.1 定位 Transcript 文件

**解决方案**: 使用 `claude --list-sessions` 命令查询

```python
import subprocess
import json

def get_transcript_path(session_id):
    """
    获取指定 session 的 transcript 文件路径

    Args:
        session_id: 会话 ID

    Returns:
        str: transcript 文件的完整路径，如果未找到返回 None
    """
    try:
        result = subprocess.run(
            ["claude", "--list-sessions", "--format=json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            logging.error(f"列出会话失败: {result.stderr}")
            return None

        # 解析 JSON 输出
        sessions = json.loads(result.stdout)

        # 查找匹配的 session
        for session in sessions:
            if session.get("session_id") == session_id:
                return session.get("transcript_path")

        logging.warning(f"未找到 session_id={session_id} 的会话")
        return None

    except subprocess.TimeoutExpired:
        logging.error("列出会话超时")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"解析会话列表失败: {e}")
        return None
    except Exception as e:
        logging.error(f"获取 transcript 路径失败: {e}")
        return None
```

**备选方案**: 如果 `--list-sessions` 不可用，直接在启动 Probe 时记录完整路径

```python
def start_probe_with_transcript_tracking(task_id, initial_prompt, project_path):
    """
    启动 Probe 并记录 transcript 路径
    """
    # 启动 Probe
    probe_info = start_probe(task_id, initial_prompt, project_path, {})

    # 计算 project_hash（需要了解 Claude Code 的 hash 算法）
    # 或者通过其他方式获取

    # 构造 transcript 路径
    home = os.path.expanduser("~")
    project_hash = calculate_project_hash(project_path)  # 需要实现
    transcript_path = f"{home}/.claude/projects/{project_hash}/{task_id}.jsonl"

    probe_info["transcript_path"] = transcript_path
    return probe_info
```

#### 1.2.2 增量读取 Transcript

**策略**: 记录上次读取的位置（文件偏移量），只读取新增内容

```python
import os

def read_transcript_incremental(transcript_path, last_offset=0):
    """
    增量读取 transcript 文件

    Args:
        transcript_path: transcript 文件路径
        last_offset: 上次读取的文件偏移量（字节）

    Returns:
        dict: {
            "messages": [新消息列表],
            "new_offset": 新的文件偏移量,
            "file_size": 当前文件大小
        }
    """
    try:
        if not os.path.exists(transcript_path):
            return {
                "messages": [],
                "new_offset": 0,
                "file_size": 0
            }

        # 获取文件大小
        file_size = os.path.getsize(transcript_path)

        # 如果文件没有增长，返回空
        if file_size <= last_offset:
            return {
                "messages": [],
                "new_offset": last_offset,
                "file_size": file_size
            }

        # 读取新增内容
        messages = []
        with open(transcript_path, 'r', encoding='utf-8') as f:
            # 跳到上次读取的位置
            f.seek(last_offset)

            # 读取新增的行
            for line in f:
                line = line.strip()
                if line:
                    try:
                        message = json.loads(line)
                        messages.append(message)
                    except json.JSONDecodeError as e:
                        logging.warning(f"解析消息失败: {e}, line: {line[:100]}")

            # 记录新的偏移量
            new_offset = f.tell()

        return {
            "messages": messages,
            "new_offset": new_offset,
            "file_size": file_size
        }

    except Exception as e:
        logging.error(f"读取 transcript 失败: {e}")
        return {
            "messages": [],
            "new_offset": last_offset,
            "file_size": 0
        }
```

#### 1.2.3 分析 Transcript 内容

**实现位置**: `scripts/transcript_analyzer.py`

```python
from datetime import datetime, timedelta

def analyze_probe_status(messages, config):
    """
    分析 Probe 的执行状态

    Args:
        messages: transcript 消息列表
        config: 任务配置（包含 success_indicators, failure_indicators 等）

    Returns:
        dict: {
            "status": "running" | "idle" | "stuck" | "error" | "completed",
            "last_activity": 最后活动时间,
            "summary": 状态摘要,
            "issues": [问题列表],
            "progress": 进度估计（0-100）
        }
    """
    if not messages:
        return {
            "status": "unknown",
            "last_activity": None,
            "summary": "无法获取 Probe 状态",
            "issues": ["transcript 为空"],
            "progress": 0
        }

    # 获取最后一条消息
    last_message = messages[-1]
    last_activity = last_message.get("timestamp")

    # 计算距离最后活动的时间
    if last_activity:
        last_time = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
        idle_minutes = (datetime.now(last_time.tzinfo) - last_time).total_seconds() / 60
    else:
        idle_minutes = 0

    # 分析消息内容
    issues = []
    status = "running"

    # 检查是否有错误
    for msg in reversed(messages[-10:]):  # 检查最近 10 条消息
        role = msg.get("role")
        content = msg.get("content", "")

        # 检查工具调用失败
        if role == "tool_result":
            if msg.get("is_error"):
                issues.append({
                    "type": "tool_error",
                    "message": content[:200],
                    "timestamp": msg.get("timestamp")
                })

        # 检查失败指标
        for indicator in config.get("criteria", {}).get("failure_indicators", []):
            if indicator.lower() in content.lower():
                issues.append({
                    "type": "failure_indicator",
                    "indicator": indicator,
                    "message": content[:200]
                })

    # 判断状态
    if issues:
        status = "error"
    elif idle_minutes > 15:
        status = "stuck"  # 超过 15 分钟无活动
    elif last_message.get("role") == "assistant" and "stop_reason" in last_message:
        status = "idle"  # 等待用户输入
    else:
        status = "running"

    # 检查是否完成
    for msg in reversed(messages[-5:]):
        content = msg.get("content", "")
        for keyword in config.get("criteria", {}).get("completion_keywords", []):
            if keyword in content:
                status = "completed"
                break

    return {
        "status": status,
        "last_activity": last_activity,
        "summary": f"状态: {status}, 最后活动: {idle_minutes:.1f} 分钟前",
        "issues": issues,
        "progress": estimate_progress(messages, config)
    }

def estimate_progress(messages, config):
    """
    估计任务进度（简单实现）
    """
    # 基于消息数量和成功指标的简单估计
    # 实际实现可以更复杂
    total_messages = len(messages)

    # 检查成功指标出现次数
    success_count = 0
    success_indicators = config.get("criteria", {}).get("success_indicators", [])

    for msg in messages:
        content = msg.get("content", "")
        for indicator in success_indicators:
            if indicator in content:
                success_count += 1

    # 简单的进度估计
    if success_count >= len(success_indicators):
        return 100
    else:
        return min(90, (total_messages / 50) * 100)  # 假设 50 条消息约完成
```

---

### 1.3 执行状态判断与展示

#### 1.3.1 状态类型定义

```python
from enum import Enum

class ProbeStatus(Enum):
    """Probe 执行状态"""
    RUNNING = "running"      # 正在执行
    IDLE = "idle"            # 空闲（等待用户输入）
    STUCK = "stuck"          # 卡住（长时间无响应）
    ERROR = "error"          # 出错
    COMPLETED = "completed"  # 任务完成
    STOPPED = "stopped"      # 已停止
    UNKNOWN = "unknown"      # 未知状态
```

#### 1.3.2 状态判断逻辑

```python
def determine_probe_status(process_info, transcript_info, config):
    """
    综合判断 Probe 状态

    Args:
        process_info: 进程信息（来自 check_probe_process）
        transcript_info: transcript 分析结果（来自 analyze_probe_status）
        config: 任务配置

    Returns:
        ProbeStatus: 最终状态
    """
    # 1. 进程已死亡
    if not process_info["alive"]:
        return ProbeStatus.STOPPED

    # 2. 基于 transcript 分析
    transcript_status = transcript_info["status"]

    if transcript_status == "completed":
        return ProbeStatus.COMPLETED
    elif transcript_status == "error":
        return ProbeStatus.ERROR
    elif transcript_status == "stuck":
        return ProbeStatus.STUCK
    elif transcript_status == "idle":
        return ProbeStatus.IDLE
    elif transcript_status == "running":
        return ProbeStatus.RUNNING
    else:
        return ProbeStatus.UNKNOWN
```

#### 1.3.3 日志查看命令

**新增命令**: `/show-probe-log`

**文件位置**: `commands/show-probe-log.md`

```markdown
# /show-probe-log

查看 Probe 任务的执行日志

## 用法

```
/show-probe-log <task_id> [--lines=50] [--follow]
```

## 参数

- `task_id`: 任务 ID（必需）
- `--lines`: 显示最后 N 行（可选，默认 50）
- `--follow`: 实时跟踪日志（可选，类似 tail -f）

## 示例

```bash
# 查看最后 50 行日志
/show-probe-log 20260201_143000_probe

# 查看最后 100 行
/show-probe-log 20260201_143000_probe --lines=100

# 实时跟踪日志
/show-probe-log 20260201_143000_probe --follow
```

## 实现

调用 `scripts/show_probe_log.py`
```

**实现脚本**: `scripts/show_probe_log.py`

```python
import sys
import time
import json
from pathlib import Path

def show_probe_log(task_id, lines=50, follow=False):
    """
    显示 Probe 日志
    """
    # 1. 加载任务配置
    task_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    config_file = task_dir / "config.json"

    if not config_file.exists():
        print(f"错误: 任务 {task_id} 不存在")
        return 1

    with open(config_file, 'r') as f:
        config = json.load(f)

    # 2. 获取 transcript 路径
    transcript_path = config.get("probe", {}).get("transcript_path")

    if not transcript_path:
        # 尝试通过 session_id 查询
        session_id = config.get("probe", {}).get("session_id")
        transcript_path = get_transcript_path(session_id)

    if not transcript_path or not Path(transcript_path).exists():
        print(f"错误: 无法找到 transcript 文件")
        return 1

    # 3. 读取并格式化输出
    if follow:
        # 实时跟踪模式
        follow_transcript(transcript_path)
    else:
        # 显示最后 N 行
        show_last_n_messages(transcript_path, lines)

    return 0

def show_last_n_messages(transcript_path, n):
    """
    显示最后 N 条消息
    """
    messages = []

    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                msg = json.loads(line.strip())
                messages.append(msg)
            except:
                pass

    # 取最后 N 条
    recent_messages = messages[-n:]

    # 格式化输出
    for msg in recent_messages:
        print_message(msg)

def follow_transcript(transcript_path):
    """
    实时跟踪 transcript（类似 tail -f）
    """
    # 先显示现有内容
    show_last_n_messages(transcript_path, 20)

    print("\n--- 实时跟踪中（Ctrl+C 退出）---\n")

    # 记录当前文件位置
    with open(transcript_path, 'r', encoding='utf-8') as f:
        f.seek(0, 2)  # 跳到文件末尾

        try:
            while True:
                line = f.readline()
                if line:
                    try:
                        msg = json.loads(line.strip())
                        print_message(msg)
                    except:
                        pass
                else:
                    time.sleep(1)  # 等待新内容
        except KeyboardInterrupt:
            print("\n已停止跟踪")

def print_message(msg):
    """
    格式化打印消息
    """
    role = msg.get("role", "unknown")
    timestamp = msg.get("timestamp", "")
    content = msg.get("content", "")

    # 颜色代码（ANSI）
    colors = {
        "user": "\033[94m",      # 蓝色
        "assistant": "\033[92m",  # 绿色
        "tool_use": "\033[93m",   # 黄色
        "tool_result": "\033[95m" # 紫色
    }
    reset = "\033[0m"

    color = colors.get(role, "")

    print(f"{color}[{timestamp}] {role.upper()}{reset}")

    # 截断过长的内容
    if len(content) > 500:
        content = content[:500] + "..."

    print(content)
    print("-" * 80)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--lines", type=int, default=50)
    parser.add_argument("--follow", action="store_true")

    args = parser.parse_args()

    sys.exit(show_probe_log(args.task_id, args.lines, args.follow))
```

---

### 1.5 纠偏执行机制

> **核心设计**：
> - Archon 本身是一个 Claude Code CLI（父进程）
> - 纠偏时，Archon 使用 `claude --resume {session_id} -p "纠偏指令"` 向 Probe 注入指令
> - **不需要单独验证**：因为 Archon 会将 Probe 任务放在后台，待后台任务完成后，Archon 自动观察结果
> - 如果纠偏仍然失败，再发送系统通知

#### 1.5.1 Archon 监控脚本

**实现位置**: `scripts/archon_check.py`

这是 Archon 的核心监控脚本，由 cron 定时调用。

```python
#!/usr/bin/env python3
"""
Archon 监控脚本

由 cron 定时调用，检查 Probe 状态并执行纠偏
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

def main(task_id):
    """
    Archon 主入口

    Args:
        task_id: 要监控的任务 ID
    """
    setup_logging(task_id)

    logging.info("=" * 60)
    logging.info(f"Archon 开始检查任务: {task_id}")

    try:
        # 1. 加载任务配置
        config = load_task_config(task_id)

        if not config:
            logging.error(f"任务 {task_id} 配置不存在")
            return 1

        # 2. 检查任务状态
        status = config.get("state", {}).get("status")

        if status != "active":
            logging.info(f"任务状态为 {status}，跳过检查")
            return 0

        # 3. 检查 Probe 进程
        pid = config.get("probe", {}).get("pid")
        process_info = check_probe_process(pid)

        if not process_info["alive"]:
            logging.warning(f"Probe 进程 {pid} 已死亡")
            update_task_status(task_id, "stopped")
            # TODO: 发送系统通知
            return 0

        # 4. 分析 Probe 状态（读取 transcript）
        session_id = config.get("probe", {}).get("session_id")
        transcript_path = get_transcript_path(session_id)

        if transcript_path:
            analysis = analyze_probe_from_transcript(transcript_path, config)
        else:
            # 备选：从日志文件分析
            log_file = config.get("probe", {}).get("stdout_log")
            analysis = analyze_probe_from_log(log_file, config)

        logging.info(f"Probe 状态分析: {analysis['status']}")

        # 5. 根据状态决定是否纠偏
        if analysis["status"] == "error" and analysis.get("issues"):
            handle_probe_error(task_id, config, analysis)
        elif analysis["status"] == "stuck":
            handle_probe_stuck(task_id, config, analysis)
        elif analysis["status"] == "completed":
            handle_probe_completed(task_id, config)
        else:
            logging.info("Probe 运行正常，无需干预")

        # 6. 更新检查时间
        update_last_check(task_id)

        logging.info("Archon 检查完成")
        return 0

    except Exception as e:
        logging.error(f"Archon 检查失败: {e}", exc_info=True)
        return 1

def handle_probe_error(task_id, config, analysis):
    """
    处理 Probe 错误状态

    流程：
    1. 检查纠偏次数是否超限
    2. 如果未超限，让 Archon（Claude Code CLI）生成纠偏指令并执行
    3. 如果超限，发送系统通知
    """
    correction_count = config.get("correction", {}).get("current_count", 0)
    max_corrections = config.get("correction", {}).get("max_auto_corrections", 3)

    if correction_count >= max_corrections:
        logging.warning(f"纠偏次数已达上限 ({correction_count}/{max_corrections})")
        # TODO: 发送系统通知，请求人工介入
        send_system_notification(
            title=f"Probe 任务需要人工介入",
            message=f"任务 {task_id} 自动纠偏 {correction_count} 次失败，请手动处理"
        )
        return

    # 执行纠偏
    logging.info(f"开始执行纠偏 ({correction_count + 1}/{max_corrections})")
    execute_correction_via_archon(task_id, config, analysis)

def execute_correction_via_archon(task_id, config, analysis):
    """
    通过 Archon（Claude Code CLI）执行纠偏

    核心逻辑：
    1. Archon 根据 Probe 的问题分析，生成纠偏指令
    2. 使用 claude --resume {session_id} -p "纠偏指令" 注入
    3. Archon 会自动观察后台任务结果（不需要单独验证）
    """
    session_id = config.get("probe", {}).get("session_id")
    issues = analysis.get("issues", [])

    # 构造纠偏指令（由 Archon 智能生成）
    correction_prompt = construct_correction_prompt(issues, config)

    logging.info(f"纠偏指令: {correction_prompt[:200]}...")

    # 执行纠偏：使用 claude --resume 向 Probe 注入指令
    # 注意：这里 Archon 本身就是 Claude Code CLI
    # 它会将 Probe 任务放在后台，待完成后自动观察结果
    import subprocess

    try:
        result = subprocess.run(
            ["claude", "--resume", session_id, "-p", correction_prompt],
            capture_output=True,
            text=True,
            timeout=300  # 5 分钟超时
        )

        if result.returncode == 0:
            logging.info("纠偏指令已注入")
            # 更新纠偏计数
            increment_correction_count(task_id)
            # 记录纠偏历史
            record_correction(task_id, "Archon", correction_prompt, "已执行")
        else:
            logging.error(f"纠偏失败: {result.stderr}")
            # 纠偏失败，发送通知
            send_system_notification(
                title=f"Probe 纠偏失败",
                message=f"任务 {task_id} 纠偏执行失败: {result.stderr[:100]}"
            )

    except subprocess.TimeoutExpired:
        logging.error("纠偏执行超时")
    except Exception as e:
        logging.error(f"纠偏执行异常: {e}")

def construct_correction_prompt(issues, config):
    """
    构造纠偏指令

    这个函数生成给 Probe 的纠偏提示词
    Archon 会根据问题分析智能生成修复建议
    """
    prompt_parts = [
        "# Archon 纠偏指令",
        "",
        "检测到以下问题需要纠正：",
        ""
    ]

    for i, issue in enumerate(issues, 1):
        prompt_parts.append(f"## 问题 {i}: {issue.get('type')}")
        prompt_parts.append(f"**描述**: {issue.get('message')}")
        prompt_parts.append("")

    prompt_parts.extend([
        "## 请求",
        "",
        "请分析上述问题并尝试修复。",
        "修复后，请验证以下条件：",
    ])

    for indicator in config.get("criteria", {}).get("success_indicators", []):
        prompt_parts.append(f"- {indicator}")

    return "\n".join(prompt_parts)

def handle_probe_stuck(task_id, config, analysis):
    """
    处理 Probe 卡住状态
    """
    logging.warning(f"Probe 卡住，尝试唤醒")

    session_id = config.get("probe", {}).get("session_id")

    # 发送唤醒指令
    wake_prompt = "请继续执行任务。如果遇到问题，请说明当前状态和遇到的困难。"

    import subprocess
    subprocess.run(
        ["claude", "--resume", session_id, "-p", wake_prompt],
        capture_output=True,
        text=True,
        timeout=60
    )

def handle_probe_completed(task_id, config):
    """
    处理 Probe 完成状态
    """
    logging.info(f"任务 {task_id} 已完成")
    update_task_status(task_id, "completed")

    # 停止定时任务
    remove_archon_cron(task_id)

    # 发送完成通知
    send_system_notification(
        title=f"Probe 任务完成",
        message=f"任务 {task_id} 已成功完成"
    )

# 辅助函数

def setup_logging(task_id):
    """配置日志"""
    log_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    log_file = log_dir / "archon.log"

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_task_config(task_id):
    """加载任务配置"""
    config_file = Path.home() / ".claude" / "daemon-archon" / task_id / "config.json"

    if not config_file.exists():
        return None

    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_task_status(task_id, status):
    """更新任务状态"""
    status_file = Path.home() / ".claude" / "daemon-archon" / task_id / "status"
    with open(status_file, 'w') as f:
        f.write(status)

def update_last_check(task_id):
    """更新最后检查时间"""
    config_file = Path.home() / ".claude" / "daemon-archon" / task_id / "config.json"

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config["state"]["last_check"] = datetime.utcnow().isoformat() + "Z"

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def increment_correction_count(task_id):
    """增加纠偏计数"""
    config_file = Path.home() / ".claude" / "daemon-archon" / task_id / "config.json"

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config["correction"]["current_count"] = config.get("correction", {}).get("current_count", 0) + 1

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def record_correction(task_id, corrector, prompt, result):
    """记录纠偏历史"""
    corrections_file = Path.home() / ".claude" / "daemon-archon" / task_id / "corrections.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not corrections_file.exists():
        content = "# 纠偏历史\n\n"
    else:
        with open(corrections_file, 'r', encoding='utf-8') as f:
            content = f.read()

    content += f"""
## {timestamp} - {corrector}

**纠偏指令**:
```
{prompt[:500]}...
```

**结果**: {result}

---
"""

    with open(corrections_file, 'w', encoding='utf-8') as f:
        f.write(content)

def remove_archon_cron(task_id):
    """移除 Archon 定时任务"""
    import subprocess
    subprocess.run(
        f"crontab -l | grep -v 'archon_check.py {task_id}' | crontab -",
        shell=True
    )

def send_system_notification(title, message):
    """发送系统通知（Linux）"""
    import subprocess
    try:
        subprocess.run(
            ["notify-send", "-u", "critical", "-a", "Daemon Archon", title, message],
            timeout=5
        )
    except Exception as e:
        logging.warning(f"发送系统通知失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: archon_check.py <task_id>")
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
```

#### 1.5.2 纠偏流程图

```
Archon 定时检查
      │
      ▼
┌─────────────────┐
│ 加载任务配置     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 检查 Probe 进程  │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 存活?   │
    └────┬────┘
         │
    ┌────┴────┐
    No        Yes
    │         │
    ▼         ▼
┌───────┐  ┌─────────────────┐
│ 标记   │  │ 分析 Probe 状态  │
│ stopped│  │ (transcript/log)│
└───────┘  └────────┬────────┘
                    │
           ┌────────┴────────┐
           │ 状态判断         │
           └────────┬────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌───────┐     ┌───────────┐   ┌───────────┐
│ error │     │ stuck     │   │ completed │
└───┬───┘     └─────┬─────┘   └─────┬─────┘
    │               │               │
    ▼               ▼               ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│ 纠偏次数   │ │ 发送唤醒   │ │ 标记完成   │
│ 超限?     │ │ 指令       │ │ 停止定时   │
└─────┬─────┘ └───────────┘ │ 发送通知   │
      │                     └───────────┘
  ┌───┴───┐
  No      Yes
  │       │
  ▼       ▼
┌─────────┐ ┌─────────────┐
│ 执行纠偏 │ │ 发送通知     │
│ (Archon │ │ 请求人工介入 │
│ 生成指令)│ └─────────────┘
└─────────┘
```

#### 1.5.3 关键设计说明

**为什么不需要单独验证纠偏结果？**

1. **Archon 本身是 Claude Code CLI**：当 Archon 执行 `claude --resume {session_id} -p "纠偏指令"` 时，它会将 Probe 任务放在后台
2. **自动观察机制**：待后台任务完成后，Archon 会自动观察任务结果
3. **下次检查时验证**：在下一次定时检查时，Archon 会重新分析 Probe 状态，判断纠偏是否成功
4. **失败处理**：如果纠偏仍然失败（问题依然存在），会增加纠偏计数，超过阈值后发送系统通知

**纠偏指令的生成**

- Archon 根据 Probe 的 transcript/日志分析问题
- 智能生成纠偏指令（包含问题描述和修复建议）
- 通过 `claude --resume` 注入到 Probe 会话

---

## 二、Cron 执行引擎跨平台实现

### 2.1 平台检测

**实现位置**: `scripts/platform_detector.py`

```python
import platform
import subprocess
import shutil

class PlatformInfo:
    """平台信息"""
    def __init__(self):
        self.system = platform.system()  # Linux, Windows, Darwin
        self.version = platform.version()
        self.has_systemd = False
        self.has_cron = False
        self.has_task_scheduler = False

    def detect(self):
        """检测平台特性"""
        if self.system == "Linux":
            self.has_systemd = self._check_systemd()
            self.has_cron = self._check_cron()
        elif self.system == "Windows":
            self.has_task_scheduler = self._check_task_scheduler()
        elif self.system == "Darwin":
            # macOS (P2 优先级)
            pass

        return self

    def _check_systemd(self):
        """检查是否有 systemd"""
        try:
            result = subprocess.run(
                ["systemctl", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def _check_cron(self):
        """检查是否有 cron"""
        return shutil.which("crontab") is not None

    def _check_task_scheduler(self):
        """检查 Windows 任务计划程序"""
        return shutil.which("schtasks") is not None

    def get_recommended_scheduler(self):
        """获取推荐的调度器"""
        if self.system == "Linux":
            if self.has_cron:
                return "crontab"
            elif self.has_systemd:
                return "systemd"
            else:
                raise UnsupportedPlatformError("未找到可用的调度器")
        elif self.system == "Windows":
            if self.has_task_scheduler:
                return "task_scheduler"
            else:
                raise UnsupportedPlatformError("未找到任务计划程序")
        elif self.system == "Darwin":
            return "launchd"  # P2 优先级
        else:
            raise UnsupportedPlatformError(f"不支持的平台: {self.system}")

class UnsupportedPlatformError(Exception):
    pass
```

---

### 2.2 Linux 实现方案

#### 2.2.1 Crontab 实现（推荐）

**实现位置**: `scripts/cron_installer.py`

```python
import subprocess
import tempfile
import os

class CrontabInstaller:
    """Crontab 调度器安装器"""

    def __init__(self, check_interval_minutes=5):
        self.check_interval_minutes = check_interval_minutes
        self.archon_script = self._get_archon_script_path()

    def _get_archon_script_path(self):
        """获取 archon_main.py 的完整路径"""
        home = os.path.expanduser("~")
        return f"{home}/.claude/plugins/daemon-archon/scripts/archon_main.py"

    def install(self):
        """安装 crontab 定时任务"""
        try:
            # 1. 读取现有 crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                existing_crontab = result.stdout
            else:
                existing_crontab = ""

            # 2. 检查是否已存在
            if "daemon-archon" in existing_crontab:
                return {
                    "success": False,
                    "message": "Daemon Archon 定时任务已存在"
                }

            # 3. 构造新的 crontab 条目
            cron_entry = self._generate_cron_entry()

            # 4. 追加新条目
            new_crontab = existing_crontab.rstrip() + "\n\n"
            new_crontab += "# Daemon Archon - 自动任务调度\n"
            new_crontab += cron_entry + "\n"

            # 5. 写入 crontab
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(new_crontab)
                temp_file = f.name

            result = subprocess.run(
                ["crontab", temp_file],
                capture_output=True,
                text=True
            )

            os.unlink(temp_file)

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"安装失败: {result.stderr}"
                }

            # 6. 验证安装
            if self.verify():
                return {
                    "success": True,
                    "message": f"已安装 Daemon Archon 定时任务（每 {self.check_interval_minutes} 分钟执行）"
                }
            else:
                return {
                    "success": False,
                    "message": "安装后验证失败"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"安装失败: {e}"
            }

    def _generate_cron_entry(self):
        """生成 cron 条目"""
        # 每 N 分钟执行一次
        cron_schedule = f"*/{self.check_interval_minutes} * * * *"

        # Python 路径
        python_path = subprocess.run(
            ["which", "python3"],
            capture_output=True,
            text=True
        ).stdout.strip() or "python3"

        # 日志文件
        home = os.path.expanduser("~")
        log_file = f"{home}/.claude/daemon-archon/archon_main.log"

        # 构造命令
        command = f"{python_path} {self.archon_script} >> {log_file} 2>&1"

        return f"{cron_schedule} {command}"

    def uninstall(self):
        """卸载 crontab 定时任务"""
        try:
            # 1. 读取现有 crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": "未找到 crontab"
                }

            existing_crontab = result.stdout

            # 2. 移除 daemon-archon 相关行
            lines = existing_crontab.split('\n')
            new_lines = []
            skip_next = False

            for line in lines:
                if "Daemon Archon" in line:
                    skip_next = True
                    continue
                if skip_next and "archon_main.py" in line:
                    skip_next = False
                    continue
                new_lines.append(line)

            new_crontab = '\n'.join(new_lines)

            # 3. 写入新的 crontab
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(new_crontab)
                temp_file = f.name

            result = subprocess.run(
                ["crontab", temp_file],
                capture_output=True,
                text=True
            )

            os.unlink(temp_file)

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"卸载失败: {result.stderr}"
                }

            return {
                "success": True,
                "message": "已卸载 Daemon Archon 定时任务"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"卸载失败: {e}"
            }

    def verify(self):
        """验证安装"""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return "archon_main.py" in result.stdout

            return False
        except:
            return False
```

#### 2.2.2 Systemd Timer 实现（备选）

**实现位置**: `scripts/systemd_installer.py`

```python
import os
from pathlib import Path

class SystemdInstaller:
    """Systemd Timer 调度器安装器"""

    def __init__(self, check_interval_minutes=5):
        self.check_interval_minutes = check_interval_minutes
        self.service_name = "daemon-archon"
        self.user_systemd_dir = Path.home() / ".config" / "systemd" / "user"

    def install(self):
        """安装 systemd timer"""
        try:
            # 1. 创建目录
            self.user_systemd_dir.mkdir(parents=True, exist_ok=True)

            # 2. 创建 service 文件
            service_content = self._generate_service_file()
            service_file = self.user_systemd_dir / f"{self.service_name}.service"

            with open(service_file, 'w') as f:
                f.write(service_content)

            # 3. 创建 timer 文件
            timer_content = self._generate_timer_file()
            timer_file = self.user_systemd_dir / f"{self.service_name}.timer"

            with open(timer_file, 'w') as f:
                f.write(timer_content)

            # 4. 重新加载 systemd
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True
            )

            # 5. 启用并启动 timer
            subprocess.run(
                ["systemctl", "--user", "enable", f"{self.service_name}.timer"],
                check=True
            )

            subprocess.run(
                ["systemctl", "--user", "start", f"{self.service_name}.timer"],
                check=True
            )

            return {
                "success": True,
                "message": f"已安装 Daemon Archon systemd timer（每 {self.check_interval_minutes} 分钟执行）"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"安装失败: {e}"
            }

    def _generate_service_file(self):
        """生成 systemd service 文件"""
        home = os.path.expanduser("~")
        archon_script = f"{home}/.claude/plugins/daemon-archon/scripts/archon_main.py"
        python_path = subprocess.run(
            ["which", "python3"],
            capture_output=True,
            text=True
        ).stdout.strip() or "python3"

        return f"""[Unit]
Description=Daemon Archon - Claude Code Task Scheduler
After=network.target

[Service]
Type=oneshot
ExecStart={python_path} {archon_script}
WorkingDirectory={home}/.claude
StandardOutput=append:{home}/.claude/daemon-archon/archon_main.log
StandardError=append:{home}/.claude/daemon-archon/archon_main.log

[Install]
WantedBy=default.target
"""

    def _generate_timer_file(self):
        """生成 systemd timer 文件"""
        return f"""[Unit]
Description=Daemon Archon Timer
Requires={self.service_name}.service

[Timer]
OnBootSec=1min
OnUnitActiveSec={self.check_interval_minutes}min
AccuracySec=1s

[Install]
WantedBy=timers.target
"""

    def uninstall(self):
        """卸载 systemd timer"""
        try:
            # 1. 停止并禁用 timer
            subprocess.run(
                ["systemctl", "--user", "stop", f"{self.service_name}.timer"],
                capture_output=True
            )

            subprocess.run(
                ["systemctl", "--user", "disable", f"{self.service_name}.timer"],
                capture_output=True
            )

            # 2. 删除文件
            service_file = self.user_systemd_dir / f"{self.service_name}.service"
            timer_file = self.user_systemd_dir / f"{self.service_name}.timer"

            if service_file.exists():
                service_file.unlink()

            if timer_file.exists():
                timer_file.unlink()

            # 3. 重新加载 systemd
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True
            )

            return {
                "success": True,
                "message": "已卸载 Daemon Archon systemd timer"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"卸载失败: {e}"
            }
```

---

### 2.3 Windows 实现方案

**实现位置**: `scripts/task_scheduler_installer.py`

```python
import subprocess
import os

class TaskSchedulerInstaller:
    """Windows 任务计划程序安装器"""

    def __init__(self, check_interval_minutes=5):
        self.check_interval_minutes = check_interval_minutes
        self.task_name = "DaemonArchon"

    def install(self):
        """安装 Windows 计划任务"""
        try:
            # 1. 构造命令
            python_path = subprocess.run(
                ["where", "python"],
                capture_output=True,
                text=True
            ).stdout.strip().split('\n')[0]

            home = os.path.expanduser("~")
            archon_script = f"{home}\\.claude\\plugins\\daemon-archon\\scripts\\archon_main.py"

            # 2. 创建任务
            # 使用 XML 配置文件方式更可靠
            xml_content = self._generate_task_xml(python_path, archon_script)

            # 写入临时 XML 文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(xml_content)
                xml_file = f.name

            # 3. 导入任务
            result = subprocess.run(
                ["schtasks", "/create", "/tn", self.task_name, "/xml", xml_file, "/f"],
                capture_output=True,
                text=True
            )

            os.unlink(xml_file)

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"安装失败: {result.stderr}"
                }

            return {
                "success": True,
                "message": f"已安装 Daemon Archon 计划任务（每 {self.check_interval_minutes} 分钟执行）"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"安装失败: {e}"
            }

    def _generate_task_xml(self, python_path, archon_script):
        """生成任务计划 XML 配置"""
        home = os.path.expanduser("~")
        log_file = f"{home}\\.claude\\daemon-archon\\archon_main.log"

        return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Daemon Archon - Claude Code Task Scheduler</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT{self.check_interval_minutes}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>{archon_script}</Arguments>
      <WorkingDirectory>{home}\\.claude</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

    def uninstall(self):
        """卸载 Windows 计划任务"""
        try:
            result = subprocess.run(
                ["schtasks", "/delete", "/tn", self.task_name, "/f"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"卸载失败: {result.stderr}"
                }

            return {
                "success": True,
                "message": "已卸载 Daemon Archon 计划任务"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"卸载失败: {e}"
            }

    def verify(self):
        """验证安装"""
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", self.task_name],
                capture_output=True,
                text=True
            )

            return result.returncode == 0
        except:
            return False
```

---

### 2.4 统一安装接口

**实现位置**: `scripts/scheduler_manager.py`

```python
from platform_detector import PlatformInfo
from cron_installer import CrontabInstaller
from systemd_installer import SystemdInstaller
from task_scheduler_installer import TaskSchedulerInstaller

class SchedulerManager:
    """调度器管理器（统一接口）"""

    def __init__(self, check_interval_minutes=5):
        self.check_interval_minutes = check_interval_minutes
        self.platform_info = PlatformInfo().detect()
        self.installer = self._get_installer()

    def _get_installer(self):
        """获取对应平台的安装器"""
        scheduler_type = self.platform_info.get_recommended_scheduler()

        if scheduler_type == "crontab":
            return CrontabInstaller(self.check_interval_minutes)
        elif scheduler_type == "systemd":
            return SystemdInstaller(self.check_interval_minutes)
        elif scheduler_type == "task_scheduler":
            return TaskSchedulerInstaller(self.check_interval_minutes)
        else:
            raise UnsupportedPlatformError(f"不支持的调度器: {scheduler_type}")

    def install(self):
        """安装调度器"""
        return self.installer.install()

    def uninstall(self):
        """卸载调度器"""
        return self.installer.uninstall()

    def verify(self):
        """验证安装"""
        return self.installer.verify()

    def get_status(self):
        """获取调度器状态"""
        return {
            "platform": self.platform_info.system,
            "scheduler": self.platform_info.get_recommended_scheduler(),
            "installed": self.verify(),
            "interval_minutes": self.check_interval_minutes
        }
```

---

### 2.5 后台执行机制

**实现位置**: `scripts/archon_main.py`

```python
#!/usr/bin/env python3
"""
Archon 主入口

由系统定时器调用，执行任务检查和处理
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# 配置日志
def setup_logging():
    """配置日志输出"""
    log_dir = Path.home() / ".claude" / "daemon-archon"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "archon_main.log"

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            # 不输出到 stdout，避免干扰定时器
        ]
    )

def main():
    """主入口"""
    setup_logging()

    logging.info("=" * 80)
    logging.info("Archon 启动")

    try:
        # 1. 加载全局配置
        from state_store import load_global_config
        config = load_global_config()

        logging.info(f"加载全局配置: {config.get('version')}")

        # 2. 扫描所有任务
        from state_store import scan_tasks
        tasks = scan_tasks()

        logging.info(f"发现 {len(tasks)} 个任务")

        # 3. 处理每个任务
        for task in tasks:
            try:
                process_task(task, config)
            except Exception as e:
                logging.error(f"处理任务 {task['task_id']} 时出错: {e}", exc_info=True)
                # 发送通知
                from notification_service import send_notification
                send_notification(
                    title="Archon 错误",
                    message=f"处理任务 {task['task_id']} 时出错: {e}",
                    config=config
                )

        logging.info("Archon 完成")

    except Exception as e:
        logging.critical(f"Archon 主程序出错: {e}", exc_info=True)
        sys.exit(1)

def process_task(task, global_config):
    """处理单个任务"""
    from lock_manager import TaskLock

    task_id = task['task_id']
    task_mode = task['mode']

    logging.info(f"处理任务: {task_id} ({task_mode})")

    # 获取任务锁
    try:
        with TaskLock(task['dir'], timeout=30):
            if task_mode == "probe":
                from probe_manager import process_probe_task
                process_probe_task(task, global_config)
            elif task_mode == "cron":
                from cron_manager import process_cron_task
                process_cron_task(task, global_config)
            else:
                logging.warning(f"未知任务模式: {task_mode}")

    except TimeoutError:
        logging.warning(f"任务 {task_id} 锁超时，跳过")
    except Exception as e:
        logging.error(f"处理任务 {task_id} 失败: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    sys.exit(main() or 0)
```

---

## 三、系统通知机制实现

### 3.1 通知服务架构

**实现位置**: `scripts/notification_service.py`

```python
import logging
from enum import Enum

class NotificationMethod(Enum):
    """通知方式"""
    SYSTEM = "system"      # 系统通知
    WEBHOOK = "webhook"    # 自定义 Webhook
    SLACK = "slack"        # Slack
    EMAIL = "email"        # 邮件（P2 优先级）

class NotificationLevel(Enum):
    """通知级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

def send_notification(title, message, config, level=NotificationLevel.INFO, details=None):
    """
    发送通知（统一入口）

    Args:
        title: 通知标题
        message: 通知消息
        config: 全局配置
        level: 通知级别
        details: 详细信息（可选）

    Returns:
        bool: 是否发送成功
    """
    # 检查是否启用通知
    if not config.get("notification", {}).get("enabled", True):
        logging.info("通知已禁用，跳过发送")
        return False

    # 获取通知方式
    method = config.get("notification", {}).get("method", "system")

    try:
        if method == "system":
            return send_system_notification(title, message, level)
        elif method == "webhook":
            webhook_url = config.get("notification", {}).get("webhook_url")
            return send_webhook_notification(webhook_url, title, message, level, details)
        elif method == "slack":
            slack_webhook = config.get("notification", {}).get("slack_webhook")
            return send_slack_notification(slack_webhook, title, message, level, details)
        elif method == "email":
            # P2 优先级
            logging.warning("邮件通知暂未实现")
            return False
        else:
            logging.error(f"未知的通知方式: {method}")
            return False

    except Exception as e:
        logging.error(f"发送通知失败: {e}", exc_info=True)
        return False
```

---

### 3.2 系统通知实现

#### 3.2.1 Linux 系统通知

```python
import subprocess
import platform

def send_system_notification(title, message, level=NotificationLevel.INFO):
    """
    发送系统通知

    Args:
        title: 通知标题
        message: 通知消息
        level: 通知级别

    Returns:
        bool: 是否发送成功
    """
    system = platform.system()

    try:
        if system == "Linux":
            return _send_linux_notification(title, message, level)
        elif system == "Windows":
            return _send_windows_notification(title, message, level)
        elif system == "Darwin":
            return _send_macos_notification(title, message, level)
        else:
            logging.warning(f"不支持的平台: {system}")
            return False

    except Exception as e:
        logging.error(f"发送系统通知失败: {e}")
        return False

def _send_linux_notification(title, message, level):
    """Linux 系统通知（使用 notify-send）"""
    # 检查 notify-send 是否可用
    if not shutil.which("notify-send"):
        logging.warning("notify-send 不可用，请安装 libnotify")
        return False

    # 映射级别到 urgency
    urgency_map = {
        NotificationLevel.INFO: "normal",
        NotificationLevel.WARNING: "normal",
        NotificationLevel.ERROR: "critical",
        NotificationLevel.CRITICAL: "critical"
    }

    urgency = urgency_map.get(level, "normal")

    # 发送通知
    result = subprocess.run(
        [
            "notify-send",
            "-u", urgency,
            "-a", "Daemon Archon",
            "-i", "dialog-information",  # 图标
            title,
            message
        ],
        capture_output=True,
        timeout=5
    )

    return result.returncode == 0
```

#### 3.2.2 Windows 系统通知

```python
def _send_windows_notification(title, message, level):
    """Windows 系统通知（使用 win10toast）"""
    try:
        from win10toast import ToastNotifier
    except ImportError:
        logging.warning("win10toast 未安装，请运行: pip install win10toast")
        return False

    toaster = ToastNotifier()

    # 根据级别选择图标
    icon_path = None  # 可以指定自定义图标路径

    try:
        toaster.show_toast(
            title=f"Daemon Archon - {title}",
            msg=message,
            duration=10,  # 显示 10 秒
            icon_path=icon_path,
            threaded=True  # 非阻塞
        )
        return True
    except Exception as e:
        logging.error(f"Windows 通知失败: {e}")
        return False
```

#### 3.2.3 macOS 系统通知

```python
def _send_macos_notification(title, message, level):
    """macOS 系统通知（使用 osascript）"""
    script = f'''
    display notification "{message}" with title "Daemon Archon" subtitle "{title}"
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        timeout=5
    )

    return result.returncode == 0
```

---

### 3.3 Webhook 通知实现

```python
import requests
import json
from datetime import datetime

def send_webhook_notification(webhook_url, title, message, level, details=None):
    """
    发送 Webhook 通知

    Args:
        webhook_url: Webhook URL
        title: 通知标题
        message: 通知消息
        level: 通知级别
        details: 详细信息

    Returns:
        bool: 是否发送成功
    """
    if not webhook_url:
        logging.warning("未配置 webhook_url")
        return False

    # 构造 payload
    payload = {
        "title": title,
        "message": message,
        "level": level.value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "daemon-archon"
    }

    if details:
        payload["details"] = details

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        response.raise_for_status()

        logging.info(f"Webhook 通知已发送: {webhook_url}")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"Webhook 通知失败: {e}")
        return False
```

---

### 3.4 Slack 通知实现

```python
def send_slack_notification(slack_webhook, title, message, level, details=None):
    """
    发送 Slack 通知

    Args:
        slack_webhook: Slack Incoming Webhook URL
        title: 通知标题
        message: 通知消息
        level: 通知级别
        details: 详细信息

    Returns:
        bool: 是否发送成功
    """
    if not slack_webhook:
        logging.warning("未配置 slack_webhook")
        return False

    # 根据级别选择颜色和图标
    level_config = {
        NotificationLevel.INFO: {"color": "#36a64f", "emoji": ":information_source:"},
        NotificationLevel.WARNING: {"color": "#ff9900", "emoji": ":warning:"},
        NotificationLevel.ERROR: {"color": "#ff0000", "emoji": ":x:"},
        NotificationLevel.CRITICAL: {"color": "#990000", "emoji": ":rotating_light:"}
    }

    config = level_config.get(level, level_config[NotificationLevel.INFO])

    # 构造 Slack 消息
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{config['emoji']} {title}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        }
    ]

    # 添加详细信息
    if details:
        fields = []
        for key, value in details.items():
            fields.append({
                "type": "mrkdwn",
                "text": f"*{key}*: {value}"
            })

        if fields:
            blocks.append({
                "type": "section",
                "fields": fields
            })

    # 添加时间戳
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"<!date^{int(datetime.now().timestamp())}^{{date_short_pretty}} {{time}}|{datetime.now().isoformat()}>"
            }
        ]
    })

    payload = {
        "blocks": blocks,
        "attachments": [
            {
                "color": config["color"],
                "fallback": f"{title}: {message}"
            }
        ]
    }

    try:
        response = requests.post(
            slack_webhook,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        response.raise_for_status()

        logging.info("Slack 通知已发送")
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"Slack 通知失败: {e}")
        return False
```

---

### 3.5 通知触发条件

```python
def should_notify(event_type, task_config, global_config):
    """
    判断是否应该发送通知

    Args:
        event_type: 事件类型（error, correction, completion, etc.）
        task_config: 任务配置
        global_config: 全局配置

    Returns:
        bool: 是否应该发送通知
    """
    # 全局通知开关
    if not global_config.get("notification", {}).get("enabled", True):
        return False

    # 任务级别的通知配置
    task_notification = task_config.get("notification", {})

    if event_type == "error":
        return task_notification.get("notify_on_error", True)
    elif event_type == "completion":
        return task_notification.get("notify_on_success", False)
    elif event_type == "correction":
        # 自动纠偏失败时通知
        return True
    elif event_type == "stuck":
        # Probe 卡住时通知
        return True
    else:
        return False

def notify_probe_issue(task_id, task_name, issue_analysis, config):
    """
    通知 Probe 任务问题

    Args:
        task_id: 任务 ID
        task_name: 任务名称
        issue_analysis: 问题分析结果
        config: 全局配置
    """
    issues = issue_analysis.get("issues", [])

    if not issues:
        return

    # 构造消息
    title = f"Probe 任务问题: {task_name}"

    message_parts = [f"任务 {task_id} 检测到问题：\n"]

    for i, issue in enumerate(issues[:3], 1):  # 最多显示 3 个问题
        message_parts.append(f"{i}. {issue.get('type')}: {issue.get('message')[:100]}")

    if len(issues) > 3:
        message_parts.append(f"... 还有 {len(issues) - 3} 个问题")

    message = "\n".join(message_parts)

    # 详细信息
    details = {
        "任务 ID": task_id,
        "任务名称": task_name,
        "状态": issue_analysis.get("status"),
        "问题数量": len(issues)
    }

    # 发送通知
    send_notification(
        title=title,
        message=message,
        config=config,
        level=NotificationLevel.ERROR,
        details=details
    )

def notify_correction_failed(task_id, task_name, correction_count, config):
    """
    通知自动纠偏失败

    Args:
        task_id: 任务 ID
        task_name: 任务名称
        correction_count: 已尝试纠偏次数
        config: 全局配置
    """
    title = f"自动纠偏失败: {task_name}"

    message = f"""
任务 {task_id} 自动纠偏失败。

已尝试 {correction_count} 次自动纠偏，但问题仍未解决。
请手动介入处理。

使用命令: /intervene-probe {task_id}
"""

    details = {
        "任务 ID": task_id,
        "任务名称": task_name,
        "纠偏次数": correction_count
    }

    send_notification(
        title=title,
        message=message,
        config=config,
        level=NotificationLevel.CRITICAL,
        details=details
    )

def notify_task_completed(task_id, task_name, config):
    """
    通知任务完成

    Args:
        task_id: 任务 ID
        task_name: 任务名称
        config: 全局配置
    """
    title = f"任务完成: {task_name}"

    message = f"任务 {task_id} 已成功完成！"

    details = {
        "任务 ID": task_id,
        "任务名称": task_name
    }

    send_notification(
        title=title,
        message=message,
        config=config,
        level=NotificationLevel.INFO,
        details=details
    )
```

---

## 四、人工纠偏介入机制

### 4.1 人工纠偏触发场景

```markdown
## 场景 1: 收到系统通知后主动介入

用户收到通知: "Probe 任务遇到严重问题"
↓
用户执行: /check-task probe-001
↓
查看问题详情和 Archon 的分析
↓
决定是否介入

## 场景 2: 定期巡检时发现问题

用户执行: /list-tasks
↓
发现某个任务状态异常
↓
执行: /check-task <task_id>
↓
查看详情后决定介入

## 场景 3: Probe 自动纠偏失败

Archon 尝试自动纠偏 3 次失败
↓
发送通知并暂停自动纠偏
↓
等待用户介入
```

---

### 4.2 人工纠偏命令设计

**新增命令**: `/intervene-probe`

**文件位置**: `commands/intervene-probe.md`

```markdown
# /intervene-probe

人工介入 Probe 任务，进行手动纠偏

## 用法

```bash
# 交互式纠偏
/intervene-probe <task_id>

# 直接注入纠偏指令
/intervene-probe <task_id> --message="纠偏指令"

# 查看 Probe 日志
/intervene-probe <task_id> --show-log

# 暂停 Probe
/intervene-probe <task_id> --pause

# 终止 Probe
/intervene-probe <task_id> --stop
```

## 参数

- `task_id`: 任务 ID（必需）
- `--message`: 纠偏指令（可选）
- `--show-log`: 查看完整日志（可选）
- `--pause`: 暂停 Probe（可选）
- `--stop`: 终止 Probe（可选）

## 交互式纠偏流程

1. 显示 Probe 当前状态和问题摘要
2. 显示 Archon 的分析和建议
3. 提供操作选项：
   - [a] 注入纠偏指令
   - [b] 查看完整日志
   - [c] 暂停 Probe
   - [d] 终止 Probe
   - [e] 修改任务目标
   - [f] 取消

## 示例

```bash
# 交互式纠偏
/intervene-probe 20260201_143000_probe

# 直接注入指令
/intervene-probe 20260201_143000_probe --message="请先备份旧代码，然后再删除"

# 查看日志
/intervene-probe 20260201_143000_probe --show-log

# 暂停任务
/intervene-probe 20260201_143000_probe --pause
```

## 实现

调用 `scripts/intervene_probe.py`
```

---

### 4.3 人工纠偏实现

**实现位置**: `scripts/intervene_probe.py`

```python
import sys
import json
from pathlib import Path
from datetime import datetime

def intervene_probe(task_id, message=None, show_log=False, pause=False, stop=False):
    """
    人工介入 Probe 任务

    Args:
        task_id: 任务 ID
        message: 纠偏指令（可选）
        show_log: 是否查看日志
        pause: 是否暂停
        stop: 是否终止

    Returns:
        int: 退出码
    """
    # 1. 加载任务配置
    task_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    config_file = task_dir / "config.json"

    if not config_file.exists():
        print(f"错误: 任务 {task_id} 不存在")
        return 1

    with open(config_file, 'r') as f:
        config = json.load(f)

    # 2. 处理不同的操作
    if show_log:
        return show_probe_log_interactive(task_id, config)

    if pause:
        return pause_probe(task_id, config)

    if stop:
        return stop_probe_interactive(task_id, config)

    if message:
        # 直接注入纠偏指令
        return inject_correction(task_id, message, corrector="用户")

    # 3. 交互式纠偏
    return interactive_intervention(task_id, config)

def interactive_intervention(task_id, config):
    """
    交互式纠偏流程
    """
    print("=" * 80)
    print(f"人工介入: {config.get('name')}")
    print("=" * 80)
    print()

    # 1. 显示当前状态
    print("## 当前状态\n")
    status_info = get_probe_status(task_id, config)
    print_status_info(status_info)
    print()

    # 2. 显示问题分析
    if status_info.get("issues"):
        print("## 问题分析\n")
        for i, issue in enumerate(status_info["issues"], 1):
            print(f"{i}. {issue.get('type')}: {issue.get('message')}")
        print()

    # 3. 显示 Archon 建议
    if status_info.get("archon_suggestion"):
        print("## Archon 建议\n")
        print(status_info["archon_suggestion"])
        print()

    # 4. 显示操作选项
    print("## 操作选项\n")
    print("[a] 注入纠偏指令")
    print("[b] 查看完整日志")
    print("[c] 暂停 Probe")
    print("[d] 终止 Probe")
    print("[e] 修改任务目标")
    print("[f] 取消")
    print()

    # 5. 获取用户选择
    choice = input("请选择操作 [a-f]: ").strip().lower()

    if choice == 'a':
        return handle_inject_correction(task_id)
    elif choice == 'b':
        return show_probe_log_interactive(task_id, config)
    elif choice == 'c':
        return pause_probe(task_id, config)
    elif choice == 'd':
        return stop_probe_interactive(task_id, config)
    elif choice == 'e':
        return edit_task_destination(task_id)
    elif choice == 'f':
        print("已取消")
        return 0
    else:
        print("无效的选择")
        return 1

def handle_inject_correction(task_id):
    """
    处理注入纠偏指令
    """
    print("\n请输入纠偏指令（输入 END 结束）：\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    correction_prompt = "\n".join(lines)

    if not correction_prompt.strip():
        print("错误: 纠偏指令不能为空")
        return 1

    # 确认
    print("\n纠偏指令：")
    print("-" * 80)
    print(correction_prompt)
    print("-" * 80)

    confirm = input("\n确认注入？[y/N]: ").strip().lower()

    if confirm != 'y':
        print("已取消")
        return 0

    # 注入指令
    result = inject_correction(task_id, correction_prompt, corrector="用户")

    if result == 0:
        print("\n✓ 纠偏指令已注入")

        # 设置人工介入标志
        set_manual_intervention_flag(task_id, True)

        print("\n提示: Archon 已暂停自动纠偏，等待您的进一步操作")
        print(f"恢复自动纠偏: /resume-auto-correction {task_id}")

    return result

def inject_correction(task_id, correction_prompt, corrector):
    """
    注入纠偏指令

    Args:
        task_id: 任务 ID
        correction_prompt: 纠偏提示词
        corrector: 纠偏者（"Archon" 或 "用户"）

    Returns:
        int: 退出码
    """
    from correction_engine import execute_correction

    result = execute_correction(task_id, correction_prompt)

    if result["success"]:
        # 记录纠偏历史
        record_correction(
            task_id=task_id,
            corrector=corrector,
            prompt=correction_prompt,
            result="已注入，等待执行"
        )
        return 0
    else:
        print(f"错误: {result['message']}")
        return 1

def pause_probe(task_id, config):
    """
    暂停 Probe
    """
    from probe_manager import stop_probe

    pid = config.get("probe", {}).get("pid")

    if not pid:
        print("错误: 无法获取 Probe 进程 PID")
        return 1

    confirm = input(f"确认暂停 Probe 进程 (PID: {pid})？[y/N]: ").strip().lower()

    if confirm != 'y':
        print("已取消")
        return 0

    success = stop_probe(pid, graceful=True)

    if success:
        # 更新状态
        update_task_status(task_id, "paused")
        print("✓ Probe 已暂停")
        return 0
    else:
        print("✗ 暂停失败")
        return 1

def stop_probe_interactive(task_id, config):
    """
    终止 Probe（交互式）
    """
    from probe_manager import stop_probe

    pid = config.get("probe", {}).get("pid")

    if not pid:
        print("错误: 无法获取 Probe 进程 PID")
        return 1

    print(f"\n警告: 即将终止 Probe 进程 (PID: {pid})")
    print("这将停止任务执行，无法恢复。")

    confirm = input("\n确认终止？[y/N]: ").strip().lower()

    if confirm != 'y':
        print("已取消")
        return 0

    success = stop_probe(pid, graceful=True, timeout=10)

    if success:
        # 更新状态
        update_task_status(task_id, "stopped")
        print("✓ Probe 已终止")
        return 0
    else:
        print("✗ 终止失败")
        return 1

def set_manual_intervention_flag(task_id, enabled):
    """
    设置人工介入标志
    """
    task_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    config_file = task_dir / "config.json"

    with open(config_file, 'r') as f:
        config = json.load(f)

    config["manual_intervention"] = enabled
    config["manual_intervention_at"] = datetime.utcnow().isoformat() + "Z"

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def update_task_status(task_id, status):
    """
    更新任务状态
    """
    task_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    status_file = task_dir / "status"

    with open(status_file, 'w') as f:
        f.write(status)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--message", help="纠偏指令")
    parser.add_argument("--show-log", action="store_true", help="查看日志")
    parser.add_argument("--pause", action="store_true", help="暂停 Probe")
    parser.add_argument("--stop", action="store_true", help="终止 Probe")

    args = parser.parse_args()

    sys.exit(intervene_probe(
        task_id=args.task_id,
        message=args.message,
        show_log=args.show_log,
        pause=args.pause,
        stop=args.stop
    ))
```

---

### 4.4 恢复自动纠偏

**新增命令**: `/resume-auto-correction`

**文件位置**: `commands/resume-auto-correction.md`

```markdown
# /resume-auto-correction

恢复 Probe 任务的自动纠偏功能

## 用法

```bash
/resume-auto-correction <task_id>
```

## 说明

当用户手动介入 Probe 任务后，Archon 会暂停自动纠偏。
使用此命令可以恢复自动纠偏功能。

## 示例

```bash
/resume-auto-correction 20260201_143000_probe
```

## 实现

调用 `scripts/resume_auto_correction.py`
```

**实现位置**: `scripts/resume_auto_correction.py`

```python
import sys
import json
from pathlib import Path

def resume_auto_correction(task_id):
    """
    恢复自动纠偏

    Args:
        task_id: 任务 ID

    Returns:
        int: 退出码
    """
    # 加载任务配置
    task_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    config_file = task_dir / "config.json"

    if not config_file.exists():
        print(f"错误: 任务 {task_id} 不存在")
        return 1

    with open(config_file, 'r') as f:
        config = json.load(f)

    # 检查是否处于人工介入状态
    if not config.get("manual_intervention"):
        print("提示: 任务未处于人工介入状态")
        return 0

    # 清除人工介入标志
    config["manual_intervention"] = False
    config["manual_intervention_ended_at"] = datetime.utcnow().isoformat() + "Z"

    # 重置纠偏计数（可选）
    reset_count = input("是否重置纠偏计数？[y/N]: ").strip().lower()
    if reset_count == 'y':
        config["correction"]["current_count"] = 0

    # 保存配置
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✓ 已恢复任务 {task_id} 的自动纠偏功能")

    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: resume_auto_correction.py <task_id>")
        sys.exit(1)

    sys.exit(resume_auto_correction(sys.argv[1]))
```

---

## 五、其他落地实现问题

### 5.1 Session ID 管理

#### 5.1.1 Session ID 策略

**问题**: 如何确保 Probe 的 session_id 可控且唯一？

**解决方案**: 使用 task_id 作为 session_id

```python
def generate_task_id(mode):
    """
    生成任务 ID

    Args:
        mode: 任务模式（"probe" 或 "cron"）

    Returns:
        str: 任务 ID，格式: YYYYMMDD_HHMMSS_{mode}
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{mode}"

# 示例
task_id = generate_task_id("probe")  # "20260203_143000_probe"

# 启动 Probe 时使用 task_id 作为 session_id
subprocess.run([
    "claude",
    "-p", initial_prompt,
    "--session-id", task_id  # 使用 task_id 作为 session_id
])
```

**优点**:
- task_id 本身就是唯一的（基于时间戳）
- session_id 与任务目录名称一致，便于管理
- 可以直接通过 task_id 恢复会话

---

### 5.2 Transcript 文件路径定位

#### 5.2.1 方案 A: 使用 `claude --list-sessions`（推荐）

```python
def get_transcript_path_from_session_list(session_id):
    """
    通过 claude --list-sessions 获取 transcript 路径

    Args:
        session_id: 会话 ID

    Returns:
        str: transcript 文件路径，如果未找到返回 None
    """
    try:
        result = subprocess.run(
            ["claude", "--list-sessions", "--format=json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            logging.error(f"列出会话失败: {result.stderr}")
            return None

        sessions = json.loads(result.stdout)

        for session in sessions:
            if session.get("session_id") == session_id:
                return session.get("transcript_path")

        return None

    except Exception as e:
        logging.error(f"获取 transcript 路径失败: {e}")
        return None
```

#### 5.2.2 方案 B: 启动时记录路径（备选）

```python
def start_probe_and_record_transcript(task_id, initial_prompt, project_path):
    """
    启动 Probe 并记录 transcript 路径
    """
    # 1. 启动 Probe
    process = subprocess.Popen(
        ["claude", "-p", initial_prompt, "--session-id", task_id],
        cwd=project_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # 2. 等待一小段时间，让 Claude Code 创建 transcript 文件
    time.sleep(2)

    # 3. 通过 --list-sessions 获取 transcript 路径
    transcript_path = get_transcript_path_from_session_list(task_id)

    if not transcript_path:
        # 如果获取失败，使用默认路径规则
        # 注意：这需要了解 Claude Code 的 project_hash 计算方法
        logging.warning("无法获取 transcript 路径，使用默认规则")
        transcript_path = estimate_transcript_path(project_path, task_id)

    return {
        "pid": process.pid,
        "session_id": task_id,
        "transcript_path": transcript_path
    }

def estimate_transcript_path(project_path, session_id):
    """
    估算 transcript 路径（需要了解 Claude Code 的 hash 算法）

    这是一个备选方案，实际实现需要根据 Claude Code 的源码确定
    """
    import hashlib

    # 假设的 hash 算法（需要验证）
    project_hash = hashlib.sha256(project_path.encode()).hexdigest()[:16]

    home = os.path.expanduser("~")
    return f"{home}/.claude/projects/{project_hash}/{session_id}.jsonl"
```

#### 5.2.3 方案 C: 在 config.json 中持久化路径

```python
def save_probe_config(task_id, probe_info, initial_prompt, project_path):
    """
    保存 Probe 配置，包含 transcript 路径
    """
    config = {
        "task_id": task_id,
        "mode": "probe",
        "name": "Probe 任务",
        "project_path": project_path,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "probe": {
            "session_id": probe_info["session_id"],
            "pid": probe_info["pid"],
            "transcript_path": probe_info["transcript_path"],  # 持久化路径
            "initial_prompt": initial_prompt
        },
        # ... 其他配置
    }

    task_dir = Path.home() / ".claude" / "daemon-archon" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    config_file = task_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
```

---

### 5.3 并发安全性

#### 5.3.1 任务级锁实现

**实现位置**: `scripts/lock_manager.py`

```python
import fcntl
import os
import time
import psutil
from pathlib import Path

class TaskLock:
    """任务级锁，防止同一任务被并发处理"""

    def __init__(self, task_dir, timeout=30):
        """
        Args:
            task_dir: 任务目录路径
            timeout: 获取锁的超时时间（秒）
        """
        self.task_dir = Path(task_dir)
        self.lock_file = self.task_dir / "task.lock"
        self.timeout = timeout
        self.fd = None

    def acquire(self):
        """
        获取锁

        Returns:
            bool: 是否成功获取锁

        Raises:
            TimeoutError: 超时未能获取锁
        """
        start_time = time.time()

        while True:
            try:
                # 尝试获取锁
                self.fd = open(self.lock_file, 'w')
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                # 写入 PID 和时间戳
                self.fd.write(f"{os.getpid()}:{time.time()}\n")
                self.fd.flush()

                return True

            except IOError:
                # 锁已被占用，检查是否为僵尸锁
                if self._is_stale_lock():
                    # 清理僵尸锁
                    self._clean_stale_lock()
                    continue

                # 检查超时
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"无法获取任务锁: {self.lock_file}")

                # 等待后重试
                time.sleep(1)

    def release(self):
        """释放锁"""
        if self.fd:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
                self.lock_file.unlink(missing_ok=True)
            except Exception as e:
                logging.error(f"释放锁失败: {e}")

    def _is_stale_lock(self):
        """
        检查是否为僵尸锁

        僵尸锁的判断标准：
        1. 锁文件存在超过 30 分钟
        2. 持有锁的进程已不存在
        """
        if not self.lock_file.exists():
            return False

        try:
            with open(self.lock_file, 'r') as f:
                content = f.read().strip()

            if not content:
                return True

            pid_str, timestamp_str = content.split(':')
            pid = int(pid_str)
            timestamp = float(timestamp_str)

            # 检查时间
            if time.time() - timestamp > 1800:  # 30 分钟
                return True

            # 检查进程是否存在
            if not psutil.pid_exists(pid):
                return True

            return False

        except Exception as e:
            logging.warning(f"检查僵尸锁失败: {e}")
            return False

    def _clean_stale_lock(self):
        """清理僵尸锁"""
        try:
            self.lock_file.unlink(missing_ok=True)
            logging.info(f"清理僵尸锁: {self.lock_file}")
        except Exception as e:
            logging.error(f"清理僵尸锁失败: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
        return False
```

#### 5.3.2 使用示例

```python
from lock_manager import TaskLock

def process_task(task):
    """处理任务（带锁保护）"""
    task_dir = task['dir']

    try:
        with TaskLock(task_dir, timeout=30):
            # 处理任务
            if task['mode'] == 'probe':
                process_probe_task(task)
            elif task['mode'] == 'cron':
                process_cron_task(task)

    except TimeoutError:
        logging.warning(f"任务 {task['task_id']} 锁超时，跳过")
    except Exception as e:
        logging.error(f"处理任务失败: {e}")
        raise
```

---

### 5.4 错误恢复机制

#### 5.4.1 Archon 主程序错误处理

```python
def main():
    """
    Archon 主入口（带完整错误处理）
    """
    setup_logging()

    logging.info("=" * 80)
    logging.info("Archon 启动")

    try:
        # 1. 清理僵尸锁
        clean_all_stale_locks()

        # 2. 加载全局配置
        config = load_global_config()

        # 3. 扫描所有任务
        tasks = scan_tasks()

        logging.info(f"发现 {len(tasks)} 个任务")

        # 4. 处理每个任务
        for task in tasks:
            try:
                process_task(task, config)
            except Exception as e:
                # 单个任务出错不影响其他任务
                logging.error(f"处理任务 {task['task_id']} 时出错: {e}", exc_info=True)

                # 发送通知
                send_notification(
                    title="Archon 错误",
                    message=f"处理任务 {task['task_id']} 时出错: {e}",
                    config=config,
                    level=NotificationLevel.ERROR
                )

        logging.info("Archon 完成")
        return 0

    except Exception as e:
        # 全局错误
        logging.critical(f"Archon 主程序出错: {e}", exc_info=True)

        # 尝试发送通知
        try:
            config = load_global_config()
            send_notification(
                title="Archon 严重错误",
                message=f"Archon 主程序出错: {e}",
                config=config,
                level=NotificationLevel.CRITICAL
            )
        except:
            pass

        return 1

def clean_all_stale_locks():
    """清理所有僵尸锁"""
    archon_dir = Path.home() / ".claude" / "daemon-archon"

    if not archon_dir.exists():
        return

    for task_dir in archon_dir.iterdir():
        if not task_dir.is_dir():
            continue

        lock_file = task_dir / "task.lock"

        if lock_file.exists():
            try:
                with open(lock_file, 'r') as f:
                    content = f.read().strip()

                if not content:
                    lock_file.unlink()
                    continue

                pid_str, timestamp_str = content.split(':')
                pid = int(pid_str)
                timestamp = float(timestamp_str)

                # 检查是否为僵尸锁
                if time.time() - timestamp > 1800 or not psutil.pid_exists(pid):
                    lock_file.unlink()
                    logging.info(f"清理僵尸锁: {lock_file}")

            except Exception as e:
                logging.warning(f"清理锁文件 {lock_file} 失败: {e}")
```

#### 5.4.2 任务级错误恢复

```python
def process_probe_task(task, config):
    """
    处理 Probe 任务（带错误恢复）
    """
    task_id = task['task_id']

    try:
        # 1. 检查 Probe 进程是否存活
        pid = task['config'].get('probe', {}).get('pid')

        if not pid:
            logging.error(f"任务 {task_id} 缺少 PID")
            return

        process_info = check_probe_process(pid)

        if not process_info['alive']:
            # Probe 进程已死亡
            logging.warning(f"Probe 进程 {pid} 已死亡")

            # 发送通知
            send_notification(
                title=f"Probe 进程异常退出",
                message=f"任务 {task_id} 的 Probe 进程已退出",
                config=config,
                level=NotificationLevel.ERROR
            )

            # 更新任务状态
            update_task_status(task_id, "stopped")
            return

        # 2. 读取 transcript
        transcript_path = task['config'].get('probe', {}).get('transcript_path')

        if not transcript_path or not Path(transcript_path).exists():
            logging.error(f"任务 {task_id} 的 transcript 文件不存在")
            return

        # 3. 分析状态
        # ... (后续处理)

    except Exception as e:
        logging.error(f"处理 Probe 任务 {task_id} 失败: {e}", exc_info=True)
        raise
```

---

### 5.5 Claude Code CLI 兼容性

#### 5.5.1 版本检测

**实现位置**: `scripts/cli_validator.py`

```python
import subprocess
import re

class CLIValidator:
    """Claude CLI 兼容性验证器"""

    def __init__(self):
        self.version = None
        self.features = {}

    def validate(self):
        """
        验证 Claude CLI 是否满足要求

        Returns:
            dict: {
                "valid": bool,
                "version": str,
                "missing_features": [str],
                "warnings": [str]
            }
        """
        result = {
            "valid": True,
            "version": None,
            "missing_features": [],
            "warnings": []
        }

        # 1. 检查 Claude CLI 是否可用
        if not shutil.which("claude"):
            result["valid"] = False
            result["warnings"].append("未找到 claude 命令")
            return result

        # 2. 检测版本
        try:
            version_result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if version_result.returncode == 0:
                result["version"] = version_result.stdout.strip()
            else:
                result["warnings"].append("无法获取 Claude CLI 版本")

        except Exception as e:
            result["warnings"].append(f"检测版本失败: {e}")

        # 3. 检查必需功能
        required_features = [
            "--session-id",  # 指定 session ID
            "--resume",      # 恢复会话
        ]

        optional_features = [
            "--list-sessions",  # 列出会话
            "--format=json",    # JSON 输出格式
        ]

        try:
            help_result = subprocess.run(
                ["claude", "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )

            help_text = help_result.stdout

            # 检查必需功能
            for feature in required_features:
                if feature not in help_text:
                    result["valid"] = False
                    result["missing_features"].append(feature)

            # 检查可选功能
            for feature in optional_features:
                if feature not in help_text:
                    result["warnings"].append(f"可选功能不可用: {feature}")

        except Exception as e:
            result["valid"] = False
            result["warnings"].append(f"检查功能失败: {e}")

        return result

    def get_version_info(self):
        """获取版本信息"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return result.stdout.strip()

            return None

        except Exception as e:
            logging.error(f"获取版本信息失败: {e}")
            return None
```

#### 5.5.2 初始化检查

```python
def check_prerequisites():
    """
    检查前置条件

    Returns:
        dict: {
            "valid": bool,
            "issues": [str]
        }
    """
    issues = []

    # 1. 检查 Claude CLI
    validator = CLIValidator()
    cli_result = validator.validate()

    if not cli_result["valid"]:
        issues.append("Claude CLI 不满足要求")
        issues.extend(cli_result["missing_features"])

    # 2. 检查 Python 版本
    import sys
    if sys.version_info < (3, 7):
        issues.append("Python 版本过低，需要 3.7+")

    # 3. 检查必需的 Python 包
    required_packages = ["psutil", "requests"]

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            issues.append(f"缺少 Python 包: {package}")

    # 4. 检查平台支持
    platform_info = PlatformInfo().detect()

    try:
        scheduler = platform_info.get_recommended_scheduler()
    except UnsupportedPlatformError as e:
        issues.append(str(e))

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }
```

---

### 5.6 依赖管理

#### 5.6.1 Python 依赖

**文件位置**: `requirements.txt`

```txt
# Daemon Archon 依赖

# 进程管理
psutil>=5.8.0

# HTTP 请求（Webhook/Slack 通知）
requests>=2.26.0

# Windows 系统通知（仅 Windows）
win10toast>=0.9; sys_platform == 'win32'
```

#### 5.6.2 系统依赖

**Linux**:
```bash
# 系统通知
sudo apt-get install libnotify-bin  # Debian/Ubuntu
sudo yum install libnotify           # RHEL/CentOS

# Cron（通常已预装）
sudo apt-get install cron
```

**Windows**:
```powershell
# 任务计划程序（系统自带）
# 无需额外安装

# Python 包
pip install win10toast
```

---

## 六、总结与建议

### 6.1 需要立即补充到 dev_design.md 的内容

1. **Probe 监控机制**（第一章）
   - 进程管理（启动、检测、终止）
   - Transcript 读取与分析
   - 状态判断逻辑
   - 日志查看命令 `/show-probe-log`
   - 纠偏执行机制

2. **Cron 执行引擎**（第二章）
   - 平台检测
   - Linux 实现（Crontab/Systemd）
   - Windows 实现（Task Scheduler）
   - 统一安装接口
   - 后台执行机制

3. **系统通知**（第三章）
   - 通知服务架构
   - 系统通知（Linux/Windows/macOS）
   - Webhook 通知
   - Slack 通知
   - 通知触发条件

4. **人工纠偏**（第四章）
   - 触发场景
   - `/intervene-probe` 命令
   - 交互式纠偏流程
   - `/resume-auto-correction` 命令

5. **其他实现问题**（第五章）
   - Session ID 管理
   - Transcript 路径定位
   - 并发安全（任务级锁）
   - 错误恢复机制
   - CLI 兼容性检查
   - 依赖管理

---

### 6.2 新增命令清单

| 命令 | 功能 | 优先级 |
|------|------|--------|
| `/show-probe-log` | 查看 Probe 日志 | P0 |
| `/intervene-probe` | 人工介入纠偏 | P0 |
| `/resume-auto-correction` | 恢复自动纠偏 | P0 |

---

### 6.3 新增脚本清单

| 脚本 | 功能 | 优先级 |
|------|------|--------|
| `platform_detector.py` | 平台检测 | P0 |
| `cron_installer.py` | Crontab 安装器 | P0 |
| `systemd_installer.py` | Systemd 安装器 | P1 |
| `task_scheduler_installer.py` | Windows 任务计划程序安装器 | P0 |
| `scheduler_manager.py` | 调度器管理器（统一接口） | P0 |
| `lock_manager.py` | 任务级锁管理 | P0 |
| `cli_validator.py` | Claude CLI 兼容性验证 | P0 |
| `show_probe_log.py` | 显示 Probe 日志 | P0 |
| `intervene_probe.py` | 人工介入纠偏 | P0 |
| `resume_auto_correction.py` | 恢复自动纠偏 | P0 |

---

### 6.4 实现优先级建议

**P0（必须实现）**:
1. Probe 进程管理
2. Transcript 读取与分析
3. Crontab 安装器（Linux）
4. Task Scheduler 安装器（Windows）
5. 系统通知（Linux/Windows）
6. 任务级锁
7. 人工纠偏命令

**P1（重要但可延后）**:
1. Systemd Timer 安装器
2. Webhook 通知
3. Slack 通知
4. CLI 兼容性检查
5. 僵尸锁清理

**P2（可选功能）**:
1. macOS 支持
2. 邮件通知
3. Web 界面

---

### 6.5 开发流程建议

1. **Phase 1: 基础框架**
   - 实现 `platform_detector.py`
   - 实现 `lock_manager.py`
   - 实现 `cli_validator.py`

2. **Phase 2: Probe 监控**
   - 实现 `probe_manager.py`（进程管理）
   - 实现 `transcript_analyzer.py`
   - 实现 `show_probe_log.py`

3. **Phase 3: Cron 执行引擎**
   - 实现 `cron_installer.py`
   - 实现 `task_scheduler_installer.py`
   - 实现 `scheduler_manager.py`

4. **Phase 4: 通知系统**
   - 实现 `notification_service.py`
   - 实现系统通知（Linux/Windows）

5. **Phase 5: 人工纠偏**
   - 实现 `intervene_probe.py`
   - 实现 `resume_auto_correction.py`

6. **Phase 6: 集成测试**
   - 端到端测试
   - 跨平台测试
   - 错误恢复测试

---

## 附录：关键技术决策

### A.1 为什么使用任务级锁而非插件级锁？

**理由**:
- 不同任务之间应该可以并行检查，互不阻塞
- 只需要防止**同一个任务**被并发处理
- 任务级锁更细粒度，更灵活

### A.2 为什么使用 task_id 作为 session_id？

**理由**:
- task_id 本身就是唯一的（基于时间戳）
- session_id 与任务目录名称一致，便于管理
- 可以直接通过 task_id 恢复会话

### A.3 为什么优先使用 Crontab 而非 Systemd？

**理由**:
- Crontab 更通用，几乎所有 Linux 发行版都支持
- 无需 root 权限
- 配置更简单
- Systemd 作为备选方案，提供更强大的功能

### A.4 为什么需要僵尸锁清理机制？

**理由**:
- Archon 可能因为异常退出而未释放锁
- 系统重启后锁文件可能残留
- 僵尸锁会阻止任务正常处理

### A.5 为什么人工介入后暂停自动纠偏？

**理由**:
- 避免 Archon 和用户同时操作造成冲突
- 用户介入通常意味着问题较复杂，需要人工判断
- 用户可以选择恢复自动纠偏

---

**文档完成日期**: 2026-02-03

**下一步行动**: 将本文档的内容整合到 `dev_design.md`，并开始实现 Phase 1 的基础框架。

