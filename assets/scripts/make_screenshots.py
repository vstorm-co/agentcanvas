"""Capture still screenshots of the report's panels for docs.

Drives agent_flow.html with Playwright (installed Chrome) and saves PNGs of the
inspector (model + tool), the conversation panel and the guided tour into assets/.

Run:  uv run --prerelease=allow python make_screenshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "agent_flow.html"
ASSETS = ROOT / "assets"
W, H = 1440, 900

# Each shot: (filename, JS to set the UI state). Globals (N, openFor, …) live in
# the report's script scope and are reachable from page.evaluate.
SHOTS: list[tuple[str, str]] = [
    (
        "screenshot-inspector.png",
        "fit(); openFor(Object.keys(N).find(k => N[k].data.type === 'model'));",
    ),
    (
        "screenshot-tool.png",
        "fit(); openFor(Object.keys(N).find(k => N[k].data.type === 'tool'));",
    ),
    (
        "screenshot-conversation.png",
        "fit(); renderConversation(); document.getElementById('conv').classList.add('open');",
    ),
    (
        "screenshot-tour.png",
        "startTour(false); next(); next(); next();",
    ),
]


def _shoot(page: Page) -> None:
    for filename, script in SHOTS:
        page.evaluate(
            "() => { document.querySelectorAll('.panel').forEach(p => p.classList.remove('open')); "
            "if (typeof endTour === 'function') endTour(); }"
        )
        page.wait_for_timeout(150)
        page.evaluate(f"() => {{ {script} }}")
        page.wait_for_timeout(700)
        page.screenshot(path=str(ASSETS / filename))
        print(f"  ✓ {filename}")


def main() -> int:
    if not HTML.exists():
        print("✖ agent_flow.html not found — run the CLI first.", file=sys.stderr)
        return 1
    ASSETS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        page.goto(HTML.as_uri())
        page.wait_for_timeout(1700)
        _shoot(page)
        browser.close()
    print(f"✓ screenshots written to {ASSETS}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
