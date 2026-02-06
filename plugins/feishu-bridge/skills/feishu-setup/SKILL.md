---
name: feishu-setup
description: 飞书消息发送服务的交互式配置向导。通过分步引导帮助用户完成飞书应用创建、权限配置、凭证设置和测试验证。
disable-model-invocation: true
---

# 飞书消息发送 - 交互式配置向导

欢迎使用飞书消息发送服务配置向导！本向导将引导你完成飞书应用的创建和配置，完成后即可使用 AI 自动发送飞书通知。

## 配置流程概览

```
步骤 1: 检查依赖环境
   ↓
步骤 2: 创建飞书应用
   ↓
步骤 3: 配置应用权限
   ↓
步骤 4: 获取应用凭证
   ↓
步骤 5: 保存配置
   ↓
步骤 6: 获取接收者 Open ID
   ↓
步骤 7: 测试发送消息
   ↓
✅ 配置完成
```

---

## 开始配置

当用户调用 `/feishu-setup` 时，按照以下步骤引导用户完成配置：

### 步骤 1: 检查依赖环境

首先检查 Python 环境和依赖库：

```bash
# 检查 Python 版本
python3 --version

# 检查 requests 库
python3 -c "import requests; print(f'requests version: {requests.__version__}')" 2>&1 || echo "需要安装 requests 库"
```

**如果缺少依赖**，执行安装：

```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/requirements.txt
```

**向用户确认**：依赖检查完成，准备开始配置飞书应用。

---

### 步骤 2: 创建飞书应用

**引导用户访问飞书开放平台**：

🔗 **飞书开放平台**: https://open.feishu.cn/

**操作步骤**：

1. 登录飞书开放平台（使用你的飞书企业账号）
2. 点击页面上的 **"创建企业自建应用"** 按钮
3. 填写应用信息：
   - **应用名称**: 例如 "Claude Code 通知助手"
   - **应用描述**: 例如 "用于 Claude Code 发送工作通知"
   - **应用图标**: 可选，上传一个图标
4. 点击 **"创建"** 按钮
5. 创建成功后，会自动跳转到应用详情页

**使用 AskUserQuestion 确认**：

```
问题: "是否已成功创建飞书应用？"
选项:
  - "已创建，进入下一步"
  - "遇到问题，需要帮助"
  - "取消配置"
```

如果用户选择"遇到问题"，提供故障排查：
- 确认是否有飞书企业账号（个人账号无法创建企业自建应用）
- 确认是否有创建应用的权限（需要企业管理员权限）
- 提供飞书开放平台文档链接

---

### 步骤 3: 配置应用权限

**引导用户配置权限**：

在应用详情页，找到左侧菜单的 **"权限管理"**：

🔗 **直达链接**: https://open.feishu.cn/app （选择你的应用 → 权限管理）

**需要添加的权限**：

1. 点击 **"添加权限"** 按钮
2. 搜索并添加以下权限：
   - ✅ `im:message` - 获取与发送单聊、群组消息
   - ✅ `im:message:send_as_bot` - 以应用的身份发消息

**重要提示**：
- 添加权限后，权限状态会显示为"待生效"
- 需要在后续步骤中发布应用版本，权限才会生效

**使用 AskUserQuestion 确认**：

```
问题: "是否已添加所需权限？"
选项:
  - "已添加 im:message 和 im:message:send_as_bot"
  - "找不到权限选项"
  - "返回上一步"
```

---

### 步骤 4: 发布应用版本

**引导用户发布应用**：

在应用详情页，找到左侧菜单的 **"版本管理与发布"**：

🔗 **直达链接**: https://open.feishu.cn/app （选择你的应用 → 版本管理与发布）

**操作步骤**：

1. 点击 **"创建版本"** 按钮
2. 填写版本信息：
   - **版本号**: 例如 "1.0.0"
   - **更新说明**: 例如 "初始版本，支持发送通知消息"
3. 点击 **"保存"** 按钮
4. 点击 **"申请发布"** 按钮
5. 选择发布范围：**"全部成员"**
6. 提交审核（企业自建应用通常自动通过）
7. 等待审核通过后，点击 **"发布"** 按钮

**使用 AskUserQuestion 确认**：

```
问题: "应用是否已成功发布？"
选项:
  - "已发布，权限已生效"
  - "审核中，等待通过"
  - "发布失败，需要帮助"
```

如果用户选择"审核中"，告知：企业自建应用通常会自动通过，请稍等片刻后刷新页面查看状态。

---

### 步骤 5: 获取应用凭证

**引导用户获取 App ID 和 App Secret**：

在应用详情页，找到左侧菜单的 **"凭证与基础信息"**：

🔗 **直达链接**: https://open.feishu.cn/app （选择你的应用 → 凭证与基础信息）

**获取凭证**：

