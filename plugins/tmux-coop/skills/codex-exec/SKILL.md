---
name: codex-exec
description: |
  将明确的后端/算法编码子任务委派给 OpenAI Codex CLI 执行，由 Claude 作为调度方负责规划、分派、验证和汇总。
  使用这个 skill 当用户要求：实现新函数/类/模块、算法实现、API handler、数据库操作、查询脚本（SQL/ES/Redis）、测试编写、文件重构、批处理脚本。
  只要任务明确且可用一个自包含 prompt 完整描述、任务量值得调用外部执行器，就应该使用这个 skill。
  不适用：架构规划、方案讨论、trivial 的 1-3 行改动（字段追加/import 新增等）、需要用户确认才能继续的任务。
  当用户说「帮我实现」「写一个」「新增模块」「重构」「写测试」「写查询」「写脚本」时，优先考虑使用这个 skill。
---

# codex-exec

Codex 是**无状态、无上下文的一次性代码执行者**（基于 gpt-5.3-codex，擅长后端/算法）。Claude 是**规划者与管理者**，用户只与 Claude 交互，Codex 调用是内部过程。

## 核心原则

**① Claude 必须亲自验证**（最重要）：Codex 自报"通过"不可信。每次调用后，Claude 独立运行验证命令确认结果，不依赖 Codex 的任何自述。

**② Codex 无记忆**：每次调用必须在 prompt 中提供完整上下文（参考文件路径、接口规范、约束）。

**③ 不要替他写代码**：只传递接口定义和参考文件路径，不要把已写好的实现代码发给他——Codex 在代码实现上能力很强，给他空间自主发挥。

**④ 失败重试上限**：同一问题连续失败 2 次后，第 3 次 Claude 接管自行修复，不再调用 Codex。

**⑤ 只汇报结果**：向用户呈现最终摘要，不暴露 Codex 调用细节。

---

## 快速判断：该不该用 Codex？

问自己三个问题：
1. 任务能用一段话完整描述清楚吗？（接口、输入输出、约束都明确）
2. 改动量超过 5 行吗？
3. 不需要用户进一步确认吗？

三个都是"是" → 交给 Codex。任何一个"否" → Claude 自行处理。

---

## tmux 环境联动

调用 Codex 前，先检测运行环境，决定执行方式：

```bash
if [ -n "$TMUX" ]; then
  # 在 tmux 中：检查右下 Pane C 是否存在
  RIGHT_BOTTOM=$(tmux show-environment CLAUDE_PANE_RIGHT_BOTTOM 2>/dev/null | cut -d= -f2)
  PANES_ALIVE=$(tmux list-panes -a -F '#{pane_id}' 2>/dev/null)

  if echo "$PANES_ALIVE" | grep -q "^${RIGHT_BOTTOM}$"; then
    # 右下 pane 存在 → 路由到 Pane C
    # 从任务 prompt 提取 2-4 个词的简述作为 pane 标题后缀，例如 "codex-实现缓存模块"
    TASK_SUMMARY="<从 prompt 中提取的简述>"
    # 设置 pane 标题（深色背景下用淡蓝色 colour117，比纯蓝 colour33 更易读）
    tmux select-pane -t "$RIGHT_BOTTOM" -T "codex-${TASK_SUMMARY}"
    tmux select-pane -t "$RIGHT_BOTTOM" -P 'fg=colour117,bg=default'
    # → 使用 tmux 路由模式（见"调用命令 - tmux 路由"），任务结束后恢复
  else
    # 在 tmux 中但布局未建立 → 提示用户先运行 /tmux-layout，或降级为当前 pane 执行
    echo "右下 Pane C 不存在，建议先运行 /tmux-layout 建立布局"
    # → 降级使用直连模式（见"调用命令 - 直连"）
  fi
else
  # 不在 tmux 中 → 直接在当前终端执行
  # → 使用直连模式（见"调用命令 - 直连"）
fi
```

---

## 调用命令

### tmux 路由模式（在 tmux 右下 Pane C 中执行）

