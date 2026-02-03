# OpenClaw Memory 系统深度分析

## 一、系统概述

Memory 系统是 OpenClaw 的核心组件之一，实现了一个**基于向量嵌入的语义搜索系统**。它允许代理（Agent）存储和检索长期记忆，支持从 Markdown 文件和会话历史中进行语义搜索。

### 1.1 核心功能

- **语义搜索**：基于向量嵌入的相似度搜索
- **混合搜索**：结合向量搜索和 BM25 关键词搜索
- **增量索引**：只索引变更的文件，避免重复计算
- **多源支持**：支持 memory 文件和 session 会话记录
- **多嵌入提供者**：支持 OpenAI、Gemini、本地模型

### 1.2 目录结构

```
src/memory/
├── manager.ts           # 核心管理器类
├── memory-schema.ts     # SQLite 数据库 schema
├── internal.ts          # 文件发现、Markdown 分块
├── session-files.ts     # 会话文件提取
├── embeddings.ts        # 嵌入提供者抽象
├── embeddings-openai.ts # OpenAI 嵌入实现
├── embeddings-gemini.ts # Gemini 嵌入实现
├── batch-openai.ts      # OpenAI 批量 API
├── batch-gemini.ts      # Gemini 批量 API
├── hybrid.ts            # 混合搜索算法
└── manager-search.ts    # 搜索查询实现
```

---

## 二、数据结构与类型定义

### 2.1 核心类型

**文件**: `src/memory/internal.ts`

```typescript
// 记忆文件条目
export type MemoryFileEntry = {
  path: string;       // 相对路径（相对于工作目录）
  absPath: string;    // 绝对路径
  mtimeMs: number;    // 文件修改时间戳
  size: number;       // 文件大小（字节）
  hash: string;       // 文件内容的 SHA256 哈希
};

// 文本块
export type MemoryChunk = {
  startLine: number;  // 块起始行号
  endLine: number;    // 块结束行号
  text: string;       // 块文本内容
  hash: string;       // 块内容的 SHA256 哈希
};
```

### 2.2 搜索结果类型

**文件**: `src/memory/manager.ts`

```typescript
type MemorySource = "memory" | "sessions";

export type MemorySearchResult = {
  path: string;        // 文件路径
  startLine: number;   // 匹配块起始行
  endLine: number;     // 匹配块结束行
  score: number;       // 相似度分数 (0-1)
  snippet: string;     // 匹配的文本片段
  source: MemorySource; // 来源类型
};
```

### 2.3 索引元数据

```typescript
type MemoryIndexMeta = {
  model: string;        // 嵌入模型名称
  provider: string;     // 嵌入提供者
  providerKey?: string; // 提供者密钥标识
  chunkTokens: number;  // 每块 token 数
  chunkOverlap: number; // 块重叠 token 数
  vectorDims?: number;  // 向量维度
};
```

### 2.4 会话文件条目

**文件**: `src/memory/session-files.ts`

```typescript
type SessionFileEntry = {
  path: string;     // 相对路径
  absPath: string;  // 绝对路径
  mtimeMs: number;  // 修改时间
  size: number;     // 文件大小
  hash: string;     // 内容哈希
  content: string;  // 提取的文本内容
};
```

---

## 三、配置系统

### 3.1 完整配置类型

**文件**: `src/agents/memory-search.ts`

```typescript
export type ResolvedMemorySearchConfig = {
  enabled: boolean;                              // 是否启用
  sources: Array<"memory" | "sessions">;         // 数据源
  extraPaths: string[];                          // 额外搜索路径
  provider: "openai" | "local" | "gemini" | "auto"; // 嵌入提供者

  // 远程 API 配置
  remote?: {
    baseUrl?: string;
    apiKey?: string;
    headers?: Record<string, string>;
    batch?: {
      enabled: boolean;
      wait: boolean;
      concurrency: number;
      pollIntervalMs: number;
      timeoutMinutes: number;
    };
  };

  // 实验性功能
  experimental: {
    sessionMemory: boolean;  // 会话记忆索引
  };

  // 回退配置
  fallback: "openai" | "gemini" | "local" | "none";
  model: string;  // 嵌入模型

  // 本地模型配置
  local: {
    modelPath?: string;
    modelCacheDir?: string;
  };

  // 存储配置
  store: {
    driver: "sqlite";
    path: string;  // 支持 {agentId} 占位符
    vector: {
      enabled: boolean;
      extensionPath?: string;  // sqlite-vec 扩展路径
    };
  };

  // 分块配置
  chunking: {
    tokens: number;   // 每块 token 数，默认 400
    overlap: number;  // 重叠 token 数，默认 80
  };

  // 同步配置
  sync: {
    onSessionStart: boolean;   // 会话开始时同步
    onSearch: boolean;         // 搜索前同步
    watch: boolean;            // 文件监听
    watchDebounceMs: number;   // 监听防抖，默认 1500ms
    intervalMinutes: number;   // 定期同步间隔
    sessions: {
      deltaBytes: number;      // 字节变化阈值，默认 100KB
      deltaMessages: number;   // 消息数阈值，默认 50
    };
  };

  // 查询配置
  query: {
    maxResults: number;        // 最大结果数，默认 6
    minScore: number;          // 最小分数阈值，默认 0.35
    hybrid: {
      enabled: boolean;        // 启用混合搜索
      vectorWeight: number;    // 向量权重，默认 0.7
      textWeight: number;      // 文本权重，默认 0.3
      candidateMultiplier: number; // 候选倍数，默认 4
    };
  };

  // 缓存配置
  cache: {
    enabled: boolean;
    maxEntries?: number;
  };
};
```

