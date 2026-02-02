# Memory Stalker - Windows 中文路径问题分析

> 分析者: OpenClaw  
> 分析时间: 2026-02-02 19:01  
> 状态: 仅分析，未修改代码

---

## 问题描述

用户反馈：在 Windows 环境下，当项目路径包含中文字符时，`save_memory.py` 脚本会出现问题。

---

## 代码分析

### 涉及文件

1. `plugins/memory-stalker/scripts/save_memory.py` - 主脚本
2. `plugins/memory-stalker/scripts/transcript_parser.py` - 解析器

### 潜在问题点

#### 1. 文件路径处理

**问题代码位置**: `save_memory.py` 第 218-220 行

```python
def save_memory(memory_content: str, project_path: str, session_id: str) -> Optional[Path]:
    memories_dir = Path(project_path) / ".claude" / "memories"
    memories_dir.mkdir(parents=True, exist_ok=True)
```

**分析**:
- `Path()` 在 Windows 上使用 `WindowsPath`，理论上支持 Unicode
- 但 `project_path` 来自 `hook_input.get("cwd", os.getcwd())`
- 如果 Claude Code 传入的 `cwd` 编码有问题，可能导致路径解析失败

#### 2. 日志文件路径

**问题代码位置**: `save_memory.py` 第 32-33 行

```python
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_FILE = LOG_DIR / "memory_stalker.log"
```

**分析**:
- `Path.home()` 在 Windows 中文用户名下可能返回包含中文的路径
- 例如: `C:\Users\张三\.claude\logs`
- 如果系统编码不是 UTF-8，可能导致日志写入失败

#### 3. 文件读取编码

**问题代码位置**: `transcript_parser.py` 第 35 行

```python
with open(transcript_file, "r", encoding="utf-8") as f:
```

**分析**:
- 这里显式指定了 `encoding="utf-8"`，是正确的做法
- 但如果 `transcript_file` 路径本身包含中文，在某些 Windows 配置下可能失败

#### 4. 文件写入

**问题代码位置**: `save_memory.py` 第 230 行

```python
memory_file.write_text(memory_content, encoding="utf-8")
```

**分析**:
- 写入时指定了 UTF-8 编码，内容编码没问题
- 但如果 `memory_file` 路径包含中文，可能在某些情况下失败

#### 5. 环境变量读取

**问题代码位置**: `save_memory.py` 第 50 行

```python
plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
```

**分析**:
- Windows 环境变量在传递中文路径时可能存在编码问题
- 特别是在 Python 3.8 + Windows 旧版本组合下

---

## 根本原因分析

### Windows 中文路径问题的常见原因

1. **系统代码页 (Code Page) 问题**
   - Windows 默认使用 GBK/GB2312 (Code Page 936) 而非 UTF-8
   - Python 的 `open()` 函数在不指定编码时使用系统默认编码
   - 路径字符串在不同编码间转换时可能出错

2. **Python 版本差异**
   - Python 3.6+ 在 Windows 上改进了 Unicode 路径支持
   - 但某些边缘情况仍可能出问题

3. **subprocess 调用**
   - 如果脚本通过 subprocess 被调用，参数传递可能丢失编码信息

4. **JSON 解析**
   - `hook_input` 从 stdin 读取 JSON
   - 如果 stdin 的编码不是 UTF-8，中文路径可能被错误解析

---

## 可能的解决思路

### 思路 1: 强制 UTF-8 模式 (Python 3.7+)

在脚本开头添加环境变量设置：

```python
import os
os.environ["PYTHONUTF8"] = "1"  # 必须在导入其他模块前设置
```

或者在运行脚本时设置环境变量：
```batch
set PYTHONUTF8=1
python save_memory.py
```

**优点**: 简单，一行代码解决
**缺点**: 需要 Python 3.7+，且必须在最开始设置

### 思路 2: 显式处理 stdin 编码

```python
import sys
import io

# 强制 stdin 使用 UTF-8
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
```

**优点**: 解决 JSON 输入的编码问题
**缺点**: 只解决输入问题，不解决路径问题

### 思路 3: 路径规范化

