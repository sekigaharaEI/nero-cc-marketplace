---
name: claude-exec
description: |
  将编码子任务委派给 Claude Code CLI 实例执行，由主 Claude 作为调度方负责规划、分派、验证和汇总。
  与 codex-exec 对称，但 Worker 具备完整的 Claude 推理能力，适合需要理解上下文、做架构判断的编码任务。
  使用这个 skill 当：需要实现复杂功能、跨文件重构、需要理解项目上下文的编码任务。
  不适用：trivial 的 1-3 行改动、纯算法实现（用 codex-exec 更快）、需要用户确认才能继续的任务。
  触发词：「用 claude 跑」「claude 子任务」「claude worker」「分发给 claude」。
---

# claude-exec

Claude Code CLI 实例是**无状态的一次性代码执行者**，具备完整推理能力。主 Claude 是**规划者与管理者**，用户只与主 Claude 交互，子 Claude 调用是内部过程。

## 核心原则

**① 主 Claude 必须亲自验证**（最重要）：子 Claude 自报"完成"不可信。每次调用后，主 Claude 独立运行验证命令确认结果。

**② 子 Claude 无记忆**：每次调用必须在 prompt 中提供完整上下文（项目 CLAUDE.md、参考文件路径、接口规范、约束）。

**③ 给足上下文但不替他写代码**：传递接口定义、参考文件路径和项目规范，让子 Claude 自主实现。

**④ 失败重试上限**：同一问题连续失败 2 次后，第 3 次主 Claude 接管自行修复。

**⑤ 只汇报结果**：向用户呈现最终摘要，不暴露子 Claude 调用细节。

**⑥ 文件隔离**：多个子 Claude 并行时，必须确保各实例操作不同文件，避免写入冲突。

---

## 快速判断：该不该用 claude-exec？

| 条件 | claude-exec | codex-exec | 主 Claude 自行处理 |
|------|:-----------:|:----------:|:-----------------:|
| 需要理解项目上下文 | ✓ | | |
| 跨文件重构/关联改动 | ✓ | | |
| 纯算法/单模块实现 | | ✓ | |
| 1-3 行 trivial 改动 | | | ✓ |
| 需要用户确认 | | | ✓ |

---

## CLI 检测

优先使用 `claude-jty-yolo` alias（自带认证和权限配置），不存在则降级为原生 `claude`：

```bash
if command -v claude-jty-yolo &>/dev/null || alias claude-jty-yolo &>/dev/null 2>&1; then
  CLAUDE_CMD="claude-jty-yolo"
else
  CLAUDE_CMD="claude"
fi
echo "使用: $CLAUDE_CMD"
```

---

## tmux 环境联动

调用子 Claude 前，先检测运行环境，决定执行方式：

```bash
if [ -n "$TMUX" ]; then
  # 在 tmux 中：检查是否有可用的 Worker pane
  # 优先使用 parallel-dispatch 的 Worker pane
  # 或使用 tmux-layout 的右上 Pane B
  RIGHT_TOP=$(tmux show-environment CLAUDE_PANE_RIGHT_TOP 2>/dev/null | cut -d= -f2)
  PANES_ALIVE=$(tmux list-panes -a -F '#{pane_id}' 2>/dev/null)

  if echo "$PANES_ALIVE" | grep -q "^${RIGHT_TOP}$"; then
    TASK_SUMMARY="<从 prompt 中提取的 2-4 词简述>"
    # 设置 pane 标题和文字颜色（橙色 colour208，区别于 Codex 的淡蓝）
    tmux select-pane -t "$RIGHT_TOP" -T "claude-${TASK_SUMMARY}"
    tmux select-pane -t "$RIGHT_TOP" -P 'fg=colour208,bg=default'
    # → 使用 tmux 路由模式
  else
    echo "Worker pane 不存在，建议先运行 /tmux-layout 建立布局"
    # → 降级使用直连模式
  fi
else
  # 不在 tmux 中 → 直连模式
fi
```

---

## 调用命令

### tmux 路由模式（在 Worker pane 中执行）

```bash
TARGET_PANE=<Worker pane ID>
OUTFILE="/tmp/claude_$(date +%s).txt"
TASK_SUMMARY="<2-4 词简述>"

# 检测 CLI
CLAUDE_CMD=$(command -v claude-jty-yolo &>/dev/null && echo "claude-jty-yolo" || echo "claude")

# 设置 pane 标题（橙色）和文字颜色
tmux select-pane -t "$TARGET_PANE" -T "claude-${TASK_SUMMARY}"
tmux select-pane -t "$TARGET_PANE" -P 'fg=colour208,bg=default'

# 发送任务：执行完毕后自动恢复标题和颜色
tmux send-keys -t "$TARGET_PANE" \
  "cd <workdir> && \
   $CLAUDE_CMD -p \"$(cat <<'CLAUDE_PROMPT'
[完整任务 prompt，见下方规范]
CLAUDE_PROMPT
)\" > $OUTFILE 2>&1; \
   tmux select-pane -t $TARGET_PANE -T 'Claude Worker'; \
   tmux select-pane -t $TARGET_PANE -P 'default'" Enter
```

