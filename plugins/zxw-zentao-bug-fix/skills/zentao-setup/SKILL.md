---
name: zentao-setup
description: 当 Codex 需要初始化当前项目的禅道工作环境时使用。该技能只负责收集项目身份、写入本地配置和确保 zentao MCP 可用，不执行 bug 修复。
---

# 禅道初始化

## 目标

这个技能是原子能力，只负责把当前项目接入禅道工作流：

- 初始化本地 `zentao-mcp`
- 写入当前项目配置
- 记录当前项目的 `project_id` 和 `human_owner`

## 输入

必填：

- `project_id`
- `human_owner`
- `ZENTAO_BASE_URL`
- `ZENTAO_ACCOUNT`
- `ZENTAO_PASSWORD`

字段说明：

- `project_id`：当前 bug 所属的禅道项目 ID，用于定位本项目的 bug 范围。
- `human_owner`：个人姓名，用于拉 bug、确认修复和回写时识别名字。
- `ZENTAO_BASE_URL`：禅道基础地址，默认填写 `http://192.168.4.158:81/zentao/`。
- `ZENTAO_ACCOUNT`：禅道登录账号。
- `ZENTAO_PASSWORD`：禅道登录密码。

## 执行流程

1. 确认当前工作目录是目标项目仓库，而不是插件源码仓库。
2. 首次使用时，必须先运行 `scripts/setup_zentao.py` 或等价初始化命令。
3. 收集并确认禅道连接信息和当前项目身份信息。
4. 把项目配置写入 `./.codex/zentao-bug-fix.yaml`。
5. 把 `zentao` MCP 配置合并进本机 Codex 配置。
6. 确认 `zentao-mcp` 使用的仍然是占位符模板之外的真实本地值。
7. 输出下一步建议：先查询 bug 列表，再按 `bug_id` 进入修复闭环。

## 配置边界

- 仓库里只保留占位符示例，不保存真实账号密码。
- 初始化只改当前项目的 `.codex/zentao-bug-fix.yaml` 和本机 Codex 配置，不改插件核心技能。
- 如果本机已有其他 Codex 配置，必须合并而不是覆盖。
- 如果用户没有显式提供 `ZENTAO_BASE_URL`，优先按默认值 `http://192.168.4.158:81/zentao/` 填写。

## 输出要求

每次结束必须输出：

- `project_id`
- `human_owner`
- `ZENTAO_BASE_URL`
- `ZENTAO_ACCOUNT`
- 是否已写入 `./.codex/zentao-bug-fix.yaml`
- 是否已写入本机 `zentao` MCP 配置
- 下一步建议
