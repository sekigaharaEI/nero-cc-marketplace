# Claude Code 会话文件 (JSONL) 结构分析

## 文件格式概述

Claude Code 的会话历史文件采用 **JSONL (JSON Lines)** 格式，每行是一个独立的 JSON 对象，记录会话中的各种事件和消息。

---

## 消息类型 (type 字段)

文件中包含以下几种主要消息类型：

| type 值 | 说明 |
|---------|------|
| `queue-operation` | 队列操作事件，标记消息处理的开始 |
| `file-history-snapshot` | 文件历史快照，记录文件备份状态 |
| `user` | 用户发送的消息 |
| `assistant` | AI 助手的回复 |
| `system` | 系统消息（如压缩边界标记） |

---

## 各类型消息的字段详解

### 1. queue-operation (队列操作)

```json
{
  "type": "queue-operation",
  "operation": "dequeue",
  "timestamp": "2026-02-03T05:39:09.274Z",
  "sessionId": "6cd4a4af-0dc4-41f6-8adc-0d49658805ac"
}
```

| 字段 | 作用 |
|------|------|
| `type` | 消息类型标识 |
| `operation` | 操作类型，`dequeue` 表示从队列中取出消息进行处理 |
| `timestamp` | 操作发生的时间戳 (ISO 8601 格式) |
| `sessionId` | 会话唯一标识符 (UUID) |

---

### 2. file-history-snapshot (文件历史快照)

```json
{
  "type": "file-history-snapshot",
  "messageId": "46016bab-1fdf-47ff-bbaa-a90800cd2a83",
  "snapshot": {
    "messageId": "46016bab-1fdf-47ff-bbaa-a90800cd2a83",
    "trackedFileBackups": {},
    "timestamp": "2026-02-03T05:39:09.337Z"
  },
  "isSnapshotUpdate": false
}
```

| 字段 | 作用 |
|------|------|
| `type` | 消息类型标识 |
| `messageId` | 关联的消息 ID |
| `snapshot.trackedFileBackups` | 被追踪文件的备份记录（用于撤销操作） |
| `snapshot.timestamp` | 快照创建时间 |
| `isSnapshotUpdate` | 是否为快照更新（false 表示新快照） |

---

### 3. user (用户消息)

```json
{
  "parentUuid": "a30b1905-c254-4139-862e-b886ef0fd124",
  "isSidechain": false,
  "userType": "external",
  "cwd": "z:\\project\\AI-查云威测试",
  "sessionId": "6cd4a4af-0dc4-41f6-8adc-0d49658805ac",
  "version": "2.1.29",
  "gitBranch": "",
  "type": "user",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "用户输入的内容"}]
  },
  "uuid": "d837d8af-c880-406d-9f3f-2af08d08562e",
  "timestamp": "2026-02-03T05:40:11.378Z",
  "permissionMode": "acceptEdits"
}
```

| 字段 | 作用 |
|------|------|
| `parentUuid` | 父消息的 UUID，用于构建对话链（首条消息为 `null`） |
| `isSidechain` | 是否为侧链消息（分支对话） |
| `userType` | 用户类型，`external` 表示外部用户 |
| `cwd` | 当前工作目录 |
| `sessionId` | 会话 ID |
| `version` | Claude Code 版本号 |
| `gitBranch` | 当前 Git 分支（空字符串表示无分支或非 Git 仓库） |
| `type` | 消息类型 |
| `message.role` | 消息角色 (`user`) |
| `message.content` | 消息内容数组，支持多种内容类型 |
| `uuid` | 消息唯一标识符 |
| `timestamp` | 消息时间戳 |
| `permissionMode` | 权限模式，`acceptEdits` 表示接受编辑操作 |

---

### 4. assistant (助手回复)

```json
{
  "parentUuid": "d837d8af-c880-406d-9f3f-2af08d08562e",
  "isSidechain": false,
  "userType": "external",
  "cwd": "z:\\project\\AI-查云威测试",
  "sessionId": "6cd4a4af-0dc4-41f6-8adc-0d49658805ac",
  "version": "2.1.29",
  "gitBranch": "",
  "message": {
    "content": [
      {"thinking": "思考过程...", "type": "thinking", "signature": ""},
      {"text": "回复内容...", "type": "text"}
    ],
    "id": "msg_5ef4afb495934ac290e2a4d7d72f1f76",
    "model": "claude-opus-4-5-20251101",
    "role": "assistant",
    "stop_reason": null,
    "stop_sequence": null,
    "type": "message",
    "usage": {
      "cache_creation": {...},
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0,
      "input_tokens": 24274,
      "output_tokens": 0,
      "service_tier": "standard"
    }
  },
  "type": "assistant",
  "uuid": "7c725e4f-738e-4a37-b980-3b9548ff58f4",
  "timestamp": "2026-02-03T05:40:17.377Z"
}
```

