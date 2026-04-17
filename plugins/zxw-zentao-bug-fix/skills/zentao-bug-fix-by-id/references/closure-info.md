# 闭环信息

要让一个 bug 从拉取、修复到回写真正闭环，至少需要这些信息。

## 必填信息

- `project_id`
- `human_owner`
- `bug_id` 或本次筛选条件
- `should_fix`
- `verification_level`
- `verification_status`
- `human_confirmation`
- `zentao_target_status`

## 推荐补充信息

- 问题摘要
- 已确认根因
- 修改文件
- 关键改动
- 测试结果
- 风险点
- 需要人工确认的项
- 是否需要延后修复

## 人工确认要点

人工确认时至少确认这三件事：

1. 这个问题是否真的要修
2. 修复方案是否接受
3. 验证结果是否足以回写禅道

## 回写前检查

- 是否已生成修复清单
- 是否已确认修复清单
- 是否已选定回写状态
- 是否已明确下一步
