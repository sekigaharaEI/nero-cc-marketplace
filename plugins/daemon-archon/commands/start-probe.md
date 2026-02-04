# /start-probe

启动 Probe 模式任务

## 用法

```
/start-probe <task_description>
```

## 参数

- `task_description`: 任务描述/初始提示词

## 说明

启动一个 Probe 模式任务。Probe 是一个持续运行的 Claude Code CLI 会话，Archon 会定时检查其状态并在需要时进行纠偏。

**适用场景**：
- 代码重构
- 长期开发任务
- 需要 Claude Code 持续执行的任务

## 工作流程

1. 创建任务目录和配置文件
2. 后台启动 Claude Code CLI（Probe）
3. 注册定时检查任务到 Archon 调度器
4. Archon 定时分析 Probe 的 transcript，判断状态
5. 如有问题，自动纠偏或通知用户

## 实现

当用户执行 `/start-probe` 时，Claude Code 应该：

1. 确保 Archon 服务正在运行
2. 生成任务 ID（格式：`YYYYMMDD_HHMMSS_probe`）
3. 调用 Archon API 创建 Probe 任务

```bash
# 检查 Archon 服务
if ! curl -s http://127.0.0.1:8765/status > /dev/null 2>&1; then
    echo "请先启动 Archon 服务: /archon-start"
    exit 1
fi

# 创建 Probe 任务
curl -X POST http://127.0.0.1:8765/probe/create \
    -H "Content-Type: application/json" \
    -d '{
        "initial_prompt": "<task_description>",
        "project_path": "<current_project_path>",
        "name": "Probe 任务",
        "check_interval_minutes": 5,
        "max_auto_corrections": 3
    }'
```

## 示例

```bash
# 启动代码重构任务
/start-probe 请重构 src/legacy 目录，将旧代码迁移到新架构

# 启动测试修复任务
/start-probe 修复所有失败的单元测试，确保测试覆盖率达到 80%

# 查看任务状态
/list-tasks
```

## 相关命令

- `/stop-probe <task_id>` - 停止 Probe 任务
- `/check-task <task_id>` - 手动检查任务状态
- `/list-tasks` - 列出所有任务