| 字段 | 作用 |
|------|------|
| `message.content` | 回复内容数组，可包含 `thinking`（思考）和 `text`（文本）类型 |
| `message.id` | API 返回的消息 ID |
| `message.model` | 使用的模型名称 |
| `message.role` | 消息角色 (`assistant`) |
| `message.stop_reason` | 停止原因 |
| `message.usage` | Token 使用统计 |
| `message.usage.input_tokens` | 输入 token 数量 |
| `message.usage.output_tokens` | 输出 token 数量 |
| `message.usage.service_tier` | 服务层级 |

---

## 对话压缩标识 (Compact Boundary)

### 如何识别对话压缩

当对话上下文过长时，Claude Code 会进行压缩。**压缩的标识是 `type: "system"` 且 `subtype: "compact_boundary"` 的消息**：

```json
{
  "parentUuid": null,
  "logicalParentUuid": "39f88e26-0298-4a3e-b807-d42a5cf0d1fb",
  "isSidechain": false,
  "userType": "external",
  "cwd": "z:\\project\\AI-查云威测试",
  "sessionId": "6cd4a4af-0dc4-41f6-8adc-0d49658805ac",
  "version": "2.1.29",
  "gitBranch": "",
  "slug": "reactive-imagining-pony",
  "type": "system",
  "subtype": "compact_boundary",
  "content": "Conversation compacted",
  "isMeta": false,
  "timestamp": "2026-02-03T06:03:18.325Z",
  "uuid": "b13e200f-40f2-46af-bb44-ce8fb44260cc",
  "level": "info",
  "compactMetadata": {
    "trigger": "manual",
    "preTokens": 26027
  }
}
```

### 压缩相关的关键字段

| 字段 | 作用 |
|------|------|
| `type: "system"` | 系统消息类型 |
| `subtype: "compact_boundary"` | **压缩边界标识** - 这是识别压缩的关键 |
| `content: "Conversation compacted"` | 压缩说明文本 |
| `logicalParentUuid` | 逻辑上的父消息 UUID（压缩前的最后一条消息） |
| `parentUuid: null` | 物理父消息为空（因为压缩后重新开始） |
| `compactMetadata.trigger` | 压缩触发方式：`manual`（手动）或 `auto`（自动） |
| `compactMetadata.preTokens` | 压缩前的 token 数量 |
| `slug` | 会话的可读标识符 |

---

### 压缩后的摘要消息

压缩边界后紧跟一条包含对话摘要的用户消息：

```json
{
  "parentUuid": "b13e200f-40f2-46af-bb44-ce8fb44260cc",
  "type": "user",
  "message": {
    "role": "user",
    "content": "This session is being continued from a previous conversation..."
  },
  "isVisibleInTranscriptOnly": true,
  "isCompactSummary": true,
  "uuid": "2e1c3044-0784-4522-b151-d69554638718"
}
```

| 字段 | 作用 |
|------|------|
| `isCompactSummary: true` | **标识这是压缩摘要消息** |
| `isVisibleInTranscriptOnly: true` | 仅在记录中可见，不显示给用户 |
| `message.content` | 包含之前对话的完整摘要 |

---

## 其他特殊消息类型

### 元消息 (isMeta: true)

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "<local-command-caveat>...</local-command-caveat>"
  },
  "isMeta": true
}
```

`isMeta: true` 表示这是元数据消息，通常用于标记本地命令的上下文。

### 命令消息

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "<command-name>/compact</command-name>..."
  }
}
```

包含 `<command-name>` 标签的消息表示用户执行了斜杠命令。

---

## 消息链结构

消息通过 `parentUuid` 和 `uuid` 形成链式结构：

```
用户消息 A (uuid: "aaa", parentUuid: null)
    ↓
助手回复 B (uuid: "bbb", parentUuid: "aaa")
    ↓
用户消息 C (uuid: "ccc", parentUuid: "bbb")
    ↓
助手回复 D (uuid: "ddd", parentUuid: "ccc")
```

---

## 总结

| 识别目标 | 关键字段/值 |
|----------|-------------|
| 对话压缩发生 | `type: "system"` + `subtype: "compact_boundary"` |
| 压缩摘要内容 | `isCompactSummary: true` |
| 压缩触发方式 | `compactMetadata.trigger` (`manual` 或 `auto`) |
| 压缩前 token 数 | `compactMetadata.preTokens` |
| 消息父子关系 | `parentUuid` 指向前一条消息的 `uuid` |
| AI 思考过程 | `message.content` 中 `type: "thinking"` 的条目 |
| Token 使用量 | `message.usage.input_tokens` / `output_tokens` |