```python
from pathlib import Path

def normalize_path(path_str: str) -> Path:
    """规范化路径，处理 Windows 中文路径问题"""
    # 尝试将路径转换为 Path 对象
    try:
        p = Path(path_str)
        # 使用 resolve() 获取绝对路径，可能有助于解决某些编码问题
        return p.resolve()
    except Exception:
        # 如果失败，尝试使用 os.fsencode/fsdecode
        import os
        encoded = os.fsencode(path_str)
        decoded = os.fsdecode(encoded)
        return Path(decoded)
```

**优点**: 更健壮的路径处理
**缺点**: 增加代码复杂度

### 思路 4: 使用短路径名 (Windows 8.3 格式)

```python
import ctypes
from ctypes import wintypes

def get_short_path_name(long_path: str) -> str:
    """获取 Windows 短路径名 (8.3 格式)，避免中文问题"""
    if not sys.platform == 'win32':
        return long_path
    
    GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    GetShortPathNameW.restype = wintypes.DWORD
    
    buffer_size = GetShortPathNameW(long_path, None, 0)
    if buffer_size == 0:
        return long_path
    
    buffer = ctypes.create_unicode_buffer(buffer_size)
    GetShortPathNameW(long_path, buffer, buffer_size)
    return buffer.value
```

**优点**: 完全避免中文路径问题
**缺点**: 仅适用于 Windows，代码复杂，且短路径可能被禁用

### 思路 5: 异常处理与回退

```python
def safe_write_file(file_path: Path, content: str) -> bool:
    """安全写入文件，带回退机制"""
    try:
        file_path.write_text(content, encoding="utf-8")
        return True
    except (OSError, UnicodeError) as e:
        logger.warning("Failed to write to %s: %s", file_path, e)
        
        # 回退：使用临时目录
        import tempfile
        fallback_dir = Path(tempfile.gettempdir()) / "memory_stalker"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_file = fallback_dir / file_path.name
        
        try:
            fallback_file.write_text(content, encoding="utf-8")
            logger.info("Fallback: saved to %s", fallback_file)
            return True
        except Exception as e2:
            logger.error("Fallback also failed: %s", e2)
            return False
```

**优点**: 不会完全失败，有回退方案
**缺点**: 文件位置可能不符合预期

### 思路 6: 检测并警告

在脚本开头添加检测逻辑：

```python
def check_path_encoding(path_str: str) -> bool:
    """检查路径是否包含可能有问题的字符"""
    try:
        # 尝试编码为 ASCII
        path_str.encode('ascii')
        return True
    except UnicodeEncodeError:
        # 包含非 ASCII 字符
        if sys.platform == 'win32':
            logger.warning(
                "Path contains non-ASCII characters: %s\n"
                "This may cause issues on Windows. Consider:\n"
                "1. Moving project to ASCII-only path\n"
                "2. Setting PYTHONUTF8=1 environment variable",
                path_str
            )
        return False
```

**优点**: 提前发现问题，给用户明确提示
**缺点**: 不解决问题，只是警告

---

## 推荐方案

### 短期方案（最小改动）

1. 在脚本开头设置 `PYTHONUTF8=1`
2. 显式设置 stdin 编码为 UTF-8
3. 添加异常处理和日志

### 长期方案（更健壮）

1. 使用 `os.fsencode()` / `os.fsdecode()` 处理所有路径
2. 添加路径编码检测和警告
3. 实现回退机制（临时目录）
4. 在文档中说明 Windows 中文路径的限制

---

## 测试建议

1. **测试环境**:
   - Windows 10/11 中文版
   - 用户名包含中文（如 `C:\Users\张三`）
   - 项目路径包含中文（如 `D:\项目\测试项目`）

2. **测试用例**:
   - 用户目录包含中文
   - 项目路径包含中文
   - transcript.jsonl 路径包含中文
   - 同时包含中文和特殊字符（空格、括号等）

3. **验证点**:
   - 日志文件能否正常创建
   - 记忆文件能否正常保存
   - 错误信息是否清晰

---

## 参考资料

- [PEP 540 – Add a new UTF-8 Mode](https://peps.python.org/pep-0540/)
- [Python Windows FAQ - Unicode filenames](https://docs.python.org/3/faq/windows.html)
- [pathlib — Object-oriented filesystem paths](https://docs.python.org/3/library/pathlib.html)

---

*本文档由 OpenClaw 自动生成，仅供参考。实际修改代码前请进行充分测试。*
