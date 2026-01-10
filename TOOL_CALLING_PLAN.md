# Tool Calling 实现规划

## 目标

让 Agent 在讨论过程中能够主动调用工具（读写文件、搜索、分析等），而不仅仅是生成文本。

## 当前状态

- 工作目录功能已实现，但仅供用户在 UI 上操作
- Agent 调用 LLM 时不传入工具定义
- LLM 返回的 tool_call 不会被处理

## 内置工具

### 文件操作

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `list_files` | 列出目录内容 | `path?: string` |
| `read_file` | 读取文件内容 | `path: string` |
| `write_file` | 写入/创建文件 | `path: string, content: string` |
| `delete_file` | 删除文件 | `path: string` |
| `rename_file` | 重命名/移动文件 | `old_path: string, new_path: string` |
| `create_directory` | 创建目录 | `path: string` |

### 搜索与分析

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `search_content` | 在文件内容中搜索（支持正则） | `pattern: string, path?: string, file_pattern?: string` |
| `search_files` | 按文件名搜索 | `pattern: string, path?: string` |
| `get_file_info` | 获取文件元信息（大小、修改时间等） | `path: string` |
| `count_lines` | 统计文件行数 | `path: string` |
| `diff_files` | 比较两个文件差异 | `path1: string, path2: string` |

### 代码辅助

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `find_definition` | 查找函数/类定义 | `name: string, path?: string` |
| `find_references` | 查找引用 | `name: string, path?: string` |
| `list_functions` | 列出文件中的函数 | `path: string` |
| `list_imports` | 列出文件的导入 | `path: string` |

### 文本处理

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `replace_in_file` | 替换文件中的内容 | `path: string, search: string, replace: string, all?: bool` |
| `insert_at_line` | 在指定行插入内容 | `path: string, line: number, content: string` |
| `delete_lines` | 删除指定行范围 | `path: string, start: number, end: number` |
| `append_to_file` | 追加内容到文件末尾 | `path: string, content: string` |

## 实现步骤

### Phase 1: 工具基础设施

1. 创建 `backend/src/tools/` 模块
2. 定义 `ToolDefinition`, `ToolCall`, `ToolResult` 结构体
3. 实现 `ToolExecutor` 框架
4. 复用现有 `commands/fs.rs` 的路径安全校验逻辑

### Phase 2: 文件操作工具

1. 实现 `list_files` - 复用现有逻辑
2. 实现 `read_file` - 复用现有逻辑
3. 实现 `write_file` - 复用现有逻辑
4. 实现 `delete_file`, `rename_file`, `create_directory`

### Phase 3: 搜索与分析工具

1. 实现 `search_content` - 正则搜索文件内容
2. 实现 `search_files` - glob 模式匹配文件名
3. 实现 `get_file_info`, `count_lines`
4. 实现 `diff_files` - 文本差异比较

### Phase 4: 代码辅助工具

1. 实现 `find_definition` - 基于正则的简单定义查找
2. 实现 `find_references` - 基于正则的引用查找
3. 实现 `list_functions`, `list_imports` - 基于正则提取

### Phase 5: 文本处理工具

1. 实现 `replace_in_file` - 字符串/正则替换
2. 实现 `insert_at_line`, `delete_lines`
3. 实现 `append_to_file`

### Phase 6: LLM Provider 集成

1. 修改 `LLMProvider` trait，添加 `chat_with_tools` 方法
2. 修改 `LLMResponse`，添加 `tool_calls` 字段
3. 在 `OpenAICompatibleProvider` 中实现 tool calling（OpenAI function calling 格式）

### Phase 7: 编排器集成

1. 修改编排器，在 Agent 回合中处理 tool_calls
2. 实现工具调用循环（LLM → tool_call → execute → result → LLM）
3. 设置最大迭代次数防止无限循环
4. 统计工具调用的 token 消耗

### Phase 8: 前端展示

1. 在消息流中显示工具调用和结果
2. 区分普通消息和工具消息的样式
3. 工具调用可折叠展示详情

## 文件结构

```
backend/src/tools/
├── mod.rs              # 模块导出
├── definition.rs       # ToolDefinition, ToolCall, ToolResult
├── executor.rs         # ToolExecutor
├── security.rs         # 路径安全校验
└── builtin/
    ├── mod.rs
    ├── files.rs        # 文件操作工具
    ├── search.rs       # 搜索与分析工具
    ├── code.rs         # 代码辅助工具
    └── text.rs         # 文本处理工具
```

## 安全控制

1. **路径限制**: 所有文件操作限制在 `workspace_path` 内
2. **路径遍历防护**: 禁止 `..` 和符号链接穿越
3. **文件大小限制**: 读取大文件时截断或分页
4. **执行超时**: 工具执行设置超时限制
5. **操作日志**: 记录所有工具调用便于审计

## 验证方式

1. 创建 Execution，设置工作目录
2. 让 Agent 读取某个文件，验证 `read_file` 正确执行
3. 让 Agent 搜索代码，验证 `search_content` 返回结果
4. 让 Agent 修改文件，验证 `write_file` 执行成功
5. 检查前端正确显示工具调用过程

## 注意事项

- OpenAI 和 Anthropic 的 tool calling 格式略有不同，需要在 provider 层适配
- 工具调用可能形成循环，需要设置最大迭代次数（建议 10 次）
- 流式输出时，tool_calls 通常在最后才完整，需要特殊处理
- 代码辅助工具基于正则实现，不做完整的语法解析
