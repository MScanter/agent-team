# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: Tauri (Rust) desktop backend.
  - `backend/src/commands/`: Tauri `invoke` commands (agents/teams/executions/fs/llm).
  - `backend/src/orchestration/`: orchestration engines (roundtable/debate/pipeline) plus event/state types.
  - `backend/src/store/`: SQLite persistence (see `STORE_SQLITE_PATH`).
- `frontend/`: React + TypeScript UI (Vite + Tailwind).
  - `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/services/`.
  - `frontend/public/`: static assets.
- Docs: `README.md`, `MIGRATION_PLAN.md`.

## Build, Test, and Development Commands
- Install deps: `npm --prefix frontend install` and `npm --prefix backend install`.
- Desktop dev (recommended): `npm --prefix backend run tauri:dev` (runs Vite on `:3000`, launches Tauri).
- Build release binary: `npm --prefix backend run tauri:build`.
- Frontend-only dev (optional): `npm --prefix frontend run dev` (proxies `/api` to `VITE_BACKEND_TARGET`, default `http://localhost:8080`).
- Rust checks: `cargo fmt --manifest-path backend/Cargo.toml` and `cargo clippy --manifest-path backend/Cargo.toml`.

## Coding Style & Naming Conventions
- TypeScript/React: 2-space indentation; match existing “no semicolons” style; components `PascalCase.tsx`, hooks `useX.ts`, shared types in `frontend/src/types/`.
- Rust: format with `cargo fmt`; keep modules `snake_case.rs`; register new commands in `backend/src/commands/mod.rs`.
- Do not commit build artifacts: `frontend/dist/`, `**/node_modules/`.

## Testing Guidelines
- No formal test suite yet; validate changes by running `tauri:dev` and smoke-testing: CRUD Agents/Teams, start an Execution, verify streaming via the `execution-event` channel and workspace file operations.
- If you add tests, keep them close to the code (`#[cfg(test)]` in `backend/src/**`) and document how to run them.

## Commit & Pull Request Guidelines
- Commits follow a lightweight conventional style seen in history: `feat: ...`, `refactor: ...` (lowercase, imperative).
- PRs include: what/why, manual test notes, screenshots/GIFs for UI changes, and any persistence changes (SQLite schema or `STORE_SQLITE_PATH` behavior).

## Security & Configuration Tips
- This is a single-machine, no-auth app; treat model/provider API keys as secrets and avoid committing them.
- Useful env vars: `STORE_SQLITE_PATH=/absolute/path/to/app.db` (read at app launch), `VITE_BACKEND_TARGET=http://localhost:8080` (frontend proxy when not running in Tauri).
