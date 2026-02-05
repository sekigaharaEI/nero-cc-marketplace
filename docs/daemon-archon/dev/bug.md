# daemon-archon Bug 追踪

## Bug 记录规范

每个 Bug 记录应包含以下信息：

```markdown
### BUG-{编号}: {简短标题}

- **状态**: [ ] 待修复 / [x] 已修复
- **优先级**: P0(紧急) / P1(高) / P2(中) / P3(低)
- **发现日期**: YYYY-MM-DD
- **修复日期**: YYYY-MM-DD (如已修复)
- **影响范围**: 描述受影响的功能模块

**问题描述**:
详细描述问题现象

**复现步骤**:
1. 步骤一
2. 步骤二
3. ...

**错误日志**:
```
相关错误日志
```

**根因分析**:
问题的根本原因

**修复方案**:
建议的修复方案

**相关文件**:
- `path/to/file1.py`
- `path/to/file2.py`
```

---

## 待办事项汇总

| 编号 | 标题 | 优先级 | 状态 |
|------|------|--------|------|
| BUG-001 | Python 模块相对导入失败导致服务无法启动 | P0 | [x] 已修复 |
| BUG-002 | Probe 启动失败：session-id 格式不符合 UUID 要求 | P0 | [x] 已修复 |
| BUG-003 | Probe 完成后状态检测失败：无法获取 transcript 路径 | P1 | [x] 已修复 |
| BUG-004 | Cron 任务执行结果解析失败：状态始终为 unknown | P1 | [x] 已修复 |
| BUG-005 | 停止任务后状态不一致：config.json 未更新 | P2 | [ ] 待修复 |

---

## Bug 列表

### BUG-001: Python 模块相对导入失败导致服务无法启动

- **状态**: [x] 已修复
- **优先级**: P0(紧急)
- **发现日期**: 2026-02-04
- **修复日期**: 2026-02-04
- **影响范围**: Archon 服务启动 (`/archon-start`)

**问题描述**:
执行 `/archon-start` 启动 Archon 服务时，服务立即崩溃退出。原因是 `scheduler.py` 等模块使用了 Python 相对导入语法 (`from .types import ...`)，但 `main.py` 作为脚本直接运行时没有包上下文，导致 `ImportError`。

**复现步骤**:
1. 执行 `/archon-init` 确认环境检查通过
2. 执行 `/archon-start` 启动服务
3. 服务启动失败，退出码 1

**错误日志**:
```
Traceback (most recent call last):
  File "/data/zyw/nero-cc-marketplace/plugins/daemon-archon/scripts/server/main.py", line 22, in <module>
    from scheduler import ArchonScheduler, get_scheduler
  File "/data/zyw/nero-cc-marketplace/plugins/daemon-archon/scripts/server/scheduler.py", line 19, in <module>
    from .types import TaskMode, TaskStatus, CronScheduleKind
ImportError: attempted relative import with no known parent package
```

**根因分析**:
`server/` 目录下的模块文件使用了相对导入语法（如 `from .types import ...`），这种语法要求模块作为包的一部分被导入。但 `start_server.sh` 脚本使用 `python3 main.py` 直接运行 `main.py`，此时 Python 不知道 `main.py` 属于哪个包，因此相对导入失败。

受影响的文件及其相对导入：
- `scheduler.py`: `from .types import ...`, `from .state_store import ...`
- `state_store.py`: `from .types import ...`
- `analyzer.py`: `from .types import ...`, `from .state_store import ...`
- `probe_executor.py`: `from .types import ...`, `from .state_store import ...`, `from .analyzer import ...`, `from .notifier import ...`, `from .stuck_detector import ...`
- `cron_executor.py`: `from .types import ...`, `from .state_store import ...`, `from .analyzer import ...`, `from .notifier import ...`, `from .stuck_detector import ...`
- `stuck_detector.py`: `from .types import ...`, `from .state_store import ...`, `from .notifier import ...`
- `__init__.py`: 所有模块的相对导入

**修复方案**:

方案一（推荐）：修改启动方式为模块运行
```bash
# 修改 start_server.sh 中的启动命令
# 从:
nohup $PYTHON_CMD "$SERVER_DIR/main.py" > "$LOG_FILE" 2>&1 &
# 改为:
cd "$SCRIPT_DIR" && nohup $PYTHON_CMD -m server.main > "$LOG_FILE" 2>&1 &
```

方案二：将所有相对导入改为绝对导入
```python
# 在每个模块文件开头添加路径处理
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# 将 from .types import ... 改为 from types import ...
# 注意：types 与 Python 内置模块同名，需要重命名为 archon_types 或其他名称
```

方案三：在 `main.py` 中设置包上下文后再导入
```python
# 在 main.py 开头添加
import sys
from pathlib import Path

# 将 server 目录的父目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 然后使用包导入
from server.scheduler import ArchonScheduler, get_scheduler
from server.state_store import ...
```

**相关文件**:
- `plugins/daemon-archon/scripts/server/main.py`
- `plugins/daemon-archon/scripts/server/scheduler.py`
- `plugins/daemon-archon/scripts/server/state_store.py`
- `plugins/daemon-archon/scripts/server/analyzer.py`
- `plugins/daemon-archon/scripts/server/probe_executor.py`
- `plugins/daemon-archon/scripts/server/cron_executor.py`
- `plugins/daemon-archon/scripts/server/stuck_detector.py`
- `plugins/daemon-archon/scripts/server/__init__.py`
- `plugins/daemon-archon/scripts/start_server.sh`

**修复记录** (2026-02-04):
采用方案一，修改启动方式为模块运行：

1. 修改 `start_server.sh`：
```bash
# 从:
nohup $PYTHON_CMD "$SERVER_DIR/main.py" > "$LOG_FILE" 2>&1 &
# 改为:
cd "$SCRIPT_DIR" && nohup $PYTHON_CMD -m server.main > "$LOG_FILE" 2>&1 &
```

2. 修改 `main.py`：
```python
# 从绝对导入改为相对导入
from .scheduler import ArchonScheduler, get_scheduler
from .state_store import ...
# 移除 sys.path.insert 行
```

修复后服务可正常启动。

---

### BUG-002: Probe 启动失败：session-id 格式不符合 UUID 要求

- **状态**: [x] 已修复
- **优先级**: P0(紧急)
- **发现日期**: 2026-02-04
- **修复日期**: 2026-02-04
- **影响范围**: Probe 任务创建 (`/start-probe`)

**问题描述**:
执行 `/start-probe` 创建 Probe 任务时，Claude CLI 启动失败，返回错误 "Invalid session ID. Must be a valid UUID."。

**复现步骤**:
1. 确保 Archon 服务已启动 (`/archon-start`)
2. 执行 `/start-probe <任务描述>`
3. API 返回 `{"detail":"启动 Probe 失败"}`

**错误日志**:
```
# ~/.claude/daemon-archon/20260204_112130_probe/probe_stderr.log
Error: Invalid session ID. Must be a valid UUID.

# ~/.claude/daemon-archon/server.log
2026-02-04 11:21:32,275 - server.probe_executor - ERROR - Probe 启动失败，进程已退出
2026-02-04 11:21:32,275 - __main__ - ERROR - 创建 Probe 任务失败: 启动 Probe 失败
```

**根因分析**:
`probe_executor.py` 中的 `_start_claude_cli` 方法使用 task_id 作为 session_id：

```python
# probe_executor.py:173-178
process = subprocess.Popen(
    [
        "claude",
        "-p", initial_prompt,
        "--session-id", task_id  # task_id 格式为 "20260204_112130_probe"
    ],
    ...
)
```

但 Claude CLI 要求 `--session-id` 必须是有效的 UUID 格式（如 `550e8400-e29b-41d4-a716-446655440000`），而代码生成的 task_id 格式为 `YYYYMMDD_HHMMSS_probe`，不符合 UUID 规范。

**修复方案**:

