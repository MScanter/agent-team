# agent-team

Single-machine (no auth) app to build agent teams and run discussions.

## Quickstart

### Desktop (Tauri)

```bash
# Prereqs:
# - Rust toolchain (rustc/cargo)
# - Node.js (npm)

npm --prefix frontend install
npm --prefix backend install

npm --prefix backend run tauri:dev
```

Build release binary:

```bash
npm --prefix backend run tauri:build
```

## Development Notes

- `STORE_SQLITE_PATH` can be set to control where SQLite lives (Tauri reads from env at launch).
- Streaming: Tauri uses app event `execution-event`.
