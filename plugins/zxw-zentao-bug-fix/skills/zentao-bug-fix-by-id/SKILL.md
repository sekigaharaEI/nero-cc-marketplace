---
name: zentao-bug-fix-by-id
description: 当 Codex 需要根据 bug_id 处理单个禅道 bug 时使用。该技能负责单 bug 的读取、确认、修复、验证、修复清单和回写闭环。
---

# 禅道单 Bug 修复

## 目标

这个技能是原子能力，只处理一个已明确的 `bug_id`，并完成从确认到回写的闭环。

## 输入

必填：

- `bug_id`

建议：

- `project_id`
- `human_owner`

## 执行流程

1. 读取 `./.codex/zentao-bug-fix.yaml`。
2. 读取 bug 详情和必要上下文。
3. 输出问题摘要、已知事实、无法确认的点和是否建议修复。
4. 等待用户明确确认“要改”后，再进入代码修改。
5. 修改代码并补最小必要测试。
6. 按风险和问题类型选择验证层级，执行静态检查、单测、集成测试或设备验证。
7. 生成修复清单。
8. 人工确认修复清单后，再回写禅道。

## 停机条件

命中任一条件，停止自动修复并转人工：

- 需求或预期行为不清晰
- 根因不唯一且影响修复方案选择
- 涉及权限、支付、鉴权、数据迁移等高风险改动
- 验证结果无法证明修复有效

## 核心原则

- 机器只处理能确认的部分。
- 不能确认时，不猜，不硬改。
- 修复前必须先得到用户对“要改”的确认。
- 修复后必须先给出修复清单，再等待人工确认。
- 只有确认后才回写禅道。

## 修复清单

修复完成后，先输出一份清单给人确认，至少包含：

- bug 编号
- 问题摘要
- 已确认根因
- 是否建议修复
- 用户确认结果
- 验证层级
- 验证结果
- 修改文件
- 关键改动
- 测试结果
- 风险点
- 需要人工确认的项目
- 建议回写状态

## 验证策略

修复后不要只说“测试过了”，要明确验证层级。

### 验证层级

1. `static`
- lint
- typecheck
- format
- 基础编译

2. `unit`
- 纯逻辑
- 工具函数
- 边界条件
- 回归最小化验证

3. `integration`
- 接口联动
- 数据库
- 缓存
- 服务交互

4. `e2e`
- 页面交互
- 用户路径
- 路由跳转
- 表单提交

5. `mobile_device`
- 真机
- 模拟器
- 原生构建
- WebView
- 桥接
- 权限
- 音视频

6. `manual_only`
- 环境无法自动化
- 需要人工打开设备或后台确认

### 验证结果

每次修复清单都必须写清楚：

- `verification_level`
- `verification_status`

其中：

- `passed`
- `partial`
- `blocked`
- `needs_human`

## 项目配置

项目配置只保留最小必填项：

- `project_id`
- `human_owner`

更完整的闭环信息见 [closure-info.md](references/closure-info.md)。

## 风险闸门

精确判定规则见参考文件：

- [risk-gates.md](references/risk-gates.md)
- [status-flow.md](references/status-flow.md)

## 输出要求

每次结束必须输出：

- `bug_id`
- `should_fix`
- `human_confirmation`
- `zentao_target_status`
- 当前已知事实
- 无法确认的点
- 当前最可能的处理方向
- `verification_level`
- `verification_status`
- 修改文件清单
- 风险点
- 是否允许回写禅道