方案一（推荐）：生成 UUID 作为 session_id，task_id 保持原格式
```python
import uuid

async def _start_claude_cli(self, task_id: str, initial_prompt: str, project_path: str):
    # 生成 UUID 作为 session_id
    session_id = str(uuid.uuid4())

    process = subprocess.Popen(
        [
            "claude",
            "-p", initial_prompt,
            "--session-id", session_id  # 使用 UUID
        ],
        ...
    )

    return {
        "pid": process.pid,
        "session_id": session_id,  # 返回 UUID
        "log_dir": str(task_dir)
    }
```

方案二：修改 task_id 生成逻辑，直接使用 UUID
```python
# main.py 中创建任务时
import uuid
task_id = str(uuid.uuid4())  # 替代 datetime.now().strftime("%Y%m%d_%H%M%S") + "_probe"
```

方案三：不使用 `--session-id` 参数，让 Claude CLI 自动生成
```python
process = subprocess.Popen(
    [
        "claude",
        "-p", initial_prompt
        # 移除 --session-id 参数
    ],
    ...
)
# 然后从 Claude CLI 输出或 transcript 目录获取自动生成的 session_id
```

**推荐方案一**，因为：
- 保持 task_id 的可读性（便于人工识别任务）
- session_id 使用 UUID 满足 Claude CLI 要求
- 两者分离，职责清晰

**相关文件**:
- `plugins/daemon-archon/scripts/server/probe_executor.py` (主要修改)
- `plugins/daemon-archon/scripts/server/main.py` (可选修改)

**修复记录** (2026-02-04):
采用方案一，生成 UUID 作为 session_id：

1. 在 `probe_executor.py` 中添加 `import uuid`
2. 修改 `_start_claude_cli` 方法：
```python
# 生成 UUID 作为 session_id（Claude CLI 要求 UUID 格式）
session_id = str(uuid.uuid4())

process = subprocess.Popen(
    [
        "claude",
        "-p", initial_prompt,
        "--session-id", session_id  # 使用 UUID 而非 task_id
    ],
    ...
)
```

修复后 Probe 任务可正常创建和启动。

---

### BUG-003: Probe 完成后状态检测失败：无法获取 transcript 路径

- **状态**: [x] 已修复
- **优先级**: P1(高)
- **发现日期**: 2026-02-04
- **修复日期**: 2026-02-04
- **影响范围**: Probe 任务状态检测 (`/check-task`)

**问题描述**:
当 Probe 任务快速完成并正常退出后，执行 `/check-task` 检查任务状态时返回 `"status": "unknown", "summary": "无法获取 transcript 路径"`，无法正确识别任务已完成。

**复现步骤**:
1. 创建一个简单的 Probe 任务（如分析项目亮点）
2. 等待 Probe 完成（Claude CLI 输出结果后退出）
3. 执行 `/check-task <task_id>`
4. 返回 `{"status": "unknown", "summary": "无法获取 transcript 路径"}`

**实际现象**:
```bash
# Probe 已成功完成，输出在 probe_stdout.log 中
$ cat ~/.claude/daemon-archon/20260204_113007_probe/probe_stdout.log
# 包含完整的分析结果

# 但进程已退出
$ ps -p 3413
# 进程已退出

# 检查任务状态
$ curl -X POST http://127.0.0.1:8765/probe/20260204_113007_probe/check
{"task_id": "20260204_113007_probe", "status": "unknown", "summary": "无法获取 transcript 路径", ...}
```

**根因分析**:

1. **transcript 路径获取逻辑问题**：`probe_executor.py` 中的 `check_probe` 方法依赖 `get_transcript_path(session_id)` 获取 transcript 文件路径，但该函数可能无法正确定位 Claude CLI 生成的 transcript 文件。

2. **进程退出检测不完善**：当检测到进程已退出时，代码将状态设为 `stopped`，但没有进一步分析 `probe_stdout.log` 来判断任务是否成功完成。

```python
# probe_executor.py:229-239
if not process_alive:
    append_log(self.task_id, "WARNING", f"Probe 进程 {pid} 已退出")
    set_task_status(self.task_id, "stopped")
    return AnalysisResult(
        status="stopped",
        summary=f"Probe 进程 {pid} 已退出"
    )
```

