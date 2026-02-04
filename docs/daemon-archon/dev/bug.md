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
