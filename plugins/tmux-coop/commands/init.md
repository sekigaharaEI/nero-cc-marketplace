# tmux-coop 初始化向导

检测 tmux 环境并引导用户完成 tmux-coop 插件的配置安装。

## 执行步骤

### 1. 检测 tmux 是否安装

```bash
command -v tmux && tmux -V
```

若未安装，展示安装指引后终止：

```
tmux 未安装。请先安装：
  - Ubuntu/Debian: sudo apt install tmux
  - macOS:         brew install tmux
  - CentOS/RHEL:   sudo yum install tmux
```

### 2. 运行配置安装脚本

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup_tmux.sh" --plugin-root "${CLAUDE_PLUGIN_ROOT}"
```

根据脚本输出的 JSON 结果判断：

- `ok: true` → 继续下一步
- `ok: false` → 展示 `error` 和 `hint` 字段内容，引导用户修复后重试

### 3. 展示安装结果

```
## tmux-coop 配置安装结果

| 检测项        | 状态 | 说明                      |
|--------------|------|---------------------------|
| tmux 版本    | ✅   | {tmux_version}            |
| 配置文件     | ✅   | 已安装到 ~/.tmux.conf     |
| 热加载       | ✅/⏭ | 在 tmux 中已热加载 / 下次启动生效 |
```

### 4. 展示使用指南

```
## tmux-coop 已就绪！

### 前缀键
默认前缀键已改为 Ctrl+s（原为 Ctrl+b）

### 可用命令

| 命令           | 说明                                   |
|---------------|----------------------------------------|
| /tmux-layout  | 建立/复用三栏协作布局（左 Claude 60%，右上长程任务，右下 Codex） |
| /tmux-init    | 重新运行初始化向导                      |

### 自动触发
安装后，以下场景 Claude 会自动使用 tmux 布局：
- 执行长程命令（构建/测试/服务启动）
- 启动 subagent
- 调用 Codex
```

### 5. 询问后续操作

使用 AskUserQuestion 询问用户：

```
初始化完成！是否现在就建立三栏工作布局？
```

选项：
- **立即建立布局**：执行 `/tmux-layout` 命令
- **稍后手动建立**：结束向导