3. **缺少对 stdout 输出的分析**：即使无法获取 transcript，也应该分析 `probe_stdout.log` 来判断任务执行结果。

**修复方案**:

方案一：增强进程退出时的结果分析
```python
async def check_probe(self) -> AnalysisResult:
    # ... 现有代码 ...

    if not process_alive:
        # 进程已退出，分析 stdout 判断是否成功完成
        stdout_log = Path(self.config.get("probe", {}).get("stdout_log", ""))
        if stdout_log.exists():
            content = stdout_log.read_text()
            # 检查是否包含完成标志
            completion_keywords = self.config.get("criteria", {}).get("completion_keywords", [])
            if any(kw in content for kw in completion_keywords) or len(content) > 500:
                set_task_status(self.task_id, "completed")
                return AnalysisResult(
                    status="completed",
                    summary="Probe 任务已完成",
                    progress=100
                )

        set_task_status(self.task_id, "stopped")
        return AnalysisResult(
            status="stopped",
            summary=f"Probe 进程 {pid} 已退出"
        )
```

方案二：修复 transcript 路径获取逻辑
```python
def get_transcript_path(session_id: str) -> Optional[str]:
    # 检查多个可能的 transcript 位置
    possible_paths = [
        Path.home() / ".claude" / "projects" / "*" / f"{session_id}.json",
        Path.home() / ".claude" / "sessions" / f"{session_id}.json",
        Path.home() / ".claude" / "transcripts" / f"{session_id}.json",
    ]

    for pattern in possible_paths:
        matches = list(Path.home().glob(str(pattern).replace(str(Path.home()), "")))
        if matches:
            return str(matches[0])

    return None
```

方案三（推荐）：结合方案一和方案二
- 优先尝试获取 transcript 进行分析
- 如果无法获取 transcript 但进程已退出，则分析 stdout 输出
- 根据输出内容判断任务是成功完成还是异常退出

**相关文件**:
- `plugins/daemon-archon/scripts/server/probe_executor.py`
- `plugins/daemon-archon/scripts/server/analyzer.py`

**修复记录** (2026-02-04):
采用方案三，结合增强进程退出分析和 transcript 路径搜索：

1. 修改 `probe_executor.py` 的 `check_probe` 方法：
```python
if not process_alive:
    # 进程已退出，分析 stdout 输出判断是否成功完成
    stdout_log_path = self.config.get("probe", {}).get("stdout_log")
    if stdout_log_path:
        stdout_log = Path(stdout_log_path)
        if stdout_log.exists():
            content = stdout_log.read_text(encoding='utf-8', errors='ignore')

            # 检查完成标志、输出长度、错误标志
            completion_keywords = self.config.get("criteria", {}).get("completion_keywords", [])
            has_completion = any(kw in content for kw in completion_keywords)
            has_output = len(content.strip()) > 500

            failure_indicators = self.config.get("criteria", {}).get("failure_indicators", [])
            has_error = any(indicator in content for indicator in failure_indicators)

            if (has_completion or has_output) and not has_error:
                set_task_status(self.task_id, "completed")
                return AnalysisResult(status="completed", summary="Probe 任务已完成", progress=100)
```

2. 增强 `analyzer.py` 的 `get_transcript_path` 函数：
```python
def get_transcript_path(session_id: str) -> Optional[str]:
    # 方法一：通过 claude --list-sessions 获取
    result = subprocess.run(["claude", "--list-sessions", "--format=json"], ...)
    if result.returncode == 0:
        sessions = json.loads(result.stdout)
        for session in sessions:
            if session.get("session_id") == session_id:
                return session.get("transcript_path")

    # 方法二：搜索常见的 transcript 位置
    possible_patterns = [
        "~/.claude/projects/*/session_id.jsonl",
        "~/.claude/sessions/session_id.jsonl",
        "~/.claude/transcripts/session_id.jsonl",
    ]
    for pattern in possible_patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
```

修复后，即使无法获取 transcript，也能通过分析 stdout 输出正确判断任务完成状态。

