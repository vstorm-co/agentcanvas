# Contributing to agentcanvas

Thanks for your interest in contributing! Bug reports, feature ideas, and code contributions are all
welcome. **All communication and contributions must be in English** so that maintainers and the wider
community can review them effectively.

## Getting help / reporting issues

- **Bug reports & feature requests** — [open a GitHub Issue](https://github.com/vstorm-co/agentcanvas/issues)
- **Security vulnerabilities** — email **info@vstorm.co** (do NOT use public Issues)
- **Questions & discussion** — GitHub Issues are the primary, publicly searchable discussion channel

## Development setup

```bash
git clone https://github.com/vstorm-co/agentcanvas.git
cd agentcanvas
make install
```

Prerequisites: [uv](https://github.com/astral-sh/uv) (Python package manager). Pydantic AI v2 is a
pre-release, hence the `--prerelease=allow` flag throughout.

`make install` also installs a [pre-commit](https://pre-commit.com/) hook (the config is also
compatible with [prek](https://github.com/j178/prek)) that runs `make format`, `make lint` and
`make typecheck` on every commit — plus codespell and a few text-hygiene fixers — so the same checks
as `make all` and CI run automatically before you commit (it also blocks direct commits to `main`).
Run them manually against the whole tree with `make hooks` (or `uv run pre-commit run --all-files`).
If you set the project up without `make install`, enable the hook once with `uv run pre-commit install`.

Copy `.env.example` to `.env` (or create `.env`) and set at least `LOGFIRE_READ_TOKEN`. To run the
demo agent you also need `LOGFIRE_WRITE_TOKEN` and `OPENROUTER_API_KEY`. **Never commit `.env` or any
token** — it is git-ignored.

## Running it locally

```bash
uv run --prerelease=allow python assets/scripts/main.py   # generate a sample run (writes to Logfire)
uv run --prerelease=allow python viz.py                    # build agent_flow.html from the latest run
```

The generated HTML embeds its CSS/JS. To verify the front-end after changes, regenerate the report
and open `agent_flow.html` in a browser; check the canvas, the guided tour, the inspector and the
conversation panel.

## Project layout

| Path | Role |
|------|------|
| `agentcanvas/logfire_client.py` | Logfire Query API client |
| `agentcanvas/parser.py` | span tree → recursive workflow payload |
| `agentcanvas/pricing.py` | cost from tokens via `genai-prices` |
| `agentcanvas/render.py` | payload → embedded HTML/CSS/JS report |
| `viz.py` | CLI entry point |
| `assets/scripts/` | dev scripts: `main.py` (demo agent), `make_demo.py`, `make_screenshots.py` |

## Quality gates

Everything is wired through `make`:

| Command | Description |
|---------|-------------|
| `make install` | `uv sync` with the dev group + install the pre-commit git hook |
| `make hooks` | run all pre-commit hooks against every file |
| `make test` | run the pytest suite (offline, against a captured trace fixture) |
| `make lint` | Ruff lint |
| `make format` | Ruff auto-format |
| `make typecheck` | mypy |
| `make all` | lint + typecheck + test |

`make all` must pass before a PR is merged; CI runs the same checks. The pre-commit hook installed by
`make install` runs `make format`, `make lint` and `make typecheck` automatically on each commit.

## Coding standards

- **Python ≥ 3.12**, fully type-annotated. Keep the data layer (`parser`, `pricing`,
  `logfire_client`) free of presentation concerns; all HTML/CSS/JS lives in `render.py`.
- The parsed workflow is a typed `WorkflowReport` (see `models.py`); the renderer consumes exactly
  those fields. If you add data to the diagram, add it to the model first.
- The renderer is plain HTML + vanilla JS embedded as a template string — **no build step and no
  external CDN**, so the report stays self-contained and works offline.
- When you change the embedded JS, sanity-check syntax (extract the `<script>` blocks and run
  `node --check`).

## Pull request process

1. Fork the repo and create your branch from `main`.
2. Make your changes, keeping the data layer and the renderer cleanly separated.
3. Verify the report renders correctly from a real Logfire trace.
4. Submit a PR with a clear description of what changed and why.
5. PR titles should follow [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:`, etc.).

## Questions?

Open an issue on [GitHub](https://github.com/vstorm-co/agentcanvas/issues).
