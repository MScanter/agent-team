# Agent Team

A desktop application for orchestrating multi-agent discussions — not a LangChain wrapper. Built from scratch in Rust with a custom LLM provider abstraction, sandboxed tool execution, and real-time event streaming via Tauri.

## Why this exists

Most multi-agent demos are Python scripts that wrap LangChain's agent loop and call it a day. They work for a blog post but fall apart when you need:

- **Concurrent tool execution** without blocking the async runtime
- **Sandboxed file access** that can't escape the workspace via symlinks or path traversal
- **Multi-provider support** without changing orchestration logic
- **Real-time streaming** to a desktop UI during multi-minute agent runs

This project explores whether a Rust + Tauri stack can do multi-agent orchestration with the same ergonomics as Python but with stronger correctness guarantees.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript)                       │
│  Pages: Home / Agents / Teams / Execution / Models   │
│  State: Zustand · Data fetching: TanStack Query      │
├─────────────────────────────────────────────────────┤
│  Tauri Bridge (JSON-RPC over IPC)                    │
├─────────────────────────────────────────────────────┤
│  Backend (Rust)                                      │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Commands │  │ Orchestration  │  │   Tool       │ │
│  │ (CRUD)   │  │ Engines        │  │   System     │ │
│  └──────────┘  └────────────────┘  └──────────────┘ │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  Store   │  │  Agent         │  │  LLM         │ │
│  │ (SQLite) │  │  Instances     │  │  Providers    │ │
│  └──────────┘  └────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Key design decisions

**1. LLM provider abstraction is a trait, not an enum**

```rust
#[async_trait]
pub trait LLMProvider: Send + Sync {
    async fn chat(&self, messages: Vec<Message>, temperature: f64, max_tokens: u32)
        -> Result<LLMResponse, AppError>;
    async fn chat_with_tools(&self, messages: Vec<Message>, tools: &[ToolDefinition], ...)
        -> Result<LLMResponse, AppError> { ... } // default: fallback to chat()
}
```

Each provider (OpenAI-compatible, Anthropic) implements the trait. Adding a new provider is one file — the orchestration layer doesn't know or care which LLM is running underneath. `chat_with_tools` has a default implementation that falls back to `chat()` for providers that don't support native tool calling, so the tool loop degrades gracefully.

**2. Tool execution is sandboxed**

Agents can read/write/search files in a workspace directory during discussions. Every tool call goes through a security layer that:

- Rejects absolute paths and `..` traversal
- Resolves and verifies symlinks at every path component
- Canonicalizes paths and checks they stay within the workspace root
- Enforces per-call limits: max read bytes (200KB), max search matches (200), timeout (10s)
- Runs blocking I/O on `tokio::task::spawn_blocking` so the async runtime stays responsive

19 built-in tools: file CRUD, content/text search, file search by pattern, file diff, symbol search (definitions/references/functions/imports), line-level text editing.

**3. Orchestration engines are state machines**

Each collaboration mode is a standalone async function that takes a `Vec<AgentInstance>`, drives the discussion, and emits events through a callback for real-time UI updates.

| Mode | Protocol |
|------|----------|
| **Roundtable** | Two-phase: all agents give initial opinions → agents respond to each other. Uses `[DONE]` token for convergence detection — when all agents signal completion, the round ends automatically. |
| **Debate** | Auto-splits agents into pro/con/judge (last agent = judge, remaining split evenly). Opening statements → multi-round rebuttals → judge verdict with structured output (论点总结 / 优势不足 / 最终判断). |
| **Pipeline** | Each agent's output becomes the next agent's context, prefixed with the original task. Suitable for chain-of-thought refinement: researcher → writer → editor. |
| **Freeform** | Open discussion with no fixed turn order — agents can interject based on the conversation state. |

All modes track per-agent token usage and expose it to the UI.

**4. Agent instance manages its own context window**

Each `AgentInstance` maintains:
- Opinion history (last 3 contributions injected as "your previous opinions")
- Tool iteration loop with configurable max_tool_iterations (default 10, clamped 1–50)
- Tool call → tool result message pairing for multi-turn tool use
- Token accounting across the full tool iteration chain, not just the final message

## Tech stack

| Layer | Technology |
|-------|-----------|
| Desktop shell | Tauri 2 |
| Backend | Rust (tokio async runtime) |
| Frontend | React 18 + TypeScript + Tailwind CSS |
| State | Zustand + TanStack Query |
| Storage | SQLite via rusqlite |
| LLM APIs | OpenAI-compatible + Anthropic (extensible via trait) |

## Quick start

```bash
# Prerequisites: Rust toolchain, Node.js >= 18

npm --prefix frontend install

# Development
npm --prefix backend run tauri:dev

# Production build
npm --prefix backend run tauri:build
# Output: backend/target/release/bundle/
```

## What this project taught me

- **Rust's type system catches orchestration bugs at compile time** — the `LLMProvider` trait means you physically can't pass the wrong message format to a provider. In Python/LangChain you'd catch this at runtime.
- **`spawn_blocking` is the right primitive for tool execution** — it keeps the Tauri IPC thread responsive while agents do file I/O. Without it, a single `read_file` on a large file blocks the entire UI.
- **Convergence detection is harder than it looks** — `[DONE]` tokens work but are fragile. A proper solution needs something like structured output (JSON `{"action": "speak" | "pass"}`) or a separate summarizer agent that decides when discussion is exhausted.
- **Tauri's event system is well-suited for streaming agent output** — each agent response is a discrete event. The frontend renders them as they arrive, no polling needed.

## Roadmap

- [ ] Structured output for agent decisions (replace `[DONE]` heuristic)
- [ ] Streaming token display (currently batch-only)
- [ ] Agent memory across sessions (vector store for long-running teams)
- [ ] Custom tool definitions per team (currently global)
- [ ] MCP (Model Context Protocol) integration for external tools

## License

MIT