1. **App ID**:
   - 在页面中找到 "App ID" 字段
   - 格式为 `cli_xxxxxxxxxx`
   - 点击复制按钮复制

2. **App Secret**:
   - 在页面中找到 "App Secret" 字段
   - 点击 **"查看"** 按钮
   - 复制显示的 Secret（注意保密！）

**使用 AskUserQuestion 获取凭证**：

```
问题: "请提供你的飞书应用凭证"
说明: "请从飞书开放平台的'凭证与基础信息'页面复制以下信息"
输入框:
  - App ID (格式: cli_xxxxxxxxxx)
  - App Secret (保密信息，不会显示在日志中)
```

**验证格式**：
- App ID 必须以 `cli_` 开头
- App Secret 不能为空

---

### 步骤 6: 保存配置

执行以下命令保存配置到配置文件：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py config set \
  --app-id "用户提供的App ID" \
  --app-secret "用户提供的App Secret" \
  --domain "feishu" \
  --recipient-open-id "用户提供的Open ID"
```

**参数说明**：
- `--app-id`: 飞书应用 ID（必需）
- `--app-secret`: 飞书应用密钥（必需）
- `--domain`: 飞书域名，默认 feishu（必需）
- `--recipient-open-id`: 接收者 Open ID（可选，用于钩子自动通知）

**验证配置**：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py config show
```

预期输出：
```
App ID: cli_xxxxxxxxxx
Domain: feishu
Config loaded from: /root/.feishu-bridge/config.json
```

---

### 步骤 7: 获取接收者 Open ID

**引导用户获取 Open ID**：

Open ID 是飞书用户的唯一标识符，格式为 `ou_xxxxxxxxxx`。

**方法：通过 API 调试台获取（推荐）**

🔗 **API 调试台-发送消息**: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create

**操作步骤**：

1. 登录 [API 调试台](https://open.feishu.cn/api-explorer)
2. 找到 [发送消息](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create) 接口
3. 在 **查询参数** 页签，将 **user_id_type** 设置为 **open_id**
4. 点击 **快速复制 open_id** 按钮
5. 在弹窗中，搜索或选择指定用户
6. 点击 **复制成员 ID**，获取用户的 open_id（格式：`ou_xxxxxxxxxx`）

**使用 AskUserQuestion 获取 Open ID**：

```
问题: "请提供接收者的 Open ID"
说明: "从 API 调试台获取，格式为 ou_xxxxxxxxxx"
输入框:
  - Open ID (格式: ou_xxxxxxxxxx)
```

**验证格式**：
- Open ID 必须以 `ou_` 开头
- 长度通常为 34-40 个字符

---

### 步骤 8: 测试发送消息

**发送测试消息**：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py send \
  --to "用户提供的Open ID" \
  --message "🎉 测试消息：Claude Code 飞书通知已配置成功！

✅ 配置信息：
- App ID: [已配置]
- Domain: feishu (中国版)
- 配置方式: [配置文件/环境变量]

现在 AI 可以根据需要自动发送飞书通知了！"
```

**检查结果**：

- ✅ **成功**: 显示 "消息发送成功" 和 Message ID
- ❌ **失败**: 显示错误信息

**使用 AskUserQuestion 确认**：

```
问题: "是否在飞书中收到了测试消息？"
选项:
  - "已收到，配置成功！"
  - "未收到，需要排查问题"
  - "重新发送测试消息"
```

---

### 步骤 9: 配置完成

**显示配置摘要**：

```
🎉 飞书消息发送服务配置完成！

📋 配置摘要：
- App ID: cli_xxxxxxxxxx
- Domain: feishu (中国版)
- 配置方式: [配置文件/环境变量]
- 接收者 Open ID: ou_xxxxxxxxxx
- 测试状态: ✅ 成功

🚀 使用方式：

1. 命令行发送：
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py send \
     --to "ou_xxxxxxxxxx" \
     --message "消息内容"

2. AI 自动调用：
   现在我可以根据你的需求自动发送飞书通知，例如：
   - "代码审查完成后，通过飞书通知我"
   - "部署成功后发送飞书消息"
   - "测试失败时通知我"

3. 自动化钩子（可选）：
   插件提供两个自动化钩子：

   a) Notification Hook - 等待提醒
      当 Claude Code 需要你的交互时自动发送通知
      需要配置: export FEISHU_RECIPIENT_OPEN_ID="ou_xxx"

   b) Stop Hook - 任务完成通知
      当 Claude Code 会话结束时自动发送简单的任务完成通知
      所有配置已包含在配置文件中（recipient_open_id）

   查看钩子状态: /hooks