```bash
RIGHT_BOTTOM=$(tmux show-environment CLAUDE_PANE_RIGHT_BOTTOM | cut -d= -f2)
OUTFILE="/tmp/codex_$(date +%s).txt"
TASK_SUMMARY="<从 prompt 中提取的 2-4 词简述>"  # 例如：实现缓存模块、重构用户服务

# 设置 pane 标题为 "codex-<简述>"，文字色用淡蓝（colour117，深色背景下清晰可读）
tmux select-pane -t "$RIGHT_BOTTOM" -T "codex-${TASK_SUMMARY}"
tmux select-pane -t "$RIGHT_BOTTOM" -P 'fg=colour117,bg=default'

# 发送任务到右下 pane：执行完毕后自动恢复标题和颜色
tmux send-keys -t "$RIGHT_BOTTOM" \
  "cd <workdir> && \
   HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 \
   timeout <秒数> codex exec --full-auto \
   --sandbox danger-full-access \
   --model gpt-5.3-codex \
   \"$(cat <<'CODEX_PROMPT'
[完整任务 prompt，见下方规范]
CODEX_PROMPT
)\" > $OUTFILE 2>&1; \
   tmux select-pane -t $RIGHT_BOTTOM -T 'Codex'; \
   tmux select-pane -t $RIGHT_BOTTOM -P 'default'" Enter
```

执行完毕后，用 Read 工具读取结果：`$OUTFILE`

### 直连模式（非 tmux 环境或布局未建立时）

```bash
cd /absolute/path/to/workdir && \
HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 \
  timeout <秒数> codex exec --full-auto \
  --sandbox danger-full-access \
  --model gpt-5.3-codex \
  "$(cat <<'CODEX_PROMPT'
[完整任务 prompt，见下方规范]
CODEX_PROMPT
)"
```

**工作目录必须与当前 Claude Code 的工作目录一致**，通过 `cd` 切换后再调用，不使用 `-C` 参数。

**关键参数：**
- `--sandbox danger-full-access`：授予完整文件系统访问权限，避免 Codex 频繁请求权限确认
- `--full-auto`：自动执行所有操作，无需人工确认
- `timeout <秒数>`：防止超时挂起，见下方预估表

**恢复上一次会话：**
```bash
cd /absolute/path/to/workdir && codex exec resume --last "继续上次任务的第二阶段"
```

> 更多非交互模式参数见 `references/non-interactive.md`

---

## 超时时间预估

| 任务类型 | 建议超时 |
|---------|---------|
| 小型单文件实现（< 100 行） | 120s |
| 中型模块实现（100~300 行） | 200s |
| 大型模块 + 测试文件 | 300s |
| 复杂多文件改动 | 300s（上限） |

---

## Prompt 五要素（缺一不可）

```
## 工作目录
<绝对路径>

## 开发规范
<从项目 CLAUDE.md 或编码规范中提取的关键约束：语言版本、格式要求、禁止事项等>

## 任务描述
<具体实现内容：目标文件路径、接口签名、输入输出格式、与其他模块的关系>
<需要参考的现有文件路径（让 Codex 自己去读）>
<如需修改现有文件，说明要改的接口/逻辑，不要粘贴整个文件>
注意：不要提供完整实现代码，只给接口规范，让 Codex 自主实现

## 成功标准
<可直接执行的验证命令 + 期望输出>
验证命令要同步执行（非后台），避免环境变量未加载导致误判

## 注意事项
<边界情况、禁止改动的文件、特殊依赖、环境变量说明等>
```

### 任务描述的写法

**正确：给参考文件，让 Codex 自读**
```
参考 agent/proofread/vocabulary_precheck/db_loader.py 的 DB 连接模式
参考 agent/proofread/sensitive_filter.py 的 AC 自动机实现
```

**错误：把代码贴给 Codex**
```python
# 不要这样做
class MyClass:
    def __init__(self):
        ...（完整实现粘贴）
```

---

## 任务粒度建议

