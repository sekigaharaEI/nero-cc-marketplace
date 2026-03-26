---
name: parallel-dispatch
description: |
  tmux 并行任务调度工作流。将用户任务拆解后分配给多个 Worker pane 并行执行，Claude 作为 Dispatcher 负责规划、下发、监控和汇总。
  使用这个 skill 当：需要并行执行多个独立子任务、批量处理、多路并发测试或数据处理。
  不适用：任务有强依赖顺序且无法并行、只有单个子任务、任务需要用户逐步确认。
  触发词：「并行执行」「同时跑」「多个 worker」「批量处理」「parallel」。
---

# parallel-dispatch — tmux 并行任务调度工作流

## 角色定义

- **Dispatcher（调度员）**：Claude，负责任务拆解、分配、监控、汇总
- **Worker**：右侧 tmux pane，负责执行命令，输出重定向到日志文件

---

## 第一步：环境初始化

### 1.1 确认当前环境

```bash
[ -z "$TMUX" ] && echo "请先进入 tmux session" && exit 1
tmux list-panes -a
```

记录当前 session 名和主 pane 编号（通常是 `.0`）。

### 1.2 确定 Worker 数量

根据任务数量决定 Worker 数量，**上限 4 个**（过多 pane 太窄难以阅读）：

| 子任务数 | Worker 数 |
|---------|----------|
| 1~2     | 2        |
| 3~4     | 3        |
| 5+      | 4（分批执行）|

### 1.3 创建 Worker pane（优先复用已有）

```bash
# 先检查是否已有布局
EXISTING=$(tmux list-panes -a -F '#{pane_id}' | wc -l)

if [ "$EXISTING" -le 1 ]; then
  SESSION=$(tmux display-message -p '#S')

  # 右侧垂直分割（右侧占 55%）
  tmux split-window -t ${SESSION}:0 -h -p 55

  # 右侧等分为 4 个 Worker：先对半分，再各自对半分
  # 第 1 次：上下对半（Worker1+2 占上半，Worker3+4 占下半）
  tmux split-window -t ${SESSION}:0.1 -v -p 50

  # 第 2 次：上半部分再对半（Worker1 和 Worker2）
  tmux split-window -t ${SESSION}:0.1 -v -p 50

  # 第 3 次：下半部分再对半（Worker3 和 Worker4）
  tmux split-window -t ${SESSION}:0.3 -v -p 50
fi
```

> 若 pane 已存在，跳过创建，只做颜色和标题设置。

### 1.4 缩窄主 pane

```bash
tmux resize-pane -t ${SESSION}:0.0 -x 95
```

### 1.5 设置 Worker 文字颜色

使用霓虹紫/蓝色系，深色背景下清晰可辨（需终端支持 true color）：

| Worker | pane | 颜色 Hex | 名称 |
|--------|------|----------|------|
| 1 | .1 | `#ff00ff` | Neon Purple 霓虹紫 |
| 2 | .2 | `#cc00ff` | Electric Purple 电紫 |
| 3 | .3 | `#9900ff` | Vivid Violet 亮紫 |
| 4 | .4 | `#6600ff` | Deep Cyber Indigo 赛博靛 |

```bash
tmux select-pane -t ${SESSION}:0.1 -P 'fg=#ff00ff,bg=default'
tmux select-pane -t ${SESSION}:0.2 -P 'fg=#cc00ff,bg=default'
tmux select-pane -t ${SESSION}:0.3 -P 'fg=#9900ff,bg=default'
tmux select-pane -t ${SESSION}:0.4 -P 'fg=#6600ff,bg=default'
```

> **前置条件**：终端需支持 true color
> ```bash
> tmux set -g default-terminal "tmux-256color"
> tmux set -ga terminal-overrides ",*256col*:Tc"
> ```
> `/tmux-init` 安装的配置已包含此项。

### 1.6 设置初始标题

```bash
tmux select-pane -t ${SESSION}:0.1 -T "Worker1 待分配"
tmux select-pane -t ${SESSION}:0.2 -T "Worker2 待分配"
tmux select-pane -t ${SESSION}:0.3 -T "Worker3 待分配"
tmux select-pane -t ${SESSION}:0.4 -T "Worker4 待分配"
```

---

## 第二步：任务规划

将用户需求拆分为若干独立子任务，每个任务明确：

| 字段 | 说明 |
|------|------|
| `task_id` | 任务标识，如 `task1`、`batch_search` |
| `desc` | 一句话描述 |
| `cmd` | 完整执行命令 |
| `log` | 日志路径：`/tmp/<task_id>.log` |
| `done_signal` | 完成判断关键字，如 `全部完成`、`=== DONE ===` |

