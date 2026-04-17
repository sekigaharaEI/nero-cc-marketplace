# 双栈插件开发工作流

本文档面向 code agent，定义本仓库中所有插件的统一开发流程、自检标准和交付要求。

适用范围：
- Claude Code 生态
- Codex 生态
- 本仓库内新增、修改、重构、下线的所有插件

默认目标：
- 同仓库维护一套共享代码和文档
- 同时产出 Claude 和 Codex 两套可发现、可安装、可验证的清单
- 任何平台差异都必须显式声明，不能假装兼容

---

## 1. 基本原则

1. 先判断再实现
   - 先确认插件要解决什么问题
   - 先确认是 Claude-only、Codex-only，还是双栈
   - 先确认哪些能力能共享，哪些必须分平台

2. 共享优先
   - 能复用的内容放在插件根目录
   - 平台相关内容只放在各自的 manifest 或平台专属目录
   - 不要为同一能力复制两套实现，除非平台能力差异迫使如此

3. 清单必须准确
   - Claude 侧使用 `.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json`
   - Codex 侧使用 `.codex-plugin/plugin.json` 和 `.agents/plugins/marketplace.json`
   - 清单内容、版本、描述和路径必须与实际目录一致

4. 不伪造兼容
   - 某个能力只在一个平台可用时，必须明确标注
   - 不要把平台专属功能包装成“都支持”
   - 不要为了统一而写无效清单或空实现

5. 版本同步
   - 同一插件在 Claude 和 Codex 两侧的版本号必须一致
   - README、marketplace、plugin manifest 之间必须同步更新
   - 改版本前先确认是否涉及发布面变化

---

## 2. 平台规范摘要

### 2.1 Claude Code 规范

Claude 侧的仓库级和插件级结构如下：

```text
.claude-plugin/marketplace.json
plugins/<plugin-name>/.claude-plugin/plugin.json
plugins/<plugin-name>/commands/
plugins/<plugin-name>/hooks/
plugins/<plugin-name>/skills/
plugins/<plugin-name>/scripts/
```

Claude 侧常见能力：
- `commands/`
- `hooks/`
- `skills/`
- `scripts/`

### 2.2 Codex 规范

Codex 侧的仓库级和插件级结构如下：

```text
.agents/plugins/marketplace.json
plugins/<plugin-name>/.codex-plugin/plugin.json
plugins/<plugin-name>/skills/
plugins/<plugin-name>/.app.json
plugins/<plugin-name>/.mcp.json
plugins/<plugin-name>/assets/
```

Codex 侧的关键规则：
- 只允许 `plugin.json` 放在 `.codex-plugin/`
- `skills/`、`.app.json`、`.mcp.json`、`assets/` 放在插件根目录
- 仓库级 marketplace 使用 `.agents/plugins/marketplace.json`
- 私人 marketplace 使用 `~/.agents/plugins/marketplace.json`

### 2.3 共享目录建议

优先放在插件根目录并复用的内容：
- `skills/`
- `scripts/`
- `assets/`
- `.mcp.json`
- `.app.json`
- `README.md`

平台专属内容：
- Claude 专属：`commands/`、`hooks/`、`.claude-plugin/`
- Codex 专属：`.codex-plugin/`、`.agents/plugins/marketplace.json`

---

## 3. 标准工作流

### 3.1 需求接收

接到任务后，先输出并确认以下信息：
- 插件名称
- 目标用户
- 主要能力
- 预期平台覆盖范围
- 是否为新增插件、已有插件修改、版本更新、迁移、下线

必须先做的判断：
- 这个插件是否必须双栈
- 哪些能力必须共享
- 哪些能力只能平台专属
- 是否会影响 marketplace、README、manifest、脚本或目录结构

### 3.2 方案拆分

将插件拆成三层：

1. 共享层
   - 核心能力
   - 通用脚本
   - 通用文档
   - 通用资源

2. Claude 层
   - slash commands
   - hooks
   - Claude 专属说明

3. Codex 层
   - Codex manifest
   - Codex marketplace
   - Codex 专属说明

如果某个需求无法自然拆分，先停下来重写边界，不要直接硬写。

### 3.3 目录创建

新插件默认目录模板：

```text
plugins/<plugin-name>/
├── .claude-plugin/
│   └── plugin.json
├── .codex-plugin/
│   └── plugin.json
├── commands/              # 仅 Claude 侧使用，必要时才创建
├── hooks/                 # 仅 Claude 侧使用，必要时才创建
├── skills/                # 双栈共享优先
├── scripts/               # 双栈共享优先
├── assets/                # 双栈共享优先
├── .mcp.json              # 双栈共享优先
├── .app.json              # 双栈共享优先
└── README.md
```

### 3.4 清单编写

必须维护的清单：
- `plugins/<plugin-name>/.claude-plugin/plugin.json`
- `plugins/<plugin-name>/.codex-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`

编写原则：
- 路径必须真实存在
- 相对路径必须从 marketplace 或插件根目录的规范出发
- 名称、版本、描述必须一致
- 平台专属能力必须写入对应平台 manifest 或 README 说明

### 3.5 文档编写

每个插件必须有自己的 `plugins/<plugin-name>/README.md`，至少包括：
- 功能简介
- 支持平台
- 安装方式
- 使用方式
- 配置说明
- 目录结构
- 注意事项

根 `README.md` 还必须同步更新：
- 可用插件列表
- 插件详情
- 平台支持说明

### 3.6 版本同步

