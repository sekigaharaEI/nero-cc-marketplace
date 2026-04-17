# 状态流转

使用尽量窄的流程，保证 bug 全程可审计。

## 建议状态

1. `new`
2. `triaged`
3. `needs_fix_confirmation`
4. `in_progress`
5. `needs_info`
6. `needs_human`
7. `needs_confirmation`
8. `needs_review`
9. `fixed`
10. `verified`
11. `closed`

## 流转规则

- `triaged`：完成摘要和风险初判后进入。
- `needs_info`：复现方式或预期行为不清楚时进入。
- `needs_human`：机器无法确认根因、修复方向或风险边界时进入。
- `needs_fix_confirmation`：候选 bug 已识别，但还没确认是否要修时进入。单 bug 手动处理必须先停在这里，等待用户明确确认“要改”后才能进入 `in_progress`。
- `needs_confirmation`：代码已修复，但还没有人工确认修复清单时进入。
- `needs_review`：修复已完成，但还需要人工最终确认或补充复核时进入。
- `in_progress`：通过风险闸门后才能进入。
- `verified`：本地或 CI 等价检查成功后才能进入。
- `closed`：经过人工 review 或明确批准的自动化策略后才能进入。

## 进入条件

- 当机器已经识别出候选 bug，但还没决定是否修复时，进入 `needs_fix_confirmation`。
- 当修复已完成，但清单还没被人确认时，进入 `needs_confirmation`。
- 当修复方向已确认，但验证结果不完整时，进入 `needs_review`。

## 修复清单模板

修复完成后，先输出一份清单给人确认，至少包含：

- bug 编号
- 问题摘要
- 已确认根因
- 是否建议修复
- 验证层级
- 验证结果
- 修改文件
- 关键改动
- 测试结果
- 风险点
- 需要人工确认的项目

## 禅道评论模板

评论尽量简短，并包含以下字段：

- 摘要
- 已知事实
- 无法确认的点
- 根因
- 修复
- 验证
- 风险
- 下一步