按**模块级**分派，不做函数级拆分：
- 一个完整的类（含初始化、方法、单例）→ 一次 Codex 调用
- 一个完整的测试文件（含所有用例）→ 一次 Codex 调用
- 同一文件内多处关联改动 → 一次 Codex 调用

1-3 行 trivial 改动（import 追加、字段新增）由 Claude 直接处理，不值得调用 Codex。

---

## 执行循环

```
对每个子任务：

  1. 构建 prompt（五要素）
     → 检测环境：$TMUX 非空 且 右下 Pane C 存在？
       ├── 是 → 设置 Pane C 文字颜色为蓝色（colour33），tmux 路由模式执行
       └── 否 → 直连模式执行（非 tmux 或布局未建立）

  2. 读取输出：
     ├── 输出正常 → 直接读取
     └── 输出超大被截断 → tail -50 读取持久化输出文件
         路径：~/.claude/projects/<project>/tool-results/<id>.txt

  3. Claude 亲自运行验证命令（不信任 Codex 自报）：
     ├── 通过 → git add <具体文件> && git commit → 下一子任务
     └── 失败一次 → 分析原因，补充上下文，重新调用 Codex
           └── 失败两次（同一问题）→ Claude 接管直接修复

全部子任务完成 → 向用户汇报摘要
```

---

## 验证命令规范

验证命令必须**同步执行**，过滤掉项目启动噪音：

```bash
# Python 测试（过滤无关 warning）
source .venv/bin/activate && \
  python -m pytest <test_path> -v 2>&1 | grep -E "PASSED|FAILED|ERROR|passed|failed|error"

# 功能验证（过滤项目初始化日志）
source .venv/bin/activate && python -c "
<验证代码>
" 2>&1 | grep -v -E "UserWarning|warnings\.warn|Loading settings|Init |Settings loaded"

# 导入检查
source .venv/bin/activate && python -m py_compile <file.py> && echo "语法OK"
```

**注意**：Codex 子进程中环境变量（DB_HOST 等）可能未加载，若依赖外部服务（数据库、API），验证时需确认服务可达，或在成功标准中说明降级行为也是合法结果。

---

## 已知陷阱

| 陷阱 | 规避方式 |
|------|---------|
| Codex 自报"通过"但实际有问题 | Claude 必须亲自跑验证命令，独立确认 |
| 输出超大被截断看不到结果 | `tail -50` 读取持久化输出文件 |
| DB/外部服务连接超时（环境变量未加载） | 验证命令用同步调用；成功标准中说明降级行为 |
| 把完整代码贴给 Codex | 只给接口规范 + 参考文件路径 |
| 任务拆太细，反而变慢 | 按模块级分派，单次改动点控制在 5 处以内 |
| 忘记用 `cd` 统一工作目录 | 调用命令始终以 `cd <workdir> &&` 开头 |
| git add . 混入无关文件 | 提交时指定具体文件，不用 `git add .` |

---

## 任务分派速查

| 任务类型 | Codex | Claude 自行处理 |
|---------|:-----:|:------:|
| 实现函数/类/模块 | ✓ | |
| 算法实现 | ✓ | |
| API handler / service 层 | ✓ | |
| 数据库查询/迁移 | ✓ | |
| 测试编写 | ✓ | |
| 单文件或多文件重构（接口明确） | ✓ | |
| 1-3 行 trivial 改动 | | ✓ |
| 架构决策/方案规划 | | ✓ |
| 需用户确认才能继续 | | ✓ |
| 同一问题连续失败 2 次 | | ✓ 接管 |

---

## 向用户汇报格式

全部子任务完成后，统一汇报一次：

```
## 执行结果

**完成：**
- [任务1]：✓ 已实现，测试通过（Claude 独立验证）
- [任务2]：✓ 已实现，测试通过（Claude 独立验证）

**接管修复：**（如有）
- [问题描述]：Codex 两次失败，Claude 接管完成

**最终状态：** 全部完成 / 部分完成（原因）
```
