"""Convenience entry point for running the CLI from a source checkout.

    uv run --prerelease=allow python viz.py [--trace-id ... | --list | -o ... | --no-open]

When installed, prefer the ``agentcanvas`` console script or ``python -m agentcanvas``.
"""

from __future__ import annotations

from agentcanvas.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
