"""Record a smooth, high-resolution demo of the report's guided "Step" tour.

Drives agent_flow.html with Playwright (installed Chrome), recording a video at
the browser's native frame rate so the pan/reveal animations stay smooth, then
encodes a crisp H.264 MP4 (plus a poster frame). MP4 keeps full resolution at a
small size — far better than a GIF for this kind of full-frame motion.

Run:  uv run --prerelease=allow python make_demo.py
Requires: Google Chrome and ffmpeg on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "agent_flow.html"
MP4_OUT = ROOT / "assets" / "demo.mp4"
POSTER_OUT = ROOT / "assets" / "demo-poster.png"
REC_W, REC_H = 1600, 1000  # record large, downscale for crisp anti-aliased text
OUT_W = 1280
FPS = 15
STEP_MS = 720  # per step: ~0.5s glide + reveal + a short hold
POSTER_AT = "2.5"  # seconds into the clip


def _record_video(tmp: Path) -> Path:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        context = browser.new_context(
            viewport={"width": REC_W, "height": REC_H},
            record_video_dir=str(tmp),
            record_video_size={"width": REC_W, "height": REC_H},
        )
        page = context.new_page()
        page.goto(HTML.as_uri())
        page.wait_for_timeout(1800)  # fonts + boot/layout

        page.click("#step")  # enter manual Step mode
        page.wait_for_timeout(900)

        while not page.is_disabled("#nnext"):
            page.click("#nnext")
            page.wait_for_timeout(STEP_MS)
        page.wait_for_timeout(1600)  # linger on the final answer

        video = page.video
        if video is None:  # pragma: no cover - video recording is always enabled above
            raise RuntimeError("Playwright did not record a video.")
        path = Path(video.path())
        context.close()
        browser.close()
        return path


def _encode(video: Path, mp4: Path, poster: Path) -> None:
    vf = f"fps={FPS},scale={OUT_W}:trunc(ow/a/2)*2:flags=lanczos"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "19",
            "-movflags",
            "+faststart",
            str(mp4),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            POSTER_AT,
            "-i",
            str(mp4),
            "-frames:v",
            "1",
            str(poster),
        ],
        check=True,
        capture_output=True,
    )


def main() -> int:
    if not HTML.exists():
        print("✖ agent_flow.html not found — run the CLI first.", file=sys.stderr)
        return 1
    if not shutil.which("ffmpeg"):
        print("✖ ffmpeg not found on PATH.", file=sys.stderr)
        return 1

    MP4_OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        video = _record_video(Path(td))
        _encode(video, MP4_OUT, POSTER_OUT)

    print(f"✓ wrote {MP4_OUT} ({MP4_OUT.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"✓ wrote {POSTER_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