执行完毕后，用 Read 工具读取结果：`$OUTFILE`

### 直连模式（非 tmux 环境或布局未建立时）

```bash
CLAUDE_CMD=$(command -v claude-jty-yolo &>/dev/null && echo "claude-jty-yolo" || echo "claude")

cd /absolute/path/to/workdir && \
  $CLAUDE_CMD -p "$(cat <<'CLAUDE_PROMPT'
[完整任务 prompt，见下方规范]
CLAUDE_PROMPT
)"
```

**工作目录必须与当前项目目录一致**，通过 `cd` 切换后再调用。

---

## Prompt 五要素（缺一不可）

```
## 工作目录
<绝对路径>

## 项目规范
<从 CLAUDE.md 中提取的关键约束：语言版本、格式要求、禁止事项等>
<项目的 CLAUDE.md 路径，让子 Claude 自己去读>

## 任务描述
<具体实现内容：目标文件路径、接口签名、输入输出格式、与其他模块的关系>
<需要参考的现有文件路径（让子 Claude 自己去读）>
<如需修改现有文件，说明要改的接口/逻辑，不要粘贴整个文件>
注意：不要提供完整实现代码，只给接口规范，让子 Claude 自主实现

## 成功标准
<可直接执行的验证命令 + 期望输出>
验证命令要同步执行（非后台）

## 注意事项
<边界情况、禁止改动的文件、特殊依赖、文件隔离要求等>
<明确列出本次任务只允许修改的文件范围>
```

---

## 超时时间预估

| 任务类型 | 建议超时 |
|---------|---------|
| 小型单文件实现（< 100 行） | 180s |
| 中型模块实现（100~300 行） | 300s |
| 大型模块 + 测试文件 | 480s |
| 跨文件重构 | 600s（上限） |

> 比 Codex 略长，因为 Claude 会做更多推理和验证。

---

## 执行循环

```
对每个子任务：

  1. 构建 prompt（五要素）
     → 检测 CLI：claude-jty-yolo 存在？
       ├── 是 → 使用 claude-jty-yolo（自带认证+权限）
       └── 否 → 使用原生 claude
     → 检测环境：$TMUX 非空 且 Worker pane 存在？
       ├── 是 → 设置 pane 标题和文字色为橙色，tmux 路由模式执行
       └── 否 → 直连模式执行

  2. 读取输出：
     ├── 输出正常 → 直接读取
     └── 输出超大被截断 → tail -50 读取输出文件

  3. 主 Claude 亲自运行验证命令（不信任子 Claude 自报）：
     ├── 通过 → git add <具体文件> && git commit → 下一子任务
     └── 失败一次 → 分析原因，补充上下文，重新调用
           └── 失败两次（同一问题）→ 主 Claude 接管直接修复

全部子任务完成 → 向用户汇报摘要
```

---

## 与 codex-exec 的对比

| | claude-exec | codex-exec |
|---|---|---|
| 底层模型 | Claude (Sonnet/Opus) | gpt-5.3-codex |
| 推理能力 | 完整推理 + 工具调用 | 擅长代码生成 |
| 上下文理解 | 可读 CLAUDE.md、理解项目结构 | 需要在 prompt 中给足上下文 |
| pane 文字色 | 橙色（colour208） | 淡蓝（colour117） |
| pane 标题前缀 | `claude-` | `codex-` |
| 适用场景 | 跨文件重构、复杂功能、需要判断力 | 纯算法、单模块实现、API handler |
| 超时 | 较长（180s~600s） | 较短（120s~300s） |

---

## 已知陷阱

| 陷阱 | 规避方式 |
|------|---------|
| 子 Claude 自报"完成"但实际有问题 | 主 Claude 必须亲自跑验证命令 |
| 多个子 Claude 同时改同一文件 | 任务拆分时确保文件范围不重叠，在 prompt 注意事项中明确限制 |
| claude-jty-yolo alias 在子 shell 中不可用 | 用 `bash -ic` 加载 alias，或直接展开完整命令 |
| 子 Claude 改了不该改的文件 | prompt 中明确列出允许修改的文件白名单 |
| 输出超大被截断 | 重定向到文件，`tail -50` 读取 |
| 忘记用 `cd` 统一工作目录 | 调用命令始终以 `cd <workdir> &&` 开头 |

---

## 向用户汇报格式

全部子任务完成后，统一汇报一次：

```
## 执行结果

**完成：**
- [任务1]：✓ 已实现，测试通过（主 Claude 独立验证）
- [任务2]：✓ 已实现，测试通过（主 Claude 独立验证）

**接管修复：**（如有）
- [问题描述]：子 Claude 两次失败，主 Claude 接管完成

**最终状态：** 全部完成 / 部分完成（原因）
```