如果插件版本发生变化，至少同步以下文件：
- `plugins/<plugin-name>/.claude-plugin/plugin.json`
- `plugins/<plugin-name>/.codex-plugin/plugin.json`
- `plugins/<plugin-name>/README.md`
- `README.md`
- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`

同步要求：
- 同一插件的版本号必须完全一致
- 如果平台支持范围变化，也要同步更新描述和安装说明
- 如果只有文档变化但没有代码变化，也要确认是否需要版本号变化

---

## 4. 不同变更类型的流程

### 4.1 新增插件

步骤：
1. 定义插件目标和平台范围
2. 拆分共享层与平台层
3. 创建插件目录
4. 创建两个 manifest
5. 实现共享脚本、技能、资源
6. 如需要，补 Claude 命令和 hook
7. 注册到两个 marketplace
8. 写插件 README
9. 更新根 README
10. 做双栈自检

### 4.2 修改已有插件

步骤：
1. 判断是否影响共享逻辑
2. 判断是否影响平台清单
3. 判断是否影响文档和版本号
4. 先改共享层，再改平台层
5. 同步更新两个 marketplace
6. 跑验证清单

### 4.3 版本升级

步骤：
1. 确认升级理由
2. 统一更新版本号
3. 检查 README 中是否提到旧版本
4. 检查 marketplace 是否反映新版本
5. 检查平台专属能力说明是否失效

### 4.4 平台能力新增

步骤：
1. 判断这个能力属于 Claude、Codex 还是共享
2. 只改对应平台的实现和清单
3. 明确写出另一平台是否不支持
4. 不要为了“看起来双栈”而塞空壳

### 4.5 插件下线或废弃

步骤：
1. 先标记废弃原因和替代方案
2. 从两个 marketplace 移除或降级可见性
3. 更新 README 标记 deprecated
4. 保留必要的兼容说明和迁移指引

---

## 5. 验证要求

### 5.1 结构验证

检查：
- 目录是否与 manifest 一致
- `.claude-plugin/plugin.json` 是否存在
- `.codex-plugin/plugin.json` 是否存在
- 需要的平台目录是否存在
- 共享资源是否放在插件根目录

### 5.2 清单验证

检查：
- marketplace 里是否注册了正确路径
- manifest 里的路径是否以 `./` 开头
- manifest 引用的文件是否真实存在
- 版本号是否一致
- 描述是否与 README 一致

### 5.3 功能验证

Claude 侧至少验证：
- marketplace 可见
- 插件可安装
- command 可执行
- hook 可触发
- 依赖文件路径正确

Codex 侧至少验证：
- repo marketplace 可识别
- plugin 可安装或可加载
- `skills/` 可见
- `.mcp.json` / `.app.json` 路径正确
- 需要的资源文件可访问

### 5.4 文档验证

检查：
- 根 README 是否更新
- 插件 README 是否更新
- 平台支持范围是否明确
- 安装命令是否正确
- 示例是否仍然有效

---

## 6. code agent 自检清单

提交前逐项确认：

### 6.1 设计层
- [ ] 已确认插件目标和平台范围
- [ ] 已区分共享层、Claude 层、Codex 层
- [ ] 已避免无意义的双份实现
- [ ] 已标记平台不对等能力

### 6.2 目录层
- [ ] 插件目录结构正确
- [ ] `.claude-plugin/plugin.json` 存在
- [ ] `.codex-plugin/plugin.json` 存在
- [ ] 共享资源放在插件根目录
- [ ] 平台专属目录没有互相污染

### 6.3 清单层
- [ ] `.claude-plugin/marketplace.json` 已更新
- [ ] `.agents/plugins/marketplace.json` 已更新
- [ ] 两侧 plugin manifest 内容一致或差异已显式说明
- [ ] 路径都能解析到真实文件
- [ ] 版本号一致

### 6.4 文档层
- [ ] 插件 README 已更新
- [ ] 根 README 已更新
- [ ] 安装方法已分别说明 Claude 和 Codex
- [ ] 支持范围已写清楚
- [ ] 版本号和功能描述一致

### 6.5 验证层
- [ ] Claude 安装验证通过
- [ ] Claude 命令或 hook 验证通过
- [ ] Codex 侧安装或加载验证通过
- [ ] Codex skills / app / MCP 相关验证通过
- [ ] 没有残留失效路径

### 6.6 发布层
- [ ] 是否需要版本号递增已确认
- [ ] 是否需要变更日志已确认
- [ ] 是否需要迁移说明已确认
- [ ] 是否需要回滚方案已确认

---

## 7. 常见错误

1. 只改 Claude，不改 Codex
   - 结果：仓库看起来同步，实际只能在一个生态工作

2. 把 manifest 写错位置
   - Claude 用 `.claude-plugin/plugin.json`
   - Codex 用 `.codex-plugin/plugin.json`
   - Codex marketplace 用 `.agents/plugins/marketplace.json`

3. 把平台专属功能写成通用能力
   - 例如把 Claude command 说成 Codex 也能直接调用

4. 版本号不同步
   - README、marketplace、manifest 显示不同版本

5. 路径引用错误
   - manifest 引用了不存在的文件
   - 相对路径没有从正确根目录解析

6. 文档和实现脱节
   - README 写了功能，但 manifest 或目录里根本没有

---

## 8. 推荐执行顺序

对于任何插件工作，默认按下面顺序执行：

1. 读 `CLAUDE.md`
2. 读本文件
3. 读插件 `README.md`
4. 读 Claude 和 Codex manifest
5. 判定平台范围
6. 设计目录和共享层
7. 实现
8. 同步清单
9. 更新文档
10. 跑自检清单

---

## 9. 参考规范

- Claude Code 插件市场规范
- Codex 插件规范
- Codex skills 规范
- 仓库现有 `CLAUDE.md`

Codex 官方插件文档可参考：
- https://developers.openai.com/codex/plugins
- https://developers.openai.com/codex/plugins/build
- https://developers.openai.com/codex/use-cases/reusable-codex-skills