### 并行性检查

- 无文件写入冲突 → 完全并行，一次下发所有 Worker
- 共享输出目录 → 确认各任务写不同子目录后并行
- 有依赖关系 → 分批，上一批全部完成后下发下一批

将任务均匀分配给各 Worker，**向用户展示分配方案后再执行**。

---

## 第三步：下发任务

**命令格式规范**（较复杂的任务优先写成独立 `/tmp/<task>.py` 文件再执行）：

```bash
tmux send-keys -t ${SESSION}:0.1 \
  "source /path/.venv/bin/activate && python /tmp/task1.py 2>&1 | tee /tmp/task1.log" \
  Enter
```

命令必须包含：
1. 激活虚拟环境（如需要）
2. 清除代理环境变量（若调用内网 API，在脚本开头处理：`os.environ.pop('HTTPS_PROXY', None)`）
3. `2>&1 | tee /tmp/<task>.log` 重定向日志（stdout + stderr 同时保留）

下发后立即更新 pane 标题为运行中状态：

```bash
tmux select-pane -t ${SESSION}:0.1 -T "Worker1 ⏳ <task_desc>"
tmux select-pane -t ${SESSION}:0.2 -T "Worker2 ⏳ <task_desc>"
```

---

## 第四步：监控

### 轻量监控命令

```bash
tail -5 /tmp/task1.log && echo "---" && \
tail -5 /tmp/task2.log && echo "---" && \
tail -5 /tmp/task3.log 2>/dev/null && echo "===" && \
echo "完成: $(find <output_dir> -name result.md | wc -l)/<total> | PASS:$(grep -rl 'PASS' <output_dir> | wc -l) FAIL:$(grep -rl 'FAIL' <output_dir> | wc -l)"
```

### 定时监控（任务耗时较长时）

```
/loop 1m <监控命令>
```

记录 cron job ID，任务全部完成后用 CronDelete 关闭。

### 任务完成后更新 pane 标题

根据日志中的完成信号和结果更新标题颜色：

| 完成情况 | 标题颜色 | 示例 |
|---------|---------|------|
| 全部正常 | 绿色 `#[fg=green]` | `"Worker1 ✅ 12P/0F"` |
| 有失败/错误 | 红色 `#[fg=red]` | `"Worker1 ❌ 10P/2F"` |
| 有警告/需关注 | 黄色 `#[fg=yellow]` | `"Worker1 ⚠️ 11P/1W"` |

```bash
# 示例：全部通过
tmux select-pane -t ${SESSION}:0.1 -T "Worker1 ✅ ${PASS}P/${FAIL}F"

# 示例：有失败
tmux select-pane -t ${SESSION}:0.1 -T "Worker1 ❌ ${PASS}P/${FAIL}F"
```

**判断逻辑：**
- 全部 PASS → 绿色 ✅
- 任意 FAIL/ERROR → 红色 ❌
- PASS 但有 WARN 或部分命中 → 黄色 ⚠️

同一 Worker pane 可复用：任务完成后直接下发下一个任务，标题随之更新。

---

## 第五步：汇总报告

所有 Worker 完成后输出总表：

```
## 任务汇总

| Worker | 任务 | 状态 | 结果 |
|--------|------|------|------|
| Worker1 | Batch1 | ✅完成 | PASS:10 FAIL:2 |
| Worker2 | Batch2 | ✅完成 | PASS:7 FAIL:0 |
| Worker3 | Retry  | ⚠️完成 | PASS:5 WARN:1 |

总计：PASS:22 FAIL:2 WARN:1 / 25
```

列出所有 FAIL/WARN 项，提示下一步处理方式。关闭 cron（CronDelete），pane 标题保持最终状态。

---

## 注意事项

| 问题 | 处理方式 |
|------|---------|
| 代理污染内网请求 | 脚本开头 `os.environ.pop('HTTPS_PROXY', None)` 清除所有 proxy 变量 |
| API 不支持 blocking 模式 | 改用 streaming 模式，解析 SSE 流 |
| SSE answer 结构不固定 | `isinstance` 判断 dict/list 分别处理 |
| Worker 数量上限 | 4 个，过多 pane 太窄难以阅读 |
| 任务失败重跑 | 向同一 pane 下发新命令，日志文件覆盖 |
| pane 已存在 | 先 `list-panes` 确认，不重复创建 |
| true color 不生效 | 确认终端和 tmux 均已配置 Tc，`/tmux-init` 已处理 |
