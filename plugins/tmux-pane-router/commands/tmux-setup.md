# /tmux-setup

在当前 tmux session 中创建三分屏布局，并保存 pane 配置供 Hook 使用。

## 用法

```
/tmux-setup
```

## 执行步骤

当用户运行 `/tmux-setup` 时，你需要：

1. 运行布局脚本：
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup_layout.sh"
   ```

2. 将脚本输出完整展示给用户

3. 提示用户：Hook 已自动配置，后续所有 Bash 命令将在右上 pane 执行，Agent 启动信息将显示在右下 pane

## 前提条件

- 必须在 tmux session 内运行 Claude Code
- 如需在 tmux 外启动，请先运行：
  ```bash
  bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup_layout.sh" --new
  ```
  这会创建新的 `claude-code` tmux session 并自动进入

## 说明

布局创建后，pane ID 保存在 `~/.claude/tmux-pane-router.conf`。
插件 Hook 读取此配置文件来确定目标 pane。
