# agent-team

This project is a single-machine desktop application for building AI agent teams and orchestrating their discussions. It is built using the Tauri framework with a Rust backend and a React frontend.

## Project Overview

- **Purpose:** Create, manage, and execute teams of AI agents.
- **Collaboration Modes:** Supports multiple orchestration styles:
    - **Roundtable:** Agents take turns in a circular fashion.
    - **Debate:** Agents engage in a structured debate format.
    - **Pipeline:** Agents work in a sequential process.
- **Workspace:** Provides a local file system workspace for agents to read and write files during execution.
- **Persistence:** Uses SQLite for storing agents, teams, and execution history.

## Architecture

### Backend (Rust/Tauri)
- **`backend/src/main.rs`**: Entry point, initializes the app state and registers Tauri commands.
- **`backend/src/commands/`**: Contains the implementations of Tauri commands (agents, teams, executions, fs, llm).
- **`backend/src/orchestration/`**: The core engines for agent collaboration (roundtable, debate, pipeline).
- **`backend/src/store/`**: Persistence layer using SQLite.
- **`backend/src/llm/`**: Integration with LLM providers (Anthropic, OpenAI compatible).
- **`backend/src/models/`**: Data models for the application.

### Frontend (React + TypeScript)
- **`frontend/src/App.tsx`**: Main application component and routing.
- **`frontend/src/components/`**: UI components organized by feature (Agent, Team, Execution, ModelConfig).
- **`frontend/src/hooks/`**: Custom React hooks for data fetching and state (using Tanstack Query and Zustand).
- **`frontend/src/services/`**: API abstraction layer that handles communication via Tauri `invoke`.
- **`frontend/src/types/`**: Shared TypeScript type definitions.

## Building and Running

### Prerequisites
- Rust toolchain (rustc/cargo)
- Node.js (npm)

### Commands
- **Install Dependencies:**
  ```bash
  npm --prefix frontend install
  npm --prefix backend install
  ```
- **Run in Development:**
  ```bash
  npm --prefix backend run tauri:dev
  ```
- **Build Release Binary:**
  ```bash
  npm --prefix backend run tauri:build
  ```
- **Linting:**
  ```bash
  # Frontend
  npm --prefix frontend run lint
  # Backend
  cargo clippy --manifest-path backend/Cargo.toml
  ```

## Development Conventions

- **TypeScript/React:**
    - 2-space indentation.
    - No semicolons.
    - Component files: `PascalCase.tsx`.
    - Hook files: `useX.ts`.
- **Rust:**
    - Standard `cargo fmt` formatting.
    - Module files: `snake_case.rs`.
    - Register new commands in `backend/src/commands/mod.rs` and `main.rs`.
- **Persistence:**
    - Database location can be overridden via `STORE_SQLITE_PATH` environment variable.
- **Security:**
    - API keys are treated as secrets; do not commit them.

## Key Files
- `README.md`: Basic setup and quickstart.
- `AGENTS.md`: Detailed repository guidelines and development notes.
- `backend/Cargo.toml`: Backend dependencies and configuration.
- `frontend/package.json`: Frontend dependencies and scripts.
