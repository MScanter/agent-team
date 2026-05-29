# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-29

First public release.

### Added
- Multi-agent orchestration desktop app built on Tauri 2 (Rust) + React 18.
- Four collaboration modes: Roundtable, Pipeline, Debate, Freeform.
- Agent and team management with a local SQLite store.
- OpenAI-compatible and Anthropic LLM providers (bring your own API key).
- Built-in file/code/search tools with sandboxed, workspace-scoped access.
- Unit tests for workspace path security, orchestration state accounting, and
  agent token reporting; GitHub Actions CI (backend `fmt` + `clippy -D warnings`
  + `test`, frontend lint + type-check + build); and a release workflow that
  builds native installers for macOS, Linux, and Windows on version tags.
- MIT `LICENSE`, `CONTRIBUTING.md`, and `.env.example`.

[Unreleased]: https://github.com/MScanter/agent-team/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MScanter/agent-team/releases/tag/v0.1.0