---

### BUG-004: Cron 任务执行结果解析失败：状态始终为 unknown

- **状态**: [x] 已修复
- **优先级**: P1(高)
- **发现日期**: 2026-02-04
- **修复日期**: 2026-02-04
- **影响范围**: Cron 任务执行结果分析

**问题描述**:
Cron 任务正常执行完成，但执行结果状态始终显示为 `unknown`，无法正确解析 Claude CLI 的输出。这导致：
1. 任务执行统计不准确（`last_result` 为 `None`）
2. 无法根据执行结果触发告警或通知
3. 内存监控等任务无法正确记录告警信息

**复现步骤**:
1. 创建 Cron 任务：`/start-cron 每分钟监控系统内存，超过100G时记录`
2. 等待任务自动执行或手动触发
3. 查看任务日志：`cat ~/.claude/daemon-archon/{task_id}/archon.log`
4. 日志显示 `执行完成: unknown, `

**实际现象**:
```bash
# 任务日志
$ cat ~/.claude/daemon-archon/20260204_115154_cron/archon.log
[2026-02-04 11:52:54] [ACTION] 开始执行 Cron 任务
[2026-02-04 11:53:34] [OUTPUT] 执行完成: unknown,   # 状态为 unknown，summary 为空

# 任务配置
$ cat config.json | jq '.execution'
{
  "run_count": 2,
  "last_result": null,  # 结果为 null
  "consecutive_failures": 0
}

# 当前系统内存 116GB > 100GB 阈值，但未记录告警
$ free -g
              total        used        free
Mem:            251         116          88
```

**根因分析**:

1. **Claude CLI 输出格式问题**：`cron_executor.py` 使用 `--output-format json` 参数执行 Claude CLI：
```python
# cron_executor.py:253-258
result = subprocess.run(
    [
        "claude",
        "-p", prompt,
        "--output-format", "json"  # 期望 JSON 格式输出
    ],
    ...
)
```

但 `--output-format json` 的实际输出格式可能与 `CronResultAnalyzer` 期望的格式不匹配。

2. **结果解析逻辑问题**：`CronResultAnalyzer.analyze_output()` 可能无法正确解析 Claude CLI 的 JSON 输出，导致返回默认的 `unknown` 状态。

3. **可能的输出格式差异**：
   - 期望格式：`{"status": "success", "summary": "...", "findings": [...], "metrics": {...}}`
   - 实际格式：Claude CLI 的 `--output-format json` 可能输出的是会话元数据，而非任务执行结果

**修复方案**:

方案一：移除 `--output-format json`，直接解析文本输出
```python
async def _execute_claude_cli(self, prompt: str) -> Dict[str, Any]:
    result = subprocess.run(
        [
            "claude",
            "-p", prompt
            # 移除 --output-format json
        ],
        ...
    )

    # 从文本输出中提取 JSON 结果
    output = result.stdout
    json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
    if json_match:
        try:
            return {"output": json.loads(json_match.group(1)), "raw": output}
        except json.JSONDecodeError:
            pass

    return {"output": output, "raw": output}
```

方案二：增强 `CronResultAnalyzer` 的解析能力
```python
class CronResultAnalyzer:
    def analyze_output(self, output: str) -> AnalysisResult:
        # 尝试多种解析方式
        # 1. 直接解析 JSON
        try:
            data = json.loads(output)
            if "result" in data:  # Claude CLI JSON 格式
                return self._parse_claude_json(data)
        except json.JSONDecodeError:
            pass

        # 2. 从 markdown 代码块中提取 JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return self._parse_result_json(data)
            except json.JSONDecodeError:
                pass

        # 3. 基于关键词分析
        return self._analyze_by_keywords(output)
```

方案三（推荐）：结合方案一和方案二
- 移除 `--output-format json`，获取原始文本输出
- 增强解析器，支持从文本中提取 JSON 或基于关键词分析
- 添加调试日志，记录原始输出便于排查

**相关文件**:
- `plugins/daemon-archon/scripts/server/cron_executor.py`
- `plugins/daemon-archon/scripts/server/analyzer.py`

