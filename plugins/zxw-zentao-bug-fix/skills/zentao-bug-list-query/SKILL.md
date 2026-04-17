---
name: zentao-bug-list-query
description: 当 Codex 需要按条件从禅道查询 bug 列表时使用。该技能只负责查询、筛选和输出候选清单，不执行代码修复。
---

# 禅道 Bug 条件查询

## 目标

这个技能是原子能力，只负责“拉取并整理候选 bug 列表”。

## 输入

最小配置：

- `project_id`
- `human_owner`

查询条件按需提供，例如：

- `status`
- `priority`
- `keyword`
- `assignee`
- `updated_since`
- `limit`

## 执行流程

1. 读取 `./.codex/zentao-bug-fix.yaml`。
2. 确认当前会话可用的 `zentao` MCP 已就绪。
3. 使用 MCP 按条件拉取 bug 列表。
4. 生成候选清单（编号、标题、优先级、状态、更新时间）。
5. 对每个候选给出“是否建议进入修复”的初判。
6. 给出推荐处理顺序和最优先的 1 个候选 bug。

## 边界

- 本技能不修改代码。
- 本技能不回写禅道状态。
- 本技能只输出候选列表和处理建议。

## 输出要求

每次结束必须输出：

- 查询条件
- 命中的 bug 清单
- 每条 bug 的初判（建议修复/建议人工先看/暂不处理）
- 推荐优先级顺序
- 最优先的 1 个 bug 编号
- 下一步建议（可直接交给 `zentao-bug-fix-by-id`）