### 3.2 默认配置值

```typescript
const DEFAULT_OPENAI_MODEL = "text-embedding-3-small";
const DEFAULT_GEMINI_MODEL = "gemini-embedding-001";
const DEFAULT_CHUNK_TOKENS = 400;
const DEFAULT_CHUNK_OVERLAP = 80;
const DEFAULT_WATCH_DEBOUNCE_MS = 1500;
const DEFAULT_SESSION_DELTA_BYTES = 100_000;  // 100KB
const DEFAULT_SESSION_DELTA_MESSAGES = 50;
const DEFAULT_MAX_RESULTS = 6;
const DEFAULT_MIN_SCORE = 0.35;
const DEFAULT_HYBRID_ENABLED = true;
const DEFAULT_HYBRID_VECTOR_WEIGHT = 0.7;
const DEFAULT_HYBRID_TEXT_WEIGHT = 0.3;
const DEFAULT_HYBRID_CANDIDATE_MULTIPLIER = 4;
const DEFAULT_CACHE_ENABLED = true;
const DEFAULT_SOURCES: Array<"memory" | "sessions"> = ["memory"];
```

---

## 四、数据库架构

### 4.1 SQLite Schema

**文件**: `src/memory/memory-schema.ts`

Memory 系统使用 SQLite 作为存储引擎，结合 sqlite-vec 扩展实现向量搜索。

#### 4.1.1 元数据表

```sql
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

存储索引元数据，包括嵌入模型、提供者、分块配置等。

#### 4.1.2 文件追踪表

```sql
CREATE TABLE IF NOT EXISTS files (
  path TEXT PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'memory',
  hash TEXT NOT NULL,
  mtime INTEGER NOT NULL,
  size INTEGER NOT NULL
);
```

追踪已索引的文件，用于增量更新检测。

#### 4.1.3 文本块表

```sql
CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  path TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'memory',
  start_line INTEGER NOT NULL,
  end_line INTEGER NOT NULL,
  hash TEXT NOT NULL,
  model TEXT NOT NULL,
  text TEXT NOT NULL,
  embedding TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
```

存储文本块及其嵌入向量。`embedding` 字段存储序列化的浮点数组。

#### 4.1.4 嵌入缓存表

```sql
CREATE TABLE IF NOT EXISTS embedding_cache (
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  provider_key TEXT NOT NULL,
  hash TEXT NOT NULL,
  embedding TEXT NOT NULL,
  dims INTEGER,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (provider, model, provider_key, hash)
);
```

缓存已计算的嵌入向量，避免重复计算。通过内容哈希去重。

#### 4.1.5 全文搜索表 (FTS5)

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text,
  id UNINDEXED,
  path UNINDEXED,
  source UNINDEXED,
  model UNINDEXED,
  start_line UNINDEXED,
  end_line UNINDEXED
);
```

使用 SQLite FTS5 实现 BM25 关键词搜索。

#### 4.1.6 向量搜索表 (sqlite-vec)

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
  id TEXT PRIMARY KEY,
  embedding FLOAT[dimensions]
);
```

使用 sqlite-vec 扩展实现高效向量相似度搜索。

### 4.2 存储位置

- **默认路径**: `~/.openclaw/memory/<agentId>.sqlite`
- **配置路径**: 支持 `{agentId}` 占位符
- **附加文件**: `.sqlite-wal`, `.sqlite-shm` (WAL 模式)

### 4.3 数据库常量

**文件**: `src/memory/manager.ts`

```typescript
const META_KEY = "memory_index_meta_v1";
const SNIPPET_MAX_CHARS = 700;
const VECTOR_TABLE = "chunks_vec";
const FTS_TABLE = "chunks_fts";
const EMBEDDING_CACHE_TABLE = "embedding_cache";
```

---

## 五、核心管理器类

### 5.1 MemoryIndexManager 类结构

**文件**: `src/memory/manager.ts:119-254`

```typescript
export class MemoryIndexManager {
  // 配置相关
  private readonly cacheKey: string;
  private readonly cfg: OpenClawConfig;
  private readonly agentId: string;
  private readonly workspaceDir: string;
  private readonly settings: ResolvedMemorySearchConfig;

  // 嵌入提供者
  private provider: EmbeddingProvider;
  private readonly requestedProvider: "openai" | "local" | "gemini" | "auto";
  private fallbackFrom?: "openai" | "local" | "gemini";
  private fallbackReason?: string;
  private openAi?: OpenAiEmbeddingClient;
  private gemini?: GeminiEmbeddingClient;

  // 批量处理配置
  private batch: {
    enabled: boolean;
    wait: boolean;
    concurrency: number;
    pollIntervalMs: number;
    timeoutMinutes: number;
  };

  // 数据库
  private db: DatabaseSync;

  // 数据源
  private readonly sources: Set<MemorySource>;
  private providerKey: string;

  // 缓存配置
  private readonly cache: { enabled: boolean; maxEntries?: number };

  // 向量搜索
  private readonly vector: {
    enabled: boolean;
    available: boolean | null;
    extensionPath?: string;
    loadError?: string;
  };

  // 全文搜索
  private readonly fts: {
    enabled: boolean;
    available: boolean;
    loadError?: string;
  };

  // 异步状态
  private vectorReady: Promise<boolean> | null = null;

  // 文件监听
  private watcher: FSWatcher | null = null;
  private watchTimer: NodeJS.Timeout | null = null;

  // 会话监听
  private sessionWatchTimer: NodeJS.Timeout | null = null;
  private sessionUnsubscribe: (() => void) | null = null;

