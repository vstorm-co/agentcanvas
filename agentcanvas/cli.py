"""Command-line interface: pull an agent run from Logfire and build the HTML report."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from .logfire_client import LogfireClient
from .parser import parse_run
from .render import render_html


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="agentcanvas",
        description="Visualize a Pydantic AI agent workflow from Logfire logs.",
    )
    parser.add_argument("--trace-id", help="Trace id to visualize (default: latest).")
    parser.add_argument("--list", action="store_true", help="List recent runs and exit.")
    parser.add_argument("-o", "--output", default="agent_flow.html", help="Output HTML file.")
    parser.add_argument(
        "--no-open", action="store_true", help="Do not open the report in a browser."
    )
    args = parser.parse_args(argv)

    try:
        client = LogfireClient()
    except RuntimeError as exc:
        print(f"✖ {exc}", file=sys.stderr)
        return 1

    if args.list:
        rows = client.list_recent_traces()
        if not rows:
            print("No agent runs found in the project.")
            return 0
        print("Recent agent runs:\n")
        for row in rows:
            dur = row.get("duration")
            suffix = f"  ({float(dur):.2f}s)" if dur else ""
            print(f"  {row['trace_id']}  {row.get('start_timestamp', '')}{suffix}")
        return 0

    trace_id = args.trace_id or client.latest_trace_id()
    if not trace_id:
        print("✖ No trace found in Logfire.", file=sys.stderr)
        return 1

    print(f"→ Fetching trace {trace_id} …")
    spans = client.fetch_trace(trace_id)
    if not spans:
        print("✖ Trace contains no spans.", file=sys.stderr)
        return 1

    report = parse_run(spans, trace_id)
    totals = report.totals
    cost = f", cost ${totals.total_cost_usd:.6f}" if report.meta.cost_known else ", cost unknown"
    print(
        f"→ Parsed: {totals.num_turns} turn(s), {totals.num_model_calls} model call(s), "
        f"{totals.num_tools} tool call(s), {totals.num_nested_agents} nested agent(s), "
        f"{totals.total_tokens} tokens{cost}"
    )

    out = Path(args.output).resolve()
    out.write_text(render_html(report), encoding="utf-8")
    print(f"✓ Report written: {out}")

    if not args.no_open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