📚 相关文档：
- 飞书开放平台: https://open.feishu.cn/
- 发送消息 API: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
- 获取 Open ID: https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-obtain-openid
```

---

## 故障排查

### 错误 1: "Failed to get token"

**错误信息**：
```
❌ 发送失败: Failed to get token
```

**原因**：App ID 或 App Secret 错误

**解决方案**：

1. 重新访问飞书开放平台获取正确的凭证：
   🔗 https://open.feishu.cn/app （选择你的应用 → 凭证与基础信息）

2. 检查配置文件或环境变量中的凭证是否正确：
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py config show
   ```

3. 确保 App ID 以 `cli_` 开头，没有多余的空格或引号

4. 重新设置配置：
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py config set \
     --app-id "正确的App ID" \
     --app-secret "正确的App Secret" \
     --domain "feishu"
   ```

---

### 错误 2: "Permission denied"

**错误信息**：
```
❌ 发送失败: Permission denied
```

**原因**：应用缺少必要权限或权限未生效

**解决方案**：

1. 检查权限管理：
   🔗 https://open.feishu.cn/app （选择你的应用 → 权限管理）

2. 确认已添加以下权限：
   - ✅ `im:message`
   - ✅ `im:message:send_as_bot`

3. 检查权限状态：
   - 如果显示"待生效"，需要重新发布应用版本
   - 如果显示"已生效"，等待几分钟后重试

4. 重新发布应用：
   🔗 https://open.feishu.cn/app （选择你的应用 → 版本管理与发布）
   - 创建新版本
   - 申请发布
   - 发布到全部成员

---

### 错误 3: "Invalid receive_id" 或 "id not exist"

**错误信息**：
```
❌ 发送失败: Invalid receive_id
或
❌ 发送失败: id not exist
```

**原因**：Open ID 格式错误或不存在

**解决方案**：

1. 检查 Open ID 格式：
   - ✅ 正确格式：`ou_ec73949642334c539c6a906f6b1438d4`
   - ❌ 错误格式：`c91122gg`（缺少 `ou_` 前缀）

2. 重新从飞书管理后台获取 Open ID：
   🔗 https://feishu.cn/admin
   - 通讯录 → 选择用户 → 查看详情 → 复制 Open ID

3. 确认 Open ID 属于当前企业：
   - Open ID 是企业级的，不同企业的 Open ID 不通用
   - 确保使用的是当前企业的用户 Open ID

4. 确认用户已添加应用：
   - 用户需要在飞书客户端中搜索并添加你的应用
   - 或者管理员在后台为用户开通应用权限

---

### 错误 4: "Network timeout"

**错误信息**：
```
❌ 发送失败: Network timeout
```

**原因**：网络连接问题

**解决方案**：

1. 检查网络连接：
   ```bash
   curl -I https://open.feishu.cn
   ```

2. 确认可以访问飞书开放平台：
   🔗 https://open.feishu.cn/

3. 检查防火墙或代理设置

4. 如果在内网环境，确认可以访问外网

---

## 安全建议

⚠️ **重要安全提示**：

1. **不要提交 App Secret 到代码仓库**
   - App Secret 是敏感信息，泄露后可能被滥用
   - 使用 `.gitignore` 忽略配置文件

2. **使用配置文件或环境变量存储凭证**
   - 配置文件：`~/.feishu-bridge/config.json`
   - 环境变量：`~/.bashrc` 或 `~/.zshrc`

3. **定期更新 App Secret**
   - 建议每 3-6 个月更新一次
   - 在飞书开放平台可以重置 App Secret

4. **最小权限原则**
   - 只添加必要的权限
   - 不要添加不需要的权限

5. **限制应用使用范围**
   - 在版本发布时，可以选择特定部门或用户
   - 避免全员开放（除非必要）

---

## 配置文件位置

- **配置文件**: `~/.feishu-bridge/config.json`
- **CLI 工具**: `${CLAUDE_PLUGIN_ROOT}/scripts/feishu_cli.py`
- **依赖文件**: `${CLAUDE_PLUGIN_ROOT}/requirements.txt`

---

## 相关链接

- 🔗 **飞书开放平台**: https://open.feishu.cn/
- 🔗 **飞书管理后台**: https://feishu.cn/admin
- 🔗 **应用管理**: https://open.feishu.cn/app
- 🔗 **发送消息 API 文档**: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
- 🔗 **获取 tenant_access_token**: https://open.feishu.cn/document/ukTMukTMukTM/ukDNz4SO0MjL5QzM/auth-v3/auth/tenant_access_token_internal
- 🔗 **如何获取 Open ID**: https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-obtain-openid

---

## 技术支持

如果遇到问题，可以：

1. 查看本文档的"故障排查"部分
2. 访问飞书开放平台文档
3. 在飞书开放平台的"工单中心"提交工单
4. 联系企业管理员获取帮助

---

配置完成后，你就可以使用 AI 自动发送飞书通知了！🎉