  // 定期同步
  private intervalTimer: NodeJS.Timeout | null = null;

  // 状态标志
  private closed = false;
  private dirty = false;
  private sessionsDirty = false;

  // 会话增量追踪
  private sessionsDirtyFiles = new Set<string>();
  private sessionPendingFiles = new Set<string>();
  private sessionDeltas = new Map<string, {
    lastSize: number;
    pendingBytes: number;
    pendingMessages: number;
  }>();
  private sessionWarm = new Set<string>();

  // 同步锁
  private syncing: Promise<void> | null = null;
}
```

### 5.2 关键常量

```typescript
const SESSION_DIRTY_DEBOUNCE_MS = 5000;
const EMBEDDING_BATCH_MAX_TOKENS = 8000;
const EMBEDDING_APPROX_CHARS_PER_TOKEN = 1;
const EMBEDDING_INDEX_CONCURRENCY = 4;
const EMBEDDING_RETRY_MAX_ATTEMPTS = 3;
const EMBEDDING_RETRY_BASE_DELAY_MS = 500;
const EMBEDDING_RETRY_MAX_DELAY_MS = 8000;
const BATCH_FAILURE_LIMIT = 2;
const SESSION_DELTA_READ_CHUNK_BYTES = 64 * 1024;
const VECTOR_LOAD_TIMEOUT_MS = 30_000;
const EMBEDDING_QUERY_TIMEOUT_REMOTE_MS = 60_000;
const EMBEDDING_QUERY_TIMEOUT_LOCAL_MS = 5 * 60_000;
const EMBEDDING_BATCH_TIMEOUT_REMOTE_MS = 2 * 60_000;
const EMBEDDING_BATCH_TIMEOUT_LOCAL_MS = 10 * 60_000;
```

---

## 六、文件发现与读取

### 6.1 Memory 文件发现

**文件**: `src/memory/internal.ts:78-144`

Memory 系统从以下位置发现文件：

1. **根目录文件**
   - `MEMORY.md` 或 `memory.md`（工作目录根目录）

2. **Memory 目录**
   - `memory/` 目录下的所有 `.md` 文件（递归）

3. **额外路径**
   - 通过 `memorySearch.extraPaths` 配置的路径

```typescript
export async function listMemoryFiles(
  workspaceDir: string,
  extraPaths?: string[],
): Promise<string[]> {
  // 1. 检查根目录 MEMORY.md / memory.md
  // 2. 扫描 memory/ 目录
  // 3. 扫描额外路径
  // 4. 按 realpath 去重
  // 5. 忽略符号链接
  // 返回相对路径列表
}
```

### 6.2 文件条目构建

```typescript
export async function buildFileEntry(
  absPath: string,
  workspaceDir: string,
): Promise<MemoryFileEntry> {
  // 1. 读取文件统计信息
  const stats = await fs.stat(absPath);

  // 2. 读取文件内容
  const content = await fs.readFile(absPath, "utf-8");

  // 3. 计算 SHA256 哈希
  const hash = hashText(content);

  // 4. 计算相对路径
  const relPath = path.relative(workspaceDir, absPath);

  return {
    path: relPath,
    absPath,
    mtimeMs: stats.mtimeMs,
    size: stats.size,
    hash,
  };
}
```

### 6.3 Markdown 分块

**文件**: `src/memory/internal.ts:166-247`

```typescript
export function chunkMarkdown(
  content: string,
  chunking: { tokens: number; overlap: number },
): MemoryChunk[] {
  // 1. 按行分割内容
  const lines = content.split("\n");

  // 2. 使用 js-tiktoken 估算 token 数
  // 3. 创建重叠的块
  //    - 每块大约 400 tokens（可配置）
  //    - 块之间重叠 80 tokens（可配置）

  // 4. 为每块计算 SHA256 哈希
  // 5. 保留行号信息

  return chunks;
}
```

**特点**：
- 保留原始行号用于定位
- 块之间有重叠以保持上下文
- 每块大小可配置
- 过滤空块

### 6.4 会话文件提取

**文件**: `src/memory/session-files.ts:44-124`

会话文件存储在 `~/.openclaw/agents/<agentId>/sessions/*.jsonl` 中。

```typescript
export function extractSessionText(content: unknown): string | null {
  // 1. 验证消息格式
  // 2. 提取 role 和 content
  // 3. 只保留 user 和 assistant 消息
  // 4. 规范化空白
  // 5. 连接文本
}

export async function buildSessionEntry(
  absPath: string,
): Promise<SessionFileEntry | null> {
  // 1. 读取 JSONL 文件
  // 2. 逐行解析 JSON
  // 3. 提取用户和助手消息
  // 4. 规范化并连接
  // 5. 计算内容哈希
  // 6. 返回会话条目
}
```

---

## 七、嵌入与索引

### 7.1 嵌入提供者抽象

**文件**: `src/memory/embeddings.ts`

```typescript
export type EmbeddingProvider = {
  id: string;
  model: string;
  embedQuery: (text: string) => Promise<number[]>;
  embedBatch: (texts: string[]) => Promise<number[][]>;
};
```

### 7.2 支持的提供者

#### 7.2.1 OpenAI

- **模型**: `text-embedding-3-small`（默认）
- **维度**: 1536
- **特点**: 支持批量 API，成本低
- **文件**: `src/memory/embeddings-openai.ts`

#### 7.2.2 Gemini

- **模型**: `gemini-embedding-001`（默认）
- **维度**: 768
- **特点**: 支持批量 API
- **文件**: `src/memory/embeddings-gemini.ts`

#### 7.2.3 本地模型

- **框架**: node-llama-cpp
- **格式**: GGUF
- **特点**: 离线运行，无 API 调用
- **配置**: `local.modelPath`, `local.modelCacheDir`

### 7.3 文件索引流程

**文件**: `src/memory/manager.ts:2300-2397`

```typescript
private async indexFile(
  entry: MemoryFileEntry | SessionFileEntry,
  options: { source: MemorySource; content?: string },
) {
  // 1. 读取文件内容
  const content = options.content ??
    (await fs.readFile(entry.absPath, "utf-8"));

  // 2. 分块 Markdown
  const chunks = chunkMarkdown(content, this.settings.chunking)
    .filter((chunk) => chunk.text.trim().length > 0);

  // 3. 生成嵌入向量
  const embeddings = this.batch.enabled
    ? await this.embedChunksWithBatch(chunks, entry, options.source)
    : await this.embedChunksInBatches(chunks);

  // 4. 确保向量表就绪
  const sample = embeddings.find((e) => e.length > 0);
  const vectorReady = sample
    ? await this.ensureVectorReady(sample.length)
    : false;

  // 5. 删除旧块
  this.db.prepare(
    `DELETE FROM chunks WHERE path = ? AND source = ?`
  ).run(entry.path, options.source);

  // 6. 插入新块
  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const embedding = embeddings[i];
    const id = `${entry.path}:${chunk.startLine}:${chunk.endLine}`;

    this.db.prepare(`
      INSERT INTO chunks (
        id, path, source, start_line, end_line,
        hash, model, text, embedding, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id, entry.path, options.source,
      chunk.startLine, chunk.endLine,
      chunk.hash, this.provider.model,
      chunk.text, JSON.stringify(embedding),
      Date.now()
    );
  }

  // 7. 插入向量表
  if (vectorReady) {
    for (let i = 0; i < chunks.length; i++) {
      const id = `${entry.path}:${chunks[i].startLine}:${chunks[i].endLine}`;
      this.db.prepare(`
        INSERT INTO ${VECTOR_TABLE} (id, embedding)
        VALUES (?, ?)
      `).run(id, embeddings[i]);
    }
  }

  // 8. 插入 FTS 表
  if (this.fts.enabled && this.fts.available) {
    for (let i = 0; i < chunks.length; i++) {
      const id = `${entry.path}:${chunks[i].startLine}:${chunks[i].endLine}`;
      this.db.prepare(`
        INSERT INTO ${FTS_TABLE} (
          text, id, path, source, model, start_line, end_line
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `).run(
        chunks[i].text, id, entry.path, options.source,
        this.provider.model, chunks[i].startLine, chunks[i].endLine
      );
    }
  }

  // 9. 更新文件元数据
  this.db.prepare(`
    INSERT OR REPLACE INTO files (path, source, hash, mtime, size)
    VALUES (?, ?, ?, ?, ?)
  `).run(
    entry.path, options.source, entry.hash,
    entry.mtimeMs, entry.size
  );
}
```

### 7.4 批量嵌入

**文件**: `src/memory/manager.ts:1900-2000+`

支持两种批量模式：

#### 7.4.1 OpenAI 批量 API

```typescript
private async embedChunksWithBatch(
  chunks: MemoryChunk[],
  entry: MemoryFileEntry | SessionFileEntry,
  source: MemorySource,
): Promise<number[][]> {
  // 1. 加载缓存的嵌入
  const cached = this.loadEmbeddingCache(
    chunks.map((c) => c.hash)
  );

  // 2. 识别缺失的块
  const missing = chunks.filter((c) => !cached.has(c.hash));

  // 3. 提交批量请求
  const batchId = await this.openAi!.submitBatch(
    missing.map((c) => c.text)
  );

  // 4. 轮询完成
  const results = await this.openAi!.pollBatch(batchId);

  // 5. 缓存结果
  for (const result of results) {
    this.cacheEmbedding(result.hash, result.embedding);
  }

  // 6. 合并缓存和新结果
  return chunks.map((c) => cached.get(c.hash) || ...);
}
```

#### 7.4.2 嵌入缓存

```typescript
private loadEmbeddingCache(hashes: string[]): Map<string, number[]> {
  // 按内容哈希加载缓存的嵌入
  // 避免重复计算相同内容
}

private cacheEmbedding(hash: string, embedding: number[]): void {
  // 存储嵌入到缓存表
  // 键: (provider, model, providerKey, hash)
}
```

---

## 八、搜索机制

### 8.1 搜索接口

**文件**: `src/memory/manager.ts:272-320`

```typescript
async search(
  query: string,
  opts?: {
    maxResults?: number;
    minScore?: number;
    sessionKey?: string;
  },
): Promise<MemorySearchResult[]> {
  // 1. 预热会话（触发同步）
  if (opts?.sessionKey) {
    await this.warmSession(opts.sessionKey);
  }

  // 2. 如果脏或配置了搜索前同步，则同步
  if (this.dirty || this.settings.sync.onSearch) {
    await this.sync({ reason: "search" });
  }

  // 3. 嵌入查询
  const queryVec = await this.provider.embedQuery(query);

  // 4. 向量搜索
  const vectorResults = await searchVector({
    db: this.db,
    vectorTable: VECTOR_TABLE,
    providerModel: this.provider.model,
    queryVec,
    limit: opts?.maxResults || this.settings.query.maxResults,
    snippetMaxChars: SNIPPET_MAX_CHARS,
    ensureVectorReady: this.ensureVectorReady.bind(this),
    sourceFilterVec: this.buildSourceFilter(),
    sourceFilterChunks: this.buildSourceFilter(),
  });

  // 5. 关键词搜索（如果启用混合搜索）
  let keywordResults: MemorySearchResult[] = [];
  if (this.settings.query.hybrid.enabled && this.fts.available) {
    keywordResults = await searchKeyword({
      db: this.db,
      ftsTable: FTS_TABLE,
      query,
      limit: opts?.maxResults || this.settings.query.maxResults,
      snippetMaxChars: SNIPPET_MAX_CHARS,
      sourceFilter: this.buildSourceFilter(),
    });
  }

  // 6. 合并混合结果
  const results = this.settings.query.hybrid.enabled
    ? mergeHybridResults({
        vector: vectorResults,
        keyword: keywordResults,
        vectorWeight: this.settings.query.hybrid.vectorWeight,
        textWeight: this.settings.query.hybrid.textWeight,
      })
    : vectorResults;

  // 7. 过滤和限制
  const minScore = opts?.minScore ?? this.settings.query.minScore;
  const maxResults = opts?.maxResults ?? this.settings.query.maxResults;

  return results
    .filter((r) => r.score >= minScore)
    .slice(0, maxResults);
}
```

### 8.2 向量搜索

**文件**: `src/memory/manager-search.ts`

```typescript
export async function searchVector(params: {
  db: DatabaseSync;
  vectorTable: string;
  providerModel: string;
  queryVec: number[];
  limit: number;
  snippetMaxChars: number;
  ensureVectorReady: (dimensions: number) => Promise<boolean>;
  sourceFilterVec: { sql: string; params: MemorySource[] };
  sourceFilterChunks: { sql: string; params: MemorySource[] };
}): Promise<MemorySearchResult[]> {
  // 1. 确保向量表就绪
  const vectorReady = await params.ensureVectorReady(params.queryVec.length);

  if (!vectorReady) {
    // 回退到进程内余弦相似度
    return searchVectorInProcess(params);
  }

  // 2. 使用 sqlite-vec 查询
  const sql = `
    SELECT
      v.id,
      distance
    FROM ${params.vectorTable} v
    WHERE v.embedding MATCH ?
      AND k = ?
    ORDER BY distance
  `;

  const rows = params.db.prepare(sql).all(
    params.queryVec,
    params.limit * params.sourceFilterVec.params.length
  );

  // 3. 获取块详情
  const results: MemorySearchResult[] = [];
  for (const row of rows) {
    const chunk = params.db.prepare(`
      SELECT path, source, start_line, end_line, text
      FROM chunks
      WHERE id = ? AND model = ? ${params.sourceFilterChunks.sql}
    `).get(row.id, params.providerModel, ...params.sourceFilterChunks.params);

    if (chunk) {
      results.push({
        path: chunk.path,
        startLine: chunk.start_line,
        endLine: chunk.end_line,
        score: 1 - row.distance,  // 距离转换为相似度
        snippet: truncateSnippet(chunk.text, params.snippetMaxChars),
        source: chunk.source,
      });
    }
  }

  return results;
}
```

### 8.3 关键词搜索 (BM25)

**文件**: `src/memory/hybrid.ts`

```typescript
export async function searchKeyword(params: {
  db: DatabaseSync;
  ftsTable: string;
  query: string;
  limit: number;
  snippetMaxChars: number;
  sourceFilter: { sql: string; params: MemorySource[] };
}): Promise<MemorySearchResult[]> {
  // 使用 FTS5 BM25 搜索
  const sql = `
    SELECT
      id,
      path,
      source,
      start_line,
      end_line,
      bm25(${params.ftsTable}) as rank
    FROM ${params.ftsTable}
    WHERE ${params.ftsTable} MATCH ?
      ${params.sourceFilter.sql}
    ORDER BY rank
    LIMIT ?
  `;

  const rows = params.db.prepare(sql).all(
    params.query,
    ...params.sourceFilter.params,
    params.limit
  );

  return rows.map((row) => ({
    id: row.id,
    path: row.path,
    source: row.source,
    startLine: row.start_line,
    endLine: row.end_line,
    score: bm25RankToScore(row.rank),
    snippet: "...",  // 从 chunks 表获取
    textScore: bm25RankToScore(row.rank),
  }));
}

export function bm25RankToScore(rank: number): number {
  // BM25 rank 是负数，越小越好
  // 转换为 0-1 分数
  return 1 / (1 + Math.max(0, -rank));
}
```

### 8.4 混合搜索合并

```typescript
export function mergeHybridResults(params: {
  vector: Array<MemorySearchResult & { id: string }>;
  keyword: Array<MemorySearchResult & { id: string; textScore: number }>;
  vectorWeight: number;
  textWeight: number;
}): MemorySearchResult[] {
  // 1. 按 ID 合并结果
  const merged = new Map<string, MemorySearchResult>();

  for (const result of params.vector) {
    merged.set(result.id, {
      ...result,
      score: result.score * params.vectorWeight,
    });
  }

  for (const result of params.keyword) {
    const existing = merged.get(result.id);
    if (existing) {
      // 组合分数
      existing.score += result.textScore * params.textWeight;
    } else {
      merged.set(result.id, {
        ...result,
        score: result.textScore * params.textWeight,
      });
    }
  }

  // 2. 排序并返回
  return Array.from(merged.values())
    .sort((a, b) => b.score - a.score);
}
```

### 8.5 搜索工具

**文件**: `src/agents/tools/memory-tool.ts:22-73`

```typescript
export function createMemorySearchTool(options: {
  config?: OpenClawConfig;
  agentSessionKey?: string;
}): AnyAgentTool | null {
  return {
    name: "memory_search",
    description: "语义搜索记忆文件和会话历史",
    input_schema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "搜索查询",
        },
        maxResults: {
          type: "number",
          description: "最大结果数",
        },
      },
      required: ["query"],
    },
    async execute(input) {
      const manager = await getMemoryIndexManager(options);
      const results = await manager.search(input.query, {
        maxResults: input.maxResults,
        sessionKey: options.agentSessionKey,
      });

      return {
        results,
        provider: manager.getProvider(),
        model: manager.getModel(),
      };
    },
  };
}
```

---

## 九、同步与管理

### 9.1 同步触发器

Memory 系统支持多种同步触发方式：

#### 9.1.1 会话启动同步

```typescript
async warmSession(sessionKey: string): Promise<void> {
  if (this.sessionWarm.has(sessionKey)) return;
  this.sessionWarm.add(sessionKey);

  if (this.settings.sync.onSessionStart) {
    await this.sync({ reason: "session-start" });
  }
}
```

#### 9.1.2 搜索前同步

在 `search()` 方法中，如果配置了 `sync.onSearch`，会在搜索前同步。

#### 9.1.3 文件监听同步

**文件**: `src/memory/manager.ts:850-884`

```typescript
private ensureWatcher() {
  if (this.watcher || !this.settings.sync.watch) return;

  // 使用 chokidar 监听文件变化
  const paths = [
    path.join(this.workspaceDir, "MEMORY.md"),
    path.join(this.workspaceDir, "memory.md"),
    path.join(this.workspaceDir, "memory"),
    ...this.settings.extraPaths,
  ];

  this.watcher = chokidar.watch(paths, {
    ignoreInitial: true,
    ignored: /(^|[\/\\])\../,  // 忽略隐藏文件
  });

  this.watcher.on("add", () => this.scheduleWatchSync());
  this.watcher.on("change", () => this.scheduleWatchSync());
  this.watcher.on("unlink", () => this.scheduleWatchSync());
}

private scheduleWatchSync() {
  this.dirty = true;

  if (this.watchTimer) {
    clearTimeout(this.watchTimer);
  }

  this.watchTimer = setTimeout(() => {
    void this.sync({ reason: "watch" });
  }, this.settings.sync.watchDebounceMs);
}
```

#### 9.1.4 会话增量同步

**文件**: `src/memory/manager.ts:886-950`

```typescript
private ensureSessionListener() {
  if (this.sessionUnsubscribe || !this.sources.has("sessions")) return;

  // 订阅会话更新事件
  this.sessionUnsubscribe = subscribeToSessionUpdates((event) => {
    if (event.agentId !== this.agentId) return;

    this.sessionPendingFiles.add(event.sessionFile);
    this.scheduleSessionDeltaBatch();
  });
}

private async processSessionDeltaBatch(): Promise<void> {
  const pending = Array.from(this.sessionPendingFiles);
  this.sessionPendingFiles.clear();

  for (const file of pending) {
    const stats = await fs.stat(file);
    const delta = this.sessionDeltas.get(file) || {
      lastSize: 0,
      pendingBytes: 0,
      pendingMessages: 0,
    };

    delta.pendingBytes += stats.size - delta.lastSize;
    delta.pendingMessages += 1;

    // 检查阈值
    if (
      delta.pendingBytes >= this.settings.sync.sessions.deltaBytes ||
      delta.pendingMessages >= this.settings.sync.sessions.deltaMessages
    ) {
      this.sessionsDirty = true;
      this.sessionsDirtyFiles.add(file);
      this.sessionDeltas.delete(file);
    } else {
      this.sessionDeltas.set(file, delta);
    }
  }

  if (this.sessionsDirty) {
    await this.sync({ reason: "session-delta" });
  }
}
```

#### 9.1.5 定期同步

```typescript
private ensureIntervalSync() {
  if (this.intervalTimer || this.settings.sync.intervalMinutes <= 0) return;

  this.intervalTimer = setInterval(() => {
    void this.sync({ reason: "interval" });
  }, this.settings.sync.intervalMinutes * 60 * 1000);
}
```

### 9.2 主同步逻辑

**文件**: `src/memory/manager.ts:1309-1375`

```typescript
async sync(params?: {
  reason?: string;
  force?: boolean;
  progress?: (update: MemorySyncProgressUpdate) => void;
}): Promise<void> {
  // 防止并发同步
  if (this.syncing) {
    await this.syncing;
    return;
  }

  this.syncing = this.runSync(params).finally(() => {
    this.syncing = null;
  });

  await this.syncing;
}

private async runSync(params?: {
  reason?: string;
  force?: boolean;
  progress?: (update: MemorySyncProgressUpdate) => void;
}): Promise<void> {
  // 1. 加载向量扩展
  await this.loadVectorExtension();

  // 2. 检查是否需要完全重建索引
  const needsFullReindex = this.needsFullReindex();

  // 3. 执行同步
  if (needsFullReindex || params?.force) {
    await this.runSafeReindex(params);
  } else {
    await this.syncMemoryFiles(params);
    await this.syncSessionFiles(params);
  }

  // 4. 清理状态
  this.dirty = false;
  this.sessionsDirty = false;
  this.sessionsDirtyFiles.clear();
}
```

### 9.3 安全重建索引

**文件**: `src/memory/manager.ts:1441-1540`

```typescript
private async runSafeReindex(params: {
  reason?: string;
  force?: boolean;
  progress?: MemorySyncProgressState;
}): Promise<void> {
  const tempPath = `${this.dbPath}.tmp`;
  const backupPath = `${this.dbPath}.backup`;

  try {
    // 1. 创建临时数据库
    const tempDb = new DatabaseSync(tempPath);
    ensureMemoryIndexSchema(tempDb);

    // 2. 在临时数据库中构建索引
    await this.buildIndexInDb(tempDb, params.progress);

    // 3. 关闭临时数据库
    tempDb.close();

    // 4. 原子交换数据库
    await this.swapIndexFiles(this.dbPath, tempPath);

    // 5. 重新打开数据库
    this.db.close();
    this.db = new DatabaseSync(this.dbPath);

    // 6. 清理备份
    await this.removeIndexFiles(backupPath);
  } catch (error) {
    // 恢复备份
    if (await fs.exists(backupPath)) {
      await this.swapIndexFiles(this.dbPath, backupPath);
    }
    throw error;
  }
}
```

### 9.4 Memory 文件同步

**文件**: `src/memory/manager.ts:1108-1181`

```typescript
private async syncMemoryFiles(params: {
  needsFullReindex: boolean;
  progress?: MemorySyncProgressState;
}) {
  if (!this.sources.has("memory")) return;

  // 1. 列出所有 memory 文件
  const files = await listMemoryFiles(
    this.workspaceDir,
    this.settings.extraPaths
  );

  const activePaths = new Set<string>();

  // 2. 处理每个文件
  for (const file of files) {
    const entry = await buildFileEntry(file, this.workspaceDir);
    activePaths.add(entry.path);

    // 检查是否需要索引
    const existing = this.db.prepare(
      `SELECT hash FROM files WHERE path = ? AND source = ?`
    ).get(entry.path, "memory");

    if (!existing || existing.hash !== entry.hash) {
      await this.indexFile(entry, { source: "memory" });
      params.progress?.update({ completed: 1 });
    }
  }

  // 3. 删除过期条目
  const staleRows = this.db.prepare(
    `SELECT path FROM files WHERE source = ?`
  ).all("memory");

  for (const stale of staleRows) {
    if (activePaths.has(stale.path)) continue;

    // 删除文件记录
    this.db.prepare(
      `DELETE FROM files WHERE path = ? AND source = ?`
    ).run(stale.path, "memory");

    // 删除向量
    this.db.prepare(
      `DELETE FROM ${VECTOR_TABLE} WHERE id IN (
        SELECT id FROM chunks WHERE path = ? AND source = ?
      )`
    ).run(stale.path, "memory");

    // 删除块
    this.db.prepare(
      `DELETE FROM chunks WHERE path = ? AND source = ?`
    ).run(stale.path, "memory");

    // 删除 FTS
    if (this.fts.enabled && this.fts.available) {
      this.db.prepare(
        `DELETE FROM ${FTS_TABLE} WHERE path = ? AND source = ? AND model = ?`
      ).run(stale.path, "memory", this.provider.model);
    }
  }
}
```

### 9.5 会话文件同步

**文件**: `src/memory/manager.ts:1183-1260`

```typescript
private async syncSessionFiles(params: {
  needsFullReindex: boolean;
  progress?: MemorySyncProgressState;
}) {
  if (!this.sources.has("sessions")) return;

  // 1. 列出所有会话文件
  const sessionDir = path.join(
    this.cfg.agentsDir,
    this.agentId,
    "sessions"
  );

  const files = await listSessionFiles(sessionDir);

  // 2. 处理每个文件
  for (const file of files) {
    const entry = await buildSessionEntry(file);
    if (!entry) continue;

    // 检查是否需要索引
    const existing = this.db.prepare(
      `SELECT hash FROM files WHERE path = ? AND source = ?`
    ).get(entry.path, "sessions");

    if (!existing || existing.hash !== entry.hash) {
      await this.indexFile(entry, {
        source: "sessions",
        content: entry.content,
      });

      // 重置增量追踪
      this.sessionDeltas.delete(file);
      params.progress?.update({ completed: 1 });
    }
  }

  // 3. 删除过期条目（同 memory 文件）
}
```

---

## 十、生命周期管理

### 10.1 资源清理

**文件**: `src/memory/manager.ts:622-649`

```typescript
async close(): Promise<void> {
  if (this.closed) return;
  this.closed = true;

  // 1. 清理所有定时器
  if (this.watchTimer) {
    clearTimeout(this.watchTimer);
    this.watchTimer = null;
  }

  if (this.sessionWatchTimer) {
    clearTimeout(this.sessionWatchTimer);
    this.sessionWatchTimer = null;
  }

  if (this.intervalTimer) {
    clearInterval(this.intervalTimer);
    this.intervalTimer = null;
  }

  // 2. 关闭文件监听器
  if (this.watcher) {
    await this.watcher.close();
    this.watcher = null;
  }

  // 3. 取消会话订阅
  if (this.sessionUnsubscribe) {
    this.sessionUnsubscribe();
    this.sessionUnsubscribe = null;
  }

  // 4. 关闭数据库
  this.db.close();

  // 5. 从缓存中移除
  INDEX_CACHE.delete(this.cacheKey);
}
```

### 10.2 索引文件管理

```typescript
private async swapIndexFiles(
  targetPath: string,
  tempPath: string,
): Promise<void> {
  // 原子交换 SQLite 文件
  // 1. 备份当前文件
  // 2. 移动临时文件到目标位置
  // 3. 处理 WAL 和 SHM 文件
  // 4. 失败时恢复备份
}

private async moveIndexFiles(
  sourceBase: string,
  targetBase: string,
): Promise<void> {
  // 移动 SQLite 文件及其 WAL/SHM
  await fs.rename(sourceBase, targetBase);
  await fs.rename(`${sourceBase}-wal`, `${targetBase}-wal`).catch(() => {});
  await fs.rename(`${sourceBase}-shm`, `${targetBase}-shm`).catch(() => {});
}

private async removeIndexFiles(basePath: string): Promise<void> {
  // 删除 SQLite 文件及其 WAL/SHM
  await fs.unlink(basePath).catch(() => {});
  await fs.unlink(`${basePath}-wal`).catch(() => {});
  await fs.unlink(`${basePath}-shm`).catch(() => {});
}
```

---

## 十一、与其他模块的集成

### 11.1 Agent 工具集成

**文件**: `src/agents/tools/memory-tool.ts`

Memory 系统通过两个工具暴露给 Agent：

1. **memory_search**: 语义搜索工具
2. **memory_get**: 文件读取工具

```typescript
export function createMemoryGetTool(options: {
  config?: OpenClawConfig;
  agentSessionKey?: string;
}): AnyAgentTool | null {
  return {
    name: "memory_get",
    description: "读取特定记忆文件",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: "文件路径" },
        from: { type: "number", description: "起始行" },
        lines: { type: "number", description: "行数" },
      },
      required: ["path"],
    },
    async execute(input) {
      // 验证路径在允许的目录内
      // 读取文件内容
      // 返回指定行范围
    },
  };
}
```

### 11.2 Memory Flush（预压缩）

**文件**: `src/auto-reply/reply/memory-flush.ts`

```typescript
export const DEFAULT_MEMORY_FLUSH_SOFT_TOKENS = 4000;

export function shouldRunMemoryFlush(params: {
  entry?: Pick<SessionEntry, "totalTokens" | "compactionCount" | "memoryFlushCompactionCount">;
  contextWindowTokens: number;
  reserveTokensFloor: number;
  softThresholdTokens: number;
}): boolean {
  // 当会话 token 数超过阈值时触发
  // 阈值 = contextWindow - reserveTokensFloor - softThresholdTokens
  // 每个压缩周期只运行一次
  // 只读工作区跳过
}
```

### 11.3 CLI 集成

**文件**: `src/cli/memory-cli.ts`

```bash
# 查看索引状态
openclaw memory status

# 深度探测（检查向量/嵌入可用性）
openclaw memory status --deep

# 手动触发索引
openclaw memory index

# 从 CLI 搜索
openclaw memory search "查询内容"
```

---

## 十二、配置示例

### 12.1 基础配置

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "enabled": true,
        "provider": "openai",
        "model": "text-embedding-3-small",
        "sources": ["memory"],
        "chunking": {
          "tokens": 400,
          "overlap": 80
        },
        "sync": {
          "onSessionStart": true,
          "watch": true
        }
      }
    }
  }
}
```

### 12.2 高级配置

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "enabled": true,
        "provider": "auto",
        "fallback": "local",
        "sources": ["memory", "sessions"],
        "extraPaths": ["docs/", "notes/"],
        "store": {
          "path": "~/.openclaw/memory/{agentId}.sqlite",
          "vector": {
            "enabled": true
          }
        },
        "sync": {
          "onSessionStart": true,
          "onSearch": false,
          "watch": true,
          "watchDebounceMs": 1500,
          "intervalMinutes": 60,
          "sessions": {
            "deltaBytes": 100000,
            "deltaMessages": 50
          }
        },
        "query": {
          "maxResults": 6,
          "minScore": 0.35,
          "hybrid": {
            "enabled": true,
            "vectorWeight": 0.7,
            "textWeight": 0.3
          }
        },
        "cache": {
          "enabled": true
        }
      }
    }
  }
}
```

---

## 十三、性能优化

### 13.1 嵌入缓存

- 按内容哈希缓存嵌入向量
- 避免重复计算相同内容
- 支持跨文件去重

### 13.2 增量索引

- 只索引变更的文件
- 使用文件哈希检测变化
- 保留未变更文件的索引

### 13.3 批量 API

- OpenAI 和 Gemini 支持批量嵌入
- 降低 API 调用成本
- 提高大规模索引效率

### 13.4 向量搜索优化

- 使用 sqlite-vec 扩展加速
- 回退到进程内余弦相似度
- 候选倍数优化混合搜索

---

## 十四、故障排查

### 14.1 常见问题

**问题**: 向量搜索不可用

**解决**:
```bash
# 检查 sqlite-vec 扩展
openclaw memory status --deep

# 手动指定扩展路径
{
  "memorySearch": {
    "store": {
      "vector": {
        "extensionPath": "/path/to/vec0.so"
      }
    }
  }
}
```

**问题**: 索引过时

**解决**:
```bash
# 手动触发同步
openclaw memory index --force
```

**问题**: 嵌入提供者失败

**解决**:
- 检查 API 密钥配置
- 配置回退提供者
- 使用本地模型

### 14.2 调试技巧

1. 查看索引状态: `openclaw memory status --deep`
2. 检查数据库: `sqlite3 ~/.openclaw/memory/<agentId>.sqlite`
3. 查看日志: 搜索 `[memory]` 标签
4. 测试搜索: `openclaw memory search "测试查询"`

---

## 十五、总结

Memory 系统是 OpenClaw 的核心能力之一，提供了：

- **语义搜索**: 基于向量嵌入的相似度搜索
- **混合搜索**: 结合向量和关键词搜索
- **增量索引**: 高效的变更检测和索引更新
- **多源支持**: Memory 文件和会话历史
- **灵活配置**: 丰富的配置选项和回退机制

通过合理配置和使用，Memory 系统可以显著提升 Agent 的上下文理解和长期记忆能力。