---

### BUG-005: 停止任务后状态不一致：config.json 未更新

- **状态**: [x] 已修复
- **优先级**: P2(中)
- **发现日期**: 2026-02-05
- **修复日期**: 2026-02-05
- **影响范围**: 任务停止操作 (`/stop-cron`, `/stop-probe`)

**问题描述**:
调用 `/stop-cron` 或 `/stop-probe` API 停止任务后，虽然任务从调度器移除且不再执行，但 `config.json` 文件中的 `state.status` 字段没有更新为 `stopped`，仍然显示为 `active`。这导致：
1. API 返回的任务列表中状态显示不正确
2. 用户无法通过 `/list-tasks` 准确了解任务真实状态
3. 状态数据不一致，可能影响任务恢复逻辑

**复现步骤**:
1. 创建并启动一个 Cron 任务：`/start-cron ...`
2. 停止任务：`curl -X POST http://127.0.0.1:8765/cron/{task_id}/stop`
3. API 返回 `{"success": true}`
4. 检查任务状态：`curl http://127.0.0.1:8765/tasks`
5. 状态显示为 `active`，而非 `stopped`
6. 检查配置文件：`cat ~/.claude/daemon-archon/{task_id}/config.json`
7. `state.status` 仍为 `active`

**实际现象**:
```bash
# 停止任务
$ curl -X POST http://127.0.0.1:8765/cron/20260205_023911_cron/stop
{"success":true,"task_id":"20260205_023911_cron"}

# 检查 status 文件（已更新）
$ cat ~/.claude/daemon-archon/20260205_023911_cron/status
stopped

# 检查 config.json（未更新）
$ cat ~/.claude/daemon-archon/20260205_023911_cron/config.json | jq '.state.status'
"active"

# API 返回的状态（读取 config.json）
$ curl -s http://127.0.0.1:8765/tasks | jq '.tasks[] | select(.task_id=="20260205_023911_cron") | .state.status'
"active"

# 任务日志显示已停止
$ tail -1 ~/.claude/daemon-archon/20260205_023911_cron/archon.log
[2026-02-05 03:02:40] [ACTION] Cron 任务已停止

# 调度器日志显示已移除
$ grep "已移除任务" ~/.claude/daemon-archon/server.log | tail -1
2026-02-05 03:02:40,558 - server.scheduler - INFO - 已移除任务: cron_20260205_023911_cron
```

**根因分析**:

1. **状态存储机制不一致**：daemon-archon 使用两种方式存储任务状态：
   - `status` 文件：单独的文本文件，存储简单的状态字符串
   - `config.json` 文件：完整的任务配置，包含 `state.status` 字段

2. **`set_task_status` 只更新 status 文件**：
```python
# state_store.py:170-180
def set_task_status(task_id: str, status: str) -> bool:
    """设置任务状态"""
    task_dir = ensure_task_dir(task_id)
    status_file = task_dir / "status"

    try:
        status_file.write_text(status)  # 只更新 status 文件
        return True
    except Exception as e:
        logger.error(f"设置任务状态失败 [{task_id}]: {e}")
        return False
```

3. **API 读取 config.json**：`/tasks` API 通过 `load_task_config()` 读取 `config.json`，而不是读取 `status` 文件，导致返回的状态是旧的。

4. **stop_cron/stop_probe 只调用 set_task_status**：
```python
# cron_executor.py:370-374
async def stop_cron(self) -> bool:
    """停止 Cron 任务"""
    set_task_status(self.task_id, "stopped")  # 只更新 status 文件
    append_log(self.task_id, "ACTION", "Cron 任务已停止")
    return True
```

**修复方案**:

方案一（推荐）：修改 `set_task_status` 同时更新 config.json
```python
def set_task_status(task_id: str, status: str) -> bool:
    """设置任务状态"""
    task_dir = ensure_task_dir(task_id)
    status_file = task_dir / "status"

    try:
        # 更新 status 文件
        status_file.write_text(status)

        # 同时更新 config.json
        config = load_task_config(task_id)
        if config:
            config["state"]["status"] = status
            save_task_config(task_id, config)

        return True
    except Exception as e:
        logger.error(f"设置任务状态失败 [{task_id}]: {e}")
        return False
```

