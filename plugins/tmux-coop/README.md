# tmux-coop

**Tmux 协作指挥官** — 基于 tmux 的多智能体协作布局插件。内置 tmux 配置、三栏分工布局与任务自动路由，让 Claude 主流程、长程任务、Codex 各司其职。

## 功能特性

- **一键初始化**：自动安装 tmux 配置、备份原有配置、热加载
- **三栏协作布局**：左侧 Claude 主流程（60%）、右上长程任务、右下 Codex 专用
- **自动任务路由**：长程命令、subagent、Codex 调用自动路由到对应 pane
- **布局复用**：已有布局自动识别复用，不重复创建
- **可扩展**：后续支持更多协作模式（如 dispatcher+worker）

## 安装

```bash
/plugin install tmux-coop@nero-cc-marketplace
```

## 使用

### 初始化（首次使用）

```
/tmux-init
```

运行初始化向导：检测 tmux 版本、安装配置文件、展示使用指南。

### 手动建立布局

```
/tmux-layout
```

在当前 tmux window 中建立或复用三栏协作布局。

### 布局结构

```
┌─────────────────────┬──────────────┐
│                     │  右上 Pane B  │
│  左 Claude 主流程    │  长程任务     │
│     (约 60% 宽)     ├──────────────┤
│                     │  右下 Pane C  │
│                     │  Codex 专用  │
└─────────────────────┴──────────────┘
```

### 自动触发

安装后，以下场景 Claude 会自动确保布局存在并路由任务：

| 触发条件 | 路由目标 |
|---------|---------|
| 长程命令（构建/测试/服务启动） | 右上 Pane B |
| 写超长文本（> 3000字） | 右上 Pane B |
| 启动 subagent | 右上 Pane B |
| 调用 Codex | 右下 Pane C（淡蓝文字 + 标题自动更新） |
| 需要并行执行多个子任务 | parallel-dispatch 多 Worker 布局 |

## 配置说明

### tmux 配置

插件内置 tmux 配置（`configs/tmux.conf`），安装后覆盖 `~/.tmux.conf`：

- 前缀键：`Ctrl+s`（替代默认的 `Ctrl+b`）
- Pane 标题显示：顶部边框，Claude 橙色、Codex 蓝色
- 鼠标支持已开启
- 关闭自动重命名（保持 pane 标题稳定）

## Skills

| Skill | 触发时机 |
|-------|---------|
| `tmux-layout` | 自动：长程命令/subagent/Codex 调用前；手动：`/tmux-layout` |
| `codex-exec` | 自动：用户说「实现/写一个/重构」时；在 tmux pane 中执行，淡蓝文字 + 标题 `codex-<简述>` |
| `claude-exec` | 自动：需要 Claude 推理能力的编码任务；在 tmux pane 中执行，橙色文字 + 标题 `claude-<简述>` |
| `parallel-dispatch` | 自动：需要并行执行多个独立子任务时；支持 Shell/Codex/Claude 三种执行器 |

## 版本历史

- `v1.0.0` - 基础原子能力：tmux 配置安装、手动布局建立、自动任务路由、Codex 联动、并行调度
