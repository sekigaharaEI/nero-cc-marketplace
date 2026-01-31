---
description: 迁移 Claude Skills 到 Agent Workflows
---

## 触发条件

当用户需要以下任务时触发此Workflow：
- "迁移skills到workflows"
- "把skills转换成workflows格式"
- "同步skills到agent目录"
- 用户提到需要将 `.claude/skills` 迁移到 `.agent/workflows`

---

本 Workflow 用于将 `.\.claude\skills` 目录下的技能文件批量迁移并转换为 `.agent/workflows` 格式。

### 1. 扫描技能目录
- 查找 `.\.claude\skills` 下的所有子文件夹。
- 每一个文件夹代表一个 Skill（例如 `write-long-text`）。

### 2. 读取与转换
- 对于每一个 Folder (假设名为 `[SkillName]`)：
    1. 读取 `.\claude\skills\[SkillName]\SKILL.md` 的内容。
    2. 检查内容是否包含 YAML frontmatter (即 `--- description: ... ---`)。如果没有，建议自动添加头部。

### 3. 写入工作流
- 将读取到的内容生成一个新文件到新位置：
    `.\.agent\workflows\[SkillName].md`
- 如果改地址已存在该文件，则跳过该skill

### 4. 验证与清理
- 确认文件已生成。

// turbo-all