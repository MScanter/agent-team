# agent-team

A desktop application for creating AI agent teams and running multi-agent discussions.

## What is this?

Agent Team lets you:

- **Create AI Agents** - Define agents with custom system prompts, personalities, and collaboration styles (dominant, supportive, critical)
- **Build Teams** - Assemble agents into teams with different collaboration modes
- **Run Discussions** - Start conversations where multiple agents discuss topics together
- **Work with Files** - Select a workspace directory and let agents read/write files during discussions

## Collaboration Modes

| Mode | Description |
|------|-------------|
| Roundtable | All agents speak in turns, share opinions, then summarize |
| Pipeline | Sequential processing - each agent's output feeds the next |
| Debate | Pro/con teams argue, a judge decides |

## Tech Stack

- **Backend**: Rust + Tauri
- **Frontend**: React + TypeScript
- **Database**: SQLite (local)
- **LLM**: OpenAI-compatible API (bring your own key)

## Quickstart

Prerequisites:
- Rust toolchain (rustc/cargo)
- Node.js (npm)

```bash
npm --prefix frontend install
npm --prefix backend install

npm --prefix backend run tauri:dev
```

Build release binary:

```bash
npm --prefix backend run tauri:build
```

## Development Notes

- `STORE_SQLITE_PATH` can be set to control where SQLite lives (Tauri reads from env at launch)
- Streaming uses Tauri app event `execution-event`
- All file operations are sandboxed to the selected workspace directory