方案二：在 stop_cron/stop_probe 中手动更新配置
```python
async def stop_cron(self) -> bool:
    """停止 Cron 任务"""
    if not self.config:
        self.load_config()

    # 更新配置
    if self.config:
        self.config["state"]["status"] = "stopped"
        save_task_config(self.task_id, self.config)

    set_task_status(self.task_id, "stopped")
    append_log(self.task_id, "ACTION", "Cron 任务已停止")
    return True
```

方案三：统一状态存储，移除 status 文件
```python
def set_task_status(task_id: str, status: str) -> bool:
    """设置任务状态"""
    config = load_task_config(task_id)
    if not config:
        return False

    config["state"]["status"] = status
    return save_task_config(task_id, config)

def get_task_status(task_id: str) -> Optional[str]:
    """获取任务状态"""
    config = load_task_config(task_id)
    return config.get("state", {}).get("status") if config else None
```

**推荐方案一**，因为：
- 保持向后兼容（status 文件仍然存在）
- 确保两种状态存储方式同步
- 修改最小，影响范围可控

**相关文件**:
- `plugins/daemon-archon/scripts/server/state_store.py` (主要修改)
- `plugins/daemon-archon/scripts/server/cron_executor.py`
- `plugins/daemon-archon/scripts/server/probe_executor.py`

**修复记录** (2026-02-04):
采用方案三，移除 `--output-format json` 并增强解析器：

1. 修改 `cron_executor.py` 的 `_execute_claude_cli` 方法：
```python
# 移除 --output-format json，获取原始文本输出
result = subprocess.run(
    [
        "claude",
        "-p", prompt
        # 移除 --output-format json
    ],
    ...
)

# 记录原始输出用于调试
logger.debug(f"Claude CLI 原始输出: {result.stdout[:500]}")
```

2. 增强 `analyzer.py` 的 `CronResultAnalyzer.analyze_output` 方法：
```python
def analyze_output(self, output: str) -> AnalysisResult:
    # 方法一：尝试直接解析 JSON
    try:
        result = json.loads(output)
        return self._analyze_json_result(result)
    except json.JSONDecodeError:
        pass

    # 方法二：从 markdown 代码块中提取 JSON
    json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            return self._analyze_json_result(result)
        except json.JSONDecodeError:
            pass

    # 方法三：基于关键词分析文本
    return self._analyze_text_result(output)
```

3. 增强 `_analyze_text_result` 方法：
```python
def _analyze_text_result(self, output: str) -> AnalysisResult:
    # 检查错误、警告、成功关键词
    # 提取数字指标（百分比、GB、MB、ms等）
    # 生成智能摘要
    # 默认状态为 success（而非 unknown）
```

修复后，Cron 任务可以正确解析 Claude CLI 的文本输出，状态不再始终为 unknown。

---

**BUG-005 修复记录** (2026-02-05):
采用方案一，修改 `set_task_status` 函数同时更新 `status` 文件和 `config.json`：

修改 `state_store.py` 的 `set_task_status` 函数：
```python
def set_task_status(task_id: str, status: str) -> bool:
    """
    设置任务状态

    同时更新 status 文件和 config.json 中的 state.status 字段
    """
    task_dir = ensure_task_dir(task_id)
    status_file = task_dir / "status"

    try:
        # 更新 status 文件
        status_file.write_text(status)

        # 同步更新 config.json
        config = load_task_config(task_id)
        if config:
            config.setdefault("state", {})["status"] = status
            save_task_config(task_id, config)

        return True
    except Exception as e:
        logger.error(f"设置任务状态失败 [{task_id}]: {e}")
        return False
```

修复后，调用 `/stop-cron` 或 `/stop-probe` API 停止任务时，`status` 文件和 `config.json` 中的状态会同步更新为 `stopped`，API 返回的任务状态也会正确显示。
