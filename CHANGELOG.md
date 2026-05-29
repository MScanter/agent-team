# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- MIT `LICENSE` file (the README already declared MIT).
- Unit tests for workspace path security (`tools/security.rs`), orchestration
  state accounting (`orchestration/state.rs`), and agent token reporting.
- GitHub Actions CI: backend `fmt` + `clippy -D warnings` + `test`, and frontend
  lint + type-check + build.
- Frontend ESLint flat config (was missing entirely) and a shared
  `getErrorMessage` utility for consistent error handling.
- Release workflow that builds native installers for macOS, Linux, and Windows
  on version tags.
- `CONTRIBUTING.md` and `.env.example`.

### Changed
- Extracted duplicated token-accounting boilerplate from the roundtable, debate,
  and pipeline engines into `AgentResponse::token_counts()`.
- Filled in `Cargo.toml` package metadata (`authors`, `license`, `repository`).
- Replaced all 52 explicit `any` usages in the frontend with real types;
  `@typescript-eslint/no-explicit-any` is now enforced as an error.

## [0.1.0] - 2026-01

### Added
- Multi-agent orchestration desktop app built on Tauri 2 (Rust) + React 18.
- Four collaboration modes: Roundtable, Pipeline, Debate, Freeform.
- Agent and team management with a local SQLite store.
- OpenAI-compatible and Anthropic LLM providers (bring your own API key).
- Built-in file/code/search tools with sandboxed, workspace-scoped access.

[Unreleased]: https://github.com/MScanter/agent-team/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MScanter/agent-team/releases/tag/v0.1.0
