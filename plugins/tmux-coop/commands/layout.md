# 建立 tmux 三栏协作布局

手动触发三栏工作布局的建立或复用。等同于触发 `tmux-layout` skill。

## 执行步骤

直接执行 `tmux-layout` skill 的完整流程：

1. 检查是否在 tmux 中（`$TMUX` 非空）
2. 检查布局是否已存在（复用优先）
3. 若不存在则建立三栏布局
4. 返回各 pane ID

详见 skill 定义：`skills/tmux-layout/SKILL.md`
