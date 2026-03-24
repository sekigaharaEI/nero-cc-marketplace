# /tmux-status

查看 tmux-pane-router 的当前配置状态。

## 用法

```
/tmux-status
```

## 执行步骤

当用户运行 `/tmux-status` 时，你需要：

1. 读取配置文件：
   ```bash
   cat ~/.claude/tmux-pane-router.conf 2>/dev/null || echo "配置文件不存在，请先运行 /tmux-setup"
   ```

2. 检查各 pane 是否存活：
   ```bash
   tmux list-panes -a -F "#{pane_id} #{window_name} #{pane_title}" 2>/dev/null
   ```

3. 综合展示状态：
   - 配置文件中的 pane ID
   - 各 pane 当前是否存在
   - Hook 是否已安装（检查 hooks.json 是否存在于插件目录）

4. 如果发现配置与实际 pane 不符，建议用户重新运行 `/tmux-setup`
