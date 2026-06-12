# Changelog

All notable changes to **agentcanvas** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-06-12

### Fixed

- Inspector: add spacing between the model-call metrics grid and the cost section, so the
  cost details no longer appear visually glued to the metrics
  ([#1](https://github.com/vstorm-co/agentcanvas/pull/1)).

## [0.1.0] - 2026-06-12

Initial release.

### Added

- **Logfire client** (`LogfireClient`) — reads agent traces via the Logfire Query API
  (SQL + read token); region configurable with `LOGFIRE_BASE_URL`.
- **Span-tree parser** (`parse_run`) — turns the OpenTelemetry GenAI spans emitted by
  Pydantic AI into a typed `WorkflowReport`: conversation turns, model rounds, tool
  calls, and **nested agents-as-tools** (recursive, to any depth).
- **Exact cost** — per model call and per run, computed from tokens via
  [`genai-prices`](https://github.com/pydantic/genai-prices); reported as "unknown"
  when the model is not in the price database.
- **Reasoning & token usage** — per-call thinking summaries and input/output/reasoning
  token counts, aggregated for the whole run.
- **Self-contained HTML report** (`render_html`) — a Figma-style, pan/zoom/drag canvas
  with a single consistent Logfire-inspired palette, featuring:
  - block diagram of the full workflow with nested agent frames,
  - a guided tour with **auto** and **manual** (Space / click / arrows) stepping,
  - a click-through, resizable inspector and a full conversation transcript,
  - long content expanding into a modal; everything embedded, works offline.
- **CLI** — `agentcanvas` console script (and `python -m agentcanvas`): build the report
  from the latest or a specific trace, list recent runs, choose the output file.
- **Example agent** (`assets/scripts/main.py`) — a thinking agent with five tools, a
  nested sub-agent and a multi-turn conversation, plus scripts to record the demo media.
- Packaging, typing (mypy), linting (ruff), tests (pytest), and CI/CD (GitHub Actions
  with PyPI Trusted Publishing).

[Unreleased]: https://github.com/vstorm-co/agentcanvas/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/vstorm-co/agentcanvas/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/vstorm-co/agentcanvas/releases/tag/v0.1.0
