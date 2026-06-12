"""Render the recursive workflow payload into a self-contained, interactive HTML report.

All CSS/JS is embedded — the output is a single shareable HTML file that works
offline. The payload is injected as `const RUN = {...}` and the JS layer builds a
Figma-style, pan/zoom/drag block diagram with nested agent frames, a conversation
panel, a guided tour (auto + manual stepping) and full-detail inspectors.
"""

from __future__ import annotations

import json

from .models import WorkflowReport


def render_html(report: WorkflowReport) -> str:
    """Render a :class:`WorkflowReport` into a single self-contained HTML document."""
    payload = report.model_dump(mode="json")
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return _TEMPLATE.replace("/*__DATA__*/", data)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Workflow — agentcanvas</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 96'%3E%3Crect x='4' y='4' width='88' height='88' rx='22' fill='%230F1B33'/%3E%3Cpath d='M34 48H46' stroke='%234C7DF0' stroke-width='3.2' stroke-linecap='round'/%3E%3Cpath d='M58 32C50 32 50 48 46 48' stroke='%234C7DF0' stroke-width='3.2' fill='none' stroke-linecap='round'/%3E%3Cpath d='M58 64C50 64 50 48 46 48' stroke='%234C7DF0' stroke-width='3.2' fill='none' stroke-linecap='round'/%3E%3Ccircle cx='30' cy='48' r='7.5' fill='%234C7DF0'/%3E%3Ccircle cx='62' cy='32' r='6.5' fill='%2322B8A0'/%3E%3Ccircle cx='62' cy='64' r='6.5' fill='%23E0892B'/%3E%3C/svg%3E">
<style>
:root{
  --bg:#f5f4ef; --grid:#e5e3da; --surface:#ffffff;
  --ink:#11131a; --muted:#5d6470; --faint:#9aa0ad;
  --line:#e8e6df; --line-2:#d6d4cb;
  --accent:#e60a80;            /* Logfire magenta */
  --accent-soft:#fdeaf5;       /* magenta tint */
  --accent-deep:#b80766;
  /* one consistent accent across every node type */
  --user:var(--accent); --agent:var(--accent); --model:var(--accent); --tool:var(--accent); --output:var(--accent);
  --panel-w:420px;
  --shadow-sm:0 1px 2px rgba(15,27,51,.05), 0 1px 3px rgba(15,27,51,.06);
  --shadow-md:0 6px 18px rgba(15,27,51,.09), 0 2px 6px rgba(15,27,51,.05);
  --shadow-lg:0 20px 48px rgba(15,27,51,.16);
  --r:13px;
  --font:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:"SF Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{font-family:var(--font);background:var(--bg);color:var(--ink);
  -webkit-font-smoothing:antialiased;display:flex;flex-direction:column;height:100vh;overflow:hidden}
button{font-family:inherit}

/* ---------------- App bar ---------------- */
.appbar{display:flex;align-items:center;gap:22px;padding:0 22px;height:60px;
  background:var(--surface);border-bottom:1px solid var(--line);flex:none;z-index:30}
.brand{display:flex;align-items:center;gap:12px;min-width:0}
.mark{width:34px;height:34px;flex:none;display:block}
.mark svg{width:34px;height:34px;display:block}
.brand h1{font-size:14.5px;font-weight:650;margin:0;letter-spacing:-.01em}
.brand .s{font-size:12px;color:var(--muted);margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:42vw}
.brand .s b{color:var(--ink);font-weight:550}
.kpis{display:flex;align-items:stretch;margin-left:auto}
.kpi{padding:0 16px;display:flex;flex-direction:column;justify-content:center;border-left:1px solid var(--line);min-width:84px}
.kpi:first-child{border-left:none}
.kpi .l{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);font-weight:600;margin-bottom:3px}
.kpi .v{font-size:16.5px;font-weight:680;letter-spacing:-.01em;line-height:1}
.kpi .v small{font-size:11px;color:var(--muted);font-weight:500}
.kpi.cost .v{color:var(--accent)}

/* ---------------- Stage / canvas ---------------- */
.stage{position:relative;flex:1;overflow:hidden;background:
  radial-gradient(circle at 1px 1px, var(--grid) 1.3px, transparent 0) 0 0/24px 24px, var(--bg)}
.viewport{position:absolute;inset:0;cursor:grab;overflow:hidden}
.viewport.grabbing{cursor:grabbing}
.world{position:absolute;top:0;left:0;transform-origin:0 0;will-change:transform}
.world.animate{transition:transform .5s cubic-bezier(.22,.61,.36,1)}
svg#wires{position:absolute;top:0;left:0;overflow:visible;pointer-events:none;z-index:2}

/* ---------------- Frames (agent containers) ---------------- */
.frame{position:absolute;border:1.5px solid var(--line-2);border-radius:16px;background:rgba(229,227,218,.4);z-index:1}
.frame.nested{background:var(--accent-soft);border-color:#f3c8e2;border-style:dashed}
.frame .fhead{position:absolute;top:-13px;left:16px;display:flex;align-items:center;gap:9px;
  background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:5px 11px;box-shadow:var(--shadow-sm)}
.frame .fdot{width:8px;height:8px;border-radius:50%}
.frame .fname{font-size:12px;font-weight:650}
.frame .fmeta{font-size:11px;color:var(--muted);border-left:1px solid var(--line);padding-left:9px;margin-left:2px}
.frame .fturn{font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--faint)}

/* ---------------- Nodes ---------------- */
.node{position:absolute;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  box-shadow:var(--shadow-sm);
  transition:box-shadow .35s ease,border-color .35s ease,opacity .5s ease,filter .5s ease;
  z-index:3;overflow:hidden}
.node::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--nc)}
.node:hover{box-shadow:var(--shadow-md);border-color:var(--line-2)}
.node.sel{border-color:var(--nc);box-shadow:0 0 0 2px color-mix(in srgb,var(--nc) 32%,transparent),var(--shadow-md)}
.node.cur{box-shadow:0 0 0 3px color-mix(in srgb,var(--nc) 30%,transparent),var(--shadow-lg);border-color:var(--nc)}
.node.dim{opacity:.28;filter:saturate(.5)}
.nw-user{width:308px}.nw-model{width:304px}.nw-tool{width:256px}.nw-out{width:308px}

.nh{display:flex;align-items:center;gap:11px;padding:14px 16px 12px;cursor:grab}
.nh:active{cursor:grabbing}
.nh .ic{width:29px;height:29px;border-radius:8px;flex:none;display:grid;place-items:center;
  background:color-mix(in srgb,var(--nc) 12%,#fff);color:var(--nc)}
.nh .ic svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.9}
.nh .tt{min-width:0;flex:1}
.nh .role{font-size:9.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--nc);font-weight:700}
.nh h3{margin:1px 0 0;font-size:13px;font-weight:620;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nh .expand{margin-left:auto;width:24px;height:24px;border-radius:6px;border:1px solid var(--line);background:#fff;
  color:var(--muted);cursor:pointer;display:grid;place-items:center;flex:none}
.nh .expand:hover{background:#f2f3f7;color:var(--ink)}
.nh .expand svg{width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:2}
.nb{padding:0 16px 16px;font-size:12.5px;color:var(--muted);line-height:1.5}
.snippet{background:#fafbfc;border:1px solid var(--line);border-radius:9px;padding:9px 11px;color:#2c313c;
  font-size:12px;line-height:1.55;overflow:hidden;word-break:break-word;
  display:-webkit-box;-webkit-box-orient:vertical}
.snippet.clip{-webkit-line-clamp:4}

.pills{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.pill{display:flex;align-items:center;gap:5px;background:#f5f6f9;border:1px solid var(--line);
  border-radius:8px;padding:4px 9px;font-size:11px;color:#3b4150;font-weight:550;white-space:nowrap}
.pill.cost{color:var(--accent-deep);background:var(--accent-soft);border-color:#f7d2e8}
.pill.think{color:var(--accent-deep);background:var(--accent-soft);border-color:#f7d2e8}
.i-brain{width:13px;height:13px;vertical-align:-2px;display:inline-block;flex:none}
.pill b{font-weight:700;color:var(--ink)}
.tbar{height:7px;border-radius:6px;overflow:hidden;display:flex;background:#ecebe4;margin:3px 0 8px}
.tbar i{display:block;height:100%}
.tbar .in{background:color-mix(in srgb,var(--accent) 28%,#dcdacf)}
.tbar .out{background:var(--accent)}
.tbar .re{background:color-mix(in srgb,var(--accent) 50%,#ffffff)}
.tlegend{display:flex;gap:12px;font-size:10.5px;color:var(--muted)}
.tlegend i{width:7px;height:7px;border-radius:2px;display:inline-block;margin-right:4px;vertical-align:middle}
.tlegend i.in{background:color-mix(in srgb,var(--accent) 28%,#dcdacf)}
.tlegend i.out{background:var(--accent)}
.think{margin-top:12px;background:var(--accent-soft);border:1px solid #f7d2e8;border-radius:10px;padding:10px 12px}
.think .tk{font-size:9.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--accent-deep);font-weight:700;display:flex;align-items:center;gap:6px;margin-bottom:6px}
.think .tx{font-size:11.5px;color:#5a4150;line-height:1.55;overflow:hidden;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tchip{font-size:11px;font-weight:600;padding:4px 9px;border-radius:8px;background:var(--accent-soft);border:1px solid #f7d2e8;color:var(--accent-deep)}

.io .lab{font-size:9.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--faint);font-weight:650;margin:7px 0 3px}
.io .box{font-family:var(--mono);font-size:11px;background:#fafbfc;border:1px solid var(--line);border-radius:7px;
  padding:6px 9px;color:#363b46;word-break:break-word;max-height:50px;overflow:hidden;white-space:pre-wrap}
.io .arr{display:flex;align-items:center;justify-content:center;color:var(--tool);margin:4px 0;font-size:11px}
.nestedhint{margin-top:9px;font-size:11px;color:var(--tool);font-weight:600;display:flex;align-items:center;gap:6px}

.explain{display:none;margin-top:10px;font-size:11px;color:#46406f;background:#f0effb;
  border:1px solid #ddd9f6;border-radius:8px;padding:7px 9px;line-height:1.5}
body.explain-on .explain{display:block}
.explain b{color:#5b53c4}

/* ---------------- Toolbar ---------------- */
.toolbar{position:absolute;top:15px;left:15px;display:flex;align-items:center;gap:5px;
  background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:6px;box-shadow:var(--shadow-md);z-index:20}
.tb{height:33px;min-width:33px;padding:0 9px;border:none;background:transparent;border-radius:8px;cursor:pointer;
  display:flex;align-items:center;gap:7px;color:#3b4150;font-size:12.5px;font-weight:560}
.tb:hover{background:#f1f2f6}
.tb svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2}
.tb.primary{background:var(--accent);color:#fff}.tb.primary:hover{background:var(--accent-deep)}
.tb.on{background:var(--accent-soft);color:var(--accent)}
.tb-sep{width:1px;height:21px;background:var(--line);margin:0 2px}
.zlabel{font-size:12px;color:var(--muted);min-width:40px;text-align:center;font-variant-numeric:tabular-nums}

/* legend */
.legend{position:absolute;left:15px;bottom:15px;display:flex;gap:13px;flex-wrap:wrap;
  background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:8px 12px;box-shadow:var(--shadow-sm);z-index:10;font-size:11px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend .li{width:18px;height:18px;border-radius:5px;display:grid;place-items:center;background:var(--accent-soft);color:var(--accent)}
.legend .li svg{width:11px;height:11px;stroke:currentColor;fill:none;stroke-width:2}

/* ---------------- Narration (guided tour) ---------------- */
.narr{position:absolute;left:50%;bottom:18px;transform:translateX(-50%) translateY(140%);
  width:min(640px,92vw);background:var(--surface);border:1px solid var(--line);border-radius:14px;
  box-shadow:var(--shadow-lg);z-index:25;transition:transform .3s cubic-bezier(.4,0,.2,1);overflow:hidden}
.narr.show{transform:translateX(-50%)}
.narr .nbar{height:3px;background:var(--accent);width:0%;transition:width .3s}
.narr .ncontent{padding:14px 16px 12px}
.narr .ntop{display:flex;align-items:center;gap:9px;margin-bottom:6px}
.narr .nstep{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--faint)}
.narr .ndot{width:9px;height:9px;border-radius:50%}
.narr h4{margin:0;font-size:14px;font-weight:650}
.narr p{margin:5px 0 0;font-size:12.5px;color:var(--muted);line-height:1.55}
.narr .nctrl{display:flex;align-items:center;gap:8px;padding:10px 16px;border-top:1px solid var(--line);background:#fafbfc}
.narr .nbtn{height:32px;padding:0 13px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer;
  font-size:12.5px;font-weight:560;color:#3b4150;display:flex;align-items:center;gap:6px}
.narr .nbtn:hover{background:#f1f2f6}.narr .nbtn:disabled{opacity:.4;cursor:default}
.narr .nbtn.primary{background:var(--accent);color:#fff;border-color:transparent}
.narr .nhint{margin-left:auto;font-size:11px;color:var(--faint)}
kbd{font-family:var(--mono);font-size:10.5px;background:#eceef3;border:1px solid var(--line-2);border-bottom-width:2px;border-radius:5px;padding:1px 5px;color:#3b4150}

/* ---------------- Inspector & conversation panels ---------------- */
.panel{position:absolute;top:0;right:0;height:100%;width:var(--panel-w);max-width:96vw;background:var(--surface);
  border-left:1px solid var(--line);box-shadow:-14px 0 44px rgba(15,27,51,.12);transform:translateX(100%);
  transition:transform .26s cubic-bezier(.4,0,.2,1);z-index:35;display:flex;flex-direction:column}
.panel.open{transform:none}
.panel.resizing{transition:none;user-select:none}
.resize{position:absolute;left:-4px;top:0;bottom:0;width:9px;cursor:col-resize;z-index:5}
.resize::before{content:"";position:absolute;left:4px;top:0;bottom:0;width:2px;background:transparent;transition:background .15s}
.resize:hover::before,.panel.resizing .resize::before{background:var(--accent)}
.resize::after{content:"";position:absolute;left:1px;top:50%;transform:translateY(-50%);width:4px;height:34px;border-radius:3px;background:var(--line-2)}
.resize:hover::after{background:var(--accent)}
.ph{display:flex;align-items:center;gap:11px;padding:15px 17px;border-bottom:1px solid var(--line);flex:none}
.ph .ic{width:29px;height:29px;border-radius:8px;display:grid;place-items:center;background:color-mix(in srgb,var(--nc) 12%,#fff);color:var(--nc)}
.ph .ic svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.9}
.ph .role{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--nc);font-weight:700}
.ph h2{margin:1px 0 0;font-size:14px;font-weight:640}
.ph .x{margin-left:auto;width:31px;height:31px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer;color:var(--muted);font-size:17px;line-height:1}
.ph .x:hover{background:#f1f2f6}
.pbody{padding:17px;overflow:auto;font-size:13px}
.mb{margin-bottom:15px}
.field{margin-bottom:15px}
.field .fl{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);font-weight:650;margin-bottom:6px}
.field pre,.field .txt{margin:0;background:#fafbfc;border:1px solid var(--line);border-radius:9px;padding:10px 12px;
  font-family:var(--mono);font-size:12px;color:#2c313c;white-space:pre-wrap;word-break:break-word;line-height:1.55;max-height:320px;overflow:auto}
.field .txt{font-family:var(--font);font-size:13px;line-height:1.6}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.metric{background:#fafbfc;border:1px solid var(--line);border-radius:9px;padding:9px 11px}
.metric .ml{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--faint);font-weight:600}
.metric .mv{font-size:17px;font-weight:680;margin-top:3px;letter-spacing:-.01em}
.msg{border:1px solid var(--line);border-radius:9px;padding:9px 11px;margin-bottom:7px;background:#fff}
.msg .mr{font-size:9.5px;text-transform:uppercase;letter-spacing:.05em;font-weight:700;margin-bottom:4px}
.msg.thinking{background:#f8f5fd;border-style:dashed}
.msg .mc{font-size:12px;color:#2c313c;white-space:pre-wrap;word-break:break-word;line-height:1.5}
.toolitem{display:flex;gap:7px;align-items:center;font-size:11.5px;color:#3b4150;padding:5px 0;border-bottom:1px solid var(--line)}
.toolitem code{font-family:var(--mono);color:var(--accent-deep);font-size:11px}

/* conversation bubbles */
.bubble{margin-bottom:12px;display:flex;flex-direction:column;max-width:90%}
.bubble.user{align-self:flex-end;align-items:flex-end;margin-left:auto}
.bubble .who{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--faint);font-weight:650;margin-bottom:4px}
.bubble .txt{padding:10px 13px;border-radius:13px;font-size:12.5px;line-height:1.55;white-space:pre-wrap;word-break:break-word}
.bubble.user .txt{background:var(--accent);color:#fff;border-bottom-right-radius:4px}
.bubble.assistant .txt{background:#f1f2f6;color:#1f2330;border-bottom-left-radius:4px}
.bubble.tool .txt{background:var(--accent-soft);color:var(--accent-deep);font-size:11.5px;border:1px solid #f7d2e8}
.bubble .meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:5px}
.convflow{display:flex;flex-direction:column}
.thinkrow{margin-top:5px;font-size:11px;color:var(--accent-deep);background:var(--accent-soft);border:1px solid #f7d2e8;border-radius:8px;padding:7px 9px;white-space:pre-wrap;line-height:1.5}

/* modal for long content */
.modal-scrim{position:fixed;inset:0;background:rgba(20,28,56,.4);backdrop-filter:blur(2px);opacity:0;pointer-events:none;transition:.2s;z-index:50}
.modal-scrim.open{opacity:1;pointer-events:auto}
.modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-48%) scale(.97);opacity:0;pointer-events:none;
  width:min(720px,92vw);max-height:84vh;background:var(--surface);border-radius:16px;box-shadow:var(--shadow-lg);
  z-index:51;transition:.2s;display:flex;flex-direction:column;overflow:hidden}
.modal.open{transform:translate(-50%,-50%);opacity:1;pointer-events:auto}
.modal .mh{display:flex;align-items:center;gap:10px;padding:16px 18px;border-bottom:1px solid var(--line)}
.modal .mh h3{margin:0;font-size:15px;font-weight:650}
.modal .mh .x{margin-left:auto;width:31px;height:31px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer;color:var(--muted);font-size:17px}
.modal .mbody{padding:18px;overflow:auto;font-size:13.5px;line-height:1.65;white-space:pre-wrap;word-break:break-word;color:#262b38}

/* footer credit */
.credit{position:absolute;right:15px;bottom:15px;z-index:10;font-size:11.5px;color:var(--muted);text-decoration:none;
  background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:7px 12px;box-shadow:var(--shadow-sm);transition:color .15s,border-color .15s}
.credit b{color:var(--accent);font-weight:680}
.credit:hover{border-color:var(--accent)}

@media (max-width:760px){.kpis{display:none}.legend{display:none}}
</style>
</head>
<body>

<div class="appbar">
  <div class="brand">
    <div class="mark"><svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="4" width="88" height="88" rx="22" fill="#0F1B33"/>
      <path d="M34 48H46" stroke="#4C7DF0" stroke-width="3.2" stroke-linecap="round"/>
      <path d="M58 32C50 32 50 48 46 48" stroke="#4C7DF0" stroke-width="3.2" fill="none" stroke-linecap="round"/>
      <path d="M58 64C50 64 50 48 46 48" stroke="#4C7DF0" stroke-width="3.2" fill="none" stroke-linecap="round"/>
      <circle cx="30" cy="48" r="7.5" fill="#4C7DF0"/><circle cx="62" cy="32" r="6.5" fill="#22B8A0"/><circle cx="62" cy="64" r="6.5" fill="#E0892B"/></svg></div>
    <div><h1>Agent Workflow</h1><div class="s" id="sub"></div></div>
  </div>
  <div class="kpis" id="kpis"></div>
</div>

<div class="stage">
  <div class="viewport" id="viewport"><div class="world" id="world"><svg id="wires"></svg></div></div>

  <div class="toolbar">
    <button class="tb primary" id="play"><svg viewBox="0 0 24 24"><polygon points="6 4 20 12 6 20 6 4"/></svg>Tour</button>
    <button class="tb" id="step"><svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="15" y2="12"/><polyline points="11 8 15 12 11 16"/><line x1="19" y1="6" x2="19" y2="18"/></svg>Step</button>
    <div class="tb-sep"></div>
    <button class="tb" id="zoomOut"><svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/></svg></button>
    <span class="zlabel" id="zlabel">100%</span>
    <button class="tb" id="zoomIn"><svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></button>
    <button class="tb" id="fit"><svg viewBox="0 0 24 24"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3m13-5v3a2 2 0 0 1-2 2h-3"/></svg></button>
    <div class="tb-sep"></div>
    <button class="tb" id="convBtn"><svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>Conversation</button>
  </div>

  <div class="legend" id="legend"></div>

  <div class="narr" id="narr">
    <div class="nbar" id="nbar"></div>
    <div class="ncontent">
      <div class="ntop"><span class="ndot" id="ndot"></span><span class="nstep" id="nstep"></span></div>
      <h4 id="ntitle"></h4><p id="ntext"></p>
    </div>
    <div class="nctrl">
      <button class="nbtn" id="nprev">‹ Back</button>
      <button class="nbtn primary" id="nnext">Next ›</button>
      <button class="nbtn" id="nauto">▶ Auto</button>
      <span class="nhint"><kbd>Space</kbd>/<kbd>→</kbd> next · <kbd>←</kbd> back · <kbd>Esc</kbd> exit</span>
      <button class="nbtn" id="nclose">Exit</button>
    </div>
  </div>

  <aside class="panel" id="inspector"><div class="resize" data-resize></div><div class="ph" id="ih"></div><div class="pbody" id="ibody"></div></aside>
  <aside class="panel" id="conv"><div class="resize" data-resize></div>
    <div class="ph" style="--nc:var(--agent)"><div class="ic"><svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
      <div><div class="role">Transcript</div><h2>Conversation</h2></div><button class="x" id="convClose">×</button></div>
    <div class="pbody" id="convBody"></div>
  </aside>

  <a class="credit" href="https://vstorm.co" target="_blank" rel="noopener">Made by <b>Vstorm.co</b></a>
</div>

<div class="modal-scrim" id="mscrim"></div>
<div class="modal" id="modal"><div class="mh"><h3 id="mtitle"></h3><button class="x" id="mclose">×</button></div><div class="mbody" id="mbody"></div></div>

<script>
const RUN = /*__DATA__*/;
</script>
<script>
/* ============================ helpers ============================ */
const $=(s,r=document)=>r.querySelector(s);
const el=(t,c,h)=>{const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e;};
const esc=s=>String(s==null?"":s).replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]));
const nfmt=n=>Number(n||0).toLocaleString("en-US");
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function fmtCost(v){ if(v==null)return "—"; if(v===0)return "$0"; if(v<0.01)return "$"+v.toFixed(6); return "$"+v.toFixed(4); }
function fmtCostShort(v){ if(v==null)return "—"; if(v===0)return "$0"; if(v<0.01)return "$"+v.toFixed(4); return "$"+v.toFixed(3); }
function clean(s){ return String(s==null?"":s).replace(/\*\*/g,"").replace(/`/g,"").replace(/^#{1,6}\s+/gm,"").replace(/^\s*[-*]\s+/gm,"• "); }
function fmtArgs(a){ if(a==null)return "{}"; if(typeof a==="object")return JSON.stringify(a);
  if(typeof a==="string"){try{return JSON.stringify(JSON.parse(a));}catch(e){return a;}} return String(a); }
const ACCENT="#e60a80";
const COL={user:ACCENT,agent:ACCENT,model:ACCENT,tool:ACCENT,output:ACCENT};
const ICON={
  user:'<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  agent:'<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M9 9h6v6H9z"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/></svg>',
  model:'<svg viewBox="0 0 24 24"><path d="M12 3l1.9 4.8L19 9l-4.1 3 1.3 5L12 14.8 7.8 17l1.3-5L5 9l5.1-1.2z"/></svg>',
  tool:'<svg viewBox="0 0 24 24"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.1-2.1z"/></svg>',
  output:'<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>'
};
const EXPAND='<svg viewBox="0 0 24 24"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>';
const BRAIN='<svg class="i-brain" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 3.5a2.5 2.5 0 0 0-2.5 2.5 2.5 2.5 0 0 0-1.5 4.5A2.5 2.5 0 0 0 6 15a2.5 2.5 0 0 0 3.5 2.3V3.5z"/><path d="M14.5 3.5A2.5 2.5 0 0 1 17 6a2.5 2.5 0 0 1 1.5 4.5A2.5 2.5 0 0 1 18 15a2.5 2.5 0 0 1-3.5 2.3V3.5z"/></svg>';

const world=$("#world"), wires=$("#wires"), viewport=$("#viewport");
const M=RUN.meta, T=RUN.totals;

/* ---------------- header ---------------- */
$("#sub").innerHTML = `Trace <b>${esc((M.trace_id||"").slice(0,16))}…</b> · <b>${esc(M.model||"model")}</b> · ${T.num_turns} turn(s)`;
$("#kpis").innerHTML = [
  {l:"Total cost",v:M.cost_known?fmtCost(T.total_cost_usd):"—",cls:"cost"},
  {l:"Tokens",v:nfmt(T.total_tokens)},
  {l:"Reasoning",v:nfmt(T.reasoning_tokens)},
  {l:"Tool calls",v:T.num_tools},
  {l:"Sub-agents",v:T.num_nested_agents},
  {l:"Duration",v:(M.duration_s?M.duration_s.toFixed(1):"?")+"<small>s</small>"},
].map(k=>`<div class="kpi ${k.cls||""}"><div class="l">${k.l}</div><div class="v">${k.v}</div></div>`).join("");

$("#legend").innerHTML = [
  ["user", "User"], ["agent", "Agent"], ["model", "Model call"], ["tool", "Tool"], ["output", "Answer"],
].map(([k, label]) => `<span><span class="li">${ICON[k]}</span>${label}</span>`).join("");

/* ============================ node + graph construction ============================ */
const N={};        // id -> {el,w,h,x,y,kind,data}
const edges=[];    // {from,to,kind:'flow'|'spawn'|'turn'}
const frames=[];   // {el,x,y,w,h,depth}
const seq=[];      // ordered ids for guided tour
let uid=0; const nid=()=>"n"+(uid++);

function mkNode(kind, cls, inner, data){
  const id=nid(); const e=el("div","node nw-"+cls); e.id=id; e.style.setProperty("--nc",COL[kind]);
  e.innerHTML=inner; world.appendChild(e); N[id]={el:e,kind,data:data||{}}; return id;
}
function head(kind,role,title,expandTarget){
  return `<div class="nh" data-drag><div class="ic">${ICON[kind]}</div>
    <div class="tt"><div class="role">${esc(role)}</div><h3>${esc(title)}</h3></div>
    ${expandTarget?`<button class="expand" data-expand>${EXPAND}</button>`:""}</div>`;
}
function snip(text,clip=true){ const t=clean(text); return `<div class="snippet ${clip?'clip':''}">${esc(t||"—")}</div>`; }

/* build one round (model) node */
function buildRound(rnd, turnNo){
  const decides=rnd.decided_tool_calls&&rnd.decided_tool_calls.length;
  const tot=Math.max(rnd.input_tokens+rnd.output_tokens,1);
  const pills=`<div class="pills">
    <span class="pill"><b>${nfmt(rnd.input_tokens+rnd.output_tokens)}</b> tok</span>
    ${M.cost_known&&rnd.cost_usd!=null?`<span class="pill cost">${fmtCostShort(rnd.cost_usd)}</span>`:""}
    ${rnd.reasoning_tokens?`<span class="pill think">${BRAIN} ${nfmt(rnd.reasoning_tokens)}</span>`:""}
    <span class="pill">${rnd.duration_s?rnd.duration_s.toFixed(2):"?"}s</span></div>`;
  const tbar=`<div class="tbar"><i class="in" style="width:${rnd.input_tokens/tot*100}%"></i><i class="out" style="width:${rnd.output_tokens/tot*100}%"></i></div>
    <div class="tlegend"><span><i class="in"></i>in ${nfmt(rnd.input_tokens)}</span><span><i class="out"></i>out ${nfmt(rnd.output_tokens)}</span></div>`;
  const think=(rnd.thinking&&rnd.thinking.length)?
    `<div class="think"><div class="tk">${BRAIN} Reasoning <span style="color:var(--faint);font-weight:600">(${rnd.reasoning_tokens} tok)</span></div><div class="tx">${esc(clean(rnd.thinking[0]))}</div></div>`:"";
  let extra="";
  let role,title,explain;
  if(decides){
    role="Model · planning"; title="Model decides what to do";
    extra=`<div class="chips">${rnd.decided_tool_calls.map(t=>`<span class="tchip">${esc(t)}</span>`).join("")}</div>`;
    explain=`The model reads the request, <b>reasons</b> about it, and decides which tools to call. It does not run them yet — it only requests them.`;
  }else{
    role="Model · responding"; title="Model writes the answer";
    if(rnd.text_out&&rnd.text_out.length) extra=snip(rnd.text_out[rnd.text_out.length-1]);
    explain=`The model received the tool results and <b>synthesises</b> them into a clear answer. This step is often the most expensive — its input carries everything gathered so far.`;
  }
  const id=mkNode("model","model",
    head("model",role,title,true)+`<div class="nb">${pills}${tbar}${think}${extra}<div class="explain">${explain}</div></div>`,
    {type:"model",rnd});
  return id;
}

/* build a tool node */
function buildTool(tool){
  const nestedHint=tool.nested?`<div class="nestedhint">↳ runs sub-agent “${esc(tool.nested.agent_name)}”</div>`:"";
  const inner=head("tool","Tool",tool.name,true)+
    `<div class="nb"><div class="io"><div class="lab">Input</div><div class="box">${esc(fmtArgs(tool.arguments))}</div>
      <div class="arr">↓</div><div class="lab">Output</div><div class="box">${esc(tool.result||"—")}</div></div>
      <div class="pills" style="margin:9px 0 0"><span class="pill">${(tool.duration_s*1000).toFixed(0)} ms</span></div>
      ${nestedHint}
      <div class="explain"><b>A tool</b> is real code the agent invoked. The model chose the input; the function returned the output.${tool.nested?" Here the tool is itself <b>another agent</b> with its own tools — shown in the frame below.":""}</div></div>`;
  return mkNode("tool","tool",inner,{type:"tool",tool});
}

/* recursively build an agent (turn or nested). Returns a descriptor for layout. */
function buildAgent(agent, isTurn, turnNo){
  const desc={kind:"agentframe",agent,isTurn,turnNo,userId:null,rounds:[],answerId:null,children:[]};
  if(isTurn){
    desc.userId=mkNode("user","user",
      head("user","User message",turnNo===0?"User request":"Follow-up",true)+
      `<div class="nb">${snip(agent.user_prompt)}<div class="explain">This is what the user typed in turn ${turnNo+1}. The agent treats it as the goal for this turn.</div></div>`,
      {type:"user",text:agent.user_prompt});
    seq.push(desc.userId);
  }
  agent.rounds.forEach(rnd=>{
    const mId=buildRound(rnd,turnNo); seq.push(mId);
    const rd={modelId:mId,tools:[]};
    rnd.tools.forEach(tool=>{
      const tId=buildTool(tool); seq.push(tId);
      const td={toolId:tId,nested:null};
      if(tool.nested){ td.nested=buildAgent(tool.nested,false); desc.children.push(td.nested);
        edges.push({from:tId,to:td.nested.frameAnchor,kind:"spawn"}); }
      rd.tools.push(td);
    });
    desc.rounds.push(rd);
  });
  // answer node for turns
  if(isTurn){
    desc.answerId=mkNode("output","out",
      head("output","Answer",`Turn ${turnNo+1} result`,true)+
      `<div class="nb">${snip(agent.final_output)}<div class="explain">The final answer the user sees for this turn.</div></div>`,
      {type:"output",text:agent.final_output,agent});
    seq.push(desc.answerId);
  }
  // frame element + anchor id
  const fid="f"+(uid++);
  desc.frameId=fid; desc.frameAnchor=fid;
  return desc;
}

/* build edges within an agent descriptor */
function buildEdges(desc){
  let prev = desc.userId?[desc.userId]:[];
  desc.rounds.forEach((rd,ri)=>{
    prev.forEach(p=>edges.push({from:p,to:rd.modelId,kind:"flow"}));
    if(rd.tools.length){
      rd.tools.forEach(td=>edges.push({from:rd.modelId,to:td.toolId,kind:"flow"}));
      prev=rd.tools.map(td=>td.toolId);
    }else prev=[rd.modelId];
  });
  if(desc.answerId){ prev.forEach(p=>edges.push({from:p,to:desc.answerId,kind:"flow"})); }
  desc.children.forEach(buildEdges);
}

const turnDescs=RUN.turns.map((t,i)=>buildAgent(t,true,i));
turnDescs.forEach(buildEdges);
// connect turns (conversation continues)
for(let i=1;i<turnDescs.length;i++){
  const a=turnDescs[i-1].answerId, b=turnDescs[i].userId;
  if(a&&b) edges.push({from:a,to:b,kind:"turn"});
}

/* ============================ layout (measure → place, recursive frames) ============================ */
const FPAD=24, FHEAD=22, GAPX=90, GAPY=34, TURN_GAP=78;
function measure(){ for(const id in N){ N[id].w=N[id].el.offsetWidth; N[id].h=N[id].el.offsetHeight; } }
function setpos(id,x,y){ const n=N[id]; n.x=x; n.y=y; n.el.style.left=x+"px"; n.el.style.top=y+"px"; }

/* --- pass 1: compute sizes bottom-up (positions are independent of placement) --- */
function sizeAgent(desc){
  let w=0, h=0, first=true;
  const addW=width=>{ w+=(first?0:GAPX)+width; first=false; };
  if(desc.userId){ addW(N[desc.userId].w); h=Math.max(h,N[desc.userId].h); }
  desc._rsize=[];
  desc.rounds.forEach(rd=>{
    const mw=N[rd.modelId].w, mh=N[rd.modelId].h;
    if(rd.tools.length){
      let colW=0, colH=0;
      rd.tools.forEach((td,i)=>{
        let sw=N[td.toolId].w, sh=N[td.toolId].h;
        if(td.nested){ const ns=sizeAgent(td.nested); sw=Math.max(sw,ns.w); sh+=GAPY+ns.h; }
        td._slot={w:sw,h:sh};
        colW=Math.max(colW,sw); colH+=(i?GAPY:0)+sh;
      });
      addW(mw+GAPX+colW); h=Math.max(h,mh,colH);
      desc._rsize.push({colW,colH});
    }else{ addW(mw); h=Math.max(h,mh); desc._rsize.push(null); }
  });
  if(desc.answerId){ addW(N[desc.answerId].w); h=Math.max(h,N[desc.answerId].h); }
  desc._size={w:w+2*FPAD, h:h+FHEAD+2*FPAD, contentW:w, contentH:h};
  return desc._size;
}

/* --- pass 2: place top-down; the spine is vertically centred on each tool column --- */
function placeAgent(desc, ax, ay){
  const sz=desc._size, C=ay+FHEAD+FPAD+sz.contentH/2;
  let x=ax+FPAD;
  if(desc.userId){ setpos(desc.userId,x,C-N[desc.userId].h/2); x+=N[desc.userId].w+GAPX; }
  desc.rounds.forEach((rd,ri)=>{
    const mw=N[rd.modelId].w, mh=N[rd.modelId].h, rs=desc._rsize[ri];
    setpos(rd.modelId,x,C-mh/2);
    if(rs){
      const colX=x+mw+GAPX; let ty=C-rs.colH/2;
      rd.tools.forEach(td=>{
        setpos(td.toolId, colX+(rs.colW-N[td.toolId].w)/2, ty);
        if(td.nested) placeAgent(td.nested, colX+(rs.colW-td.nested._size.w)/2, ty+N[td.toolId].h+GAPY);
        ty+=td._slot.h+GAPY;
      });
      x=colX+rs.colW+GAPX;
    }else x+=mw+GAPX;
  });
  if(desc.answerId){ setpos(desc.answerId,x,C-N[desc.answerId].h/2); }
  desc._rect={x:ax,y:ay,w:sz.w,h:sz.h};
}

let worldW=0, worldH=0;
function layoutAll(){
  measure();
  let y=FPAD; worldW=0;
  turnDescs.forEach(d=>sizeAgent(d));
  turnDescs.forEach(d=>{ placeAgent(d, FPAD, y); y=d._rect.y+d._rect.h+TURN_GAP; worldW=Math.max(worldW,d._rect.x+d._rect.w); });
  worldH=y;
  // build frame DOM
  frames.length=0; world.querySelectorAll(".frame").forEach(f=>f.remove());
  function frameFor(desc,depth){
    const r=desc._rect; const f=el("div","frame"+(depth>0?" nested":""));
    f.id=desc.frameId;
    f.style.left=r.x+"px"; f.style.top=r.y+"px"; f.style.width=r.w+"px"; f.style.height=r.h+"px";
    const a=desc.agent;
    const meta=`${a.rounds.length} call(s)`+(M.cost_known? " · "+fmtCost(sumCost(a)) : "");
    f.innerHTML=`<div class="fhead"><span class="fdot" style="background:${COL.agent}"></span>
      <span class="fname">${esc(a.agent_name)}</span>
      <span class="fmeta">${meta}</span>
      ${desc.isTurn?`<span class="fturn">· Turn ${desc.turnNo+1}</span>`:`<span class="fturn">· sub-agent</span>`}</div>`;
    world.insertBefore(f,world.firstChild.nextSibling); // behind nodes, above svg base
    frames.push({el:f,desc,depth});
    desc.children.forEach(c=>frameFor(c,depth+1));
  }
  turnDescs.forEach(d=>frameFor(d,0));
  world.style.width=worldW+"px"; world.style.height=worldH+"px";
  drawWires();
}
function sumCost(a){ let c=0; a.rounds.forEach(r=>{if(r.cost_usd)c+=r.cost_usd;}); return c; }

/* ============================ wires ============================ */
function rect(id){ const n=N[id]; if(n)return {x:n.x,y:n.y,w:n.w,h:n.h,t:'node'};
  const f=frames.find(f=>f.desc.frameId===id); if(f){const r=f.desc._rect;return{x:r.x,y:r.y,w:r.w,h:r.h,t:'frame'};} return null; }
function drawWires(){
  wires.setAttribute("width",worldW); wires.setAttribute("height",worldH);
  wires.setAttribute("viewBox",`0 0 ${worldW} ${worldH}`);
  let defs=`<defs>
    <marker id="arr" markerWidth="9" markerHeight="9" refX="6.5" refY="4.5" orient="auto"><path d="M1 1 L8 4.5 L1 8" fill="none" stroke="#aab2c4" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>
    <marker id="arrT" markerWidth="9" markerHeight="9" refX="6.5" refY="4.5" orient="auto"><path d="M1 1 L8 4.5 L1 8" fill="none" stroke="#e60a80" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>`;
  let p="";
  edges.forEach((e,i)=>{
    const a=rect(e.from), b=rect(e.to); if(!a||!b)return;
    let d, stroke="#c3c9d6", w=1.7, dash="", marker="url(#arr)";
    if(e.kind==="spawn"){ // tool bottom -> frame top
      const sx=a.x+a.w/2, sy=a.y+a.h, tx=b.x+40, ty=b.y;
      d=`M ${sx} ${sy} C ${sx} ${sy+30}, ${tx} ${ty-30}, ${tx} ${ty}`;
      stroke="#e60a80"; dash="5 4"; marker="url(#arr)";
    }else if(e.kind==="turn"){ // answer -> next user (long)
      const sx=a.x+a.w/2, sy=a.y+a.h, tx=b.x+b.w/2, ty=b.y;
      d=`M ${sx} ${sy} C ${sx} ${sy+40}, ${tx} ${ty-40}, ${tx} ${ty}`;
      stroke="#e60a80"; dash="2 5"; w=2; marker="url(#arrT)";
    }else{ // flow: right -> left
      const s={x:a.x+a.w,y:a.y+a.h/2}, t={x:b.x,y:b.y+b.h/2};
      const dx=Math.max(30,(t.x-s.x)*0.5);
      d=`M ${s.x} ${s.y} C ${s.x+dx} ${s.y}, ${t.x-dx} ${t.y}, ${t.x} ${t.y}`;
    }
    p+=`<path class="wire" data-from="${e.from}" data-to="${e.to}" d="${d}" fill="none" stroke="${stroke}" stroke-width="${w}" ${dash?`stroke-dasharray="${dash}"`:""} marker-end="${marker}"/>`;
  });
  wires.innerHTML=defs+p;
}

/* ============================ pan / zoom / drag ============================ */
let view={x:0,y:0,k:1};
function apply(){ world.style.transform=`translate(${view.x}px,${view.y}px) scale(${view.k})`; $("#zlabel").textContent=Math.round(view.k*100)+"%"; }
function setAnimate(on){ world.classList.toggle("animate", on); }
function fit(){ const r=viewport.getBoundingClientRect();
  const k=clamp(Math.min((r.width-70)/worldW,(r.height-80)/worldH),0.18,1.5);
  view.k=k; view.x=(r.width-worldW*k)/2; view.y=Math.max(20,(r.height-worldH*k)/2); apply(); }
function zoomAt(cx,cy,f){ const k2=clamp(view.k*f,0.18,2.4); const wx=(cx-view.x)/view.k,wy=(cy-view.y)/view.k;
  view.x=cx-wx*k2; view.y=cy-wy*k2; view.k=k2; apply(); }
viewport.addEventListener("wheel",e=>{e.preventDefault();setAnimate(false);const r=viewport.getBoundingClientRect();zoomAt(e.clientX-r.left,e.clientY-r.top,e.deltaY<0?1.1:1/1.1);},{passive:false});
$("#zoomIn").onclick=()=>{const r=viewport.getBoundingClientRect();zoomAt(r.width/2,r.height/2,1.2);};
$("#zoomOut").onclick=()=>{const r=viewport.getBoundingClientRect();zoomAt(r.width/2,r.height/2,1/1.2);};
$("#fit").onclick=fit;

let pan=null, nodeDrag=null, justDragged=false, justPanned=false;
viewport.addEventListener("pointerdown",e=>{
  setAnimate(false);
  const handle=e.target.closest("[data-drag]");
  if(handle){ const node=handle.closest(".node"); const n=N[node.id];
    nodeDrag={id:node.id,sx:e.clientX,sy:e.clientY,ox:n.x,oy:n.y,moved:false};
    viewport.setPointerCapture(e.pointerId); e.preventDefault(); return; }
  if(e.target.closest(".node")||e.target.closest(".panel")||e.target.closest(".narr"))return;
  pan={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y,moved:false}; viewport.classList.add("grabbing"); viewport.setPointerCapture(e.pointerId);
});
viewport.addEventListener("pointermove",e=>{
  if(nodeDrag){ const dx=(e.clientX-nodeDrag.sx)/view.k, dy=(e.clientY-nodeDrag.sy)/view.k;
    if(Math.abs(dx)+Math.abs(dy)>2)nodeDrag.moved=true;
    setpos(nodeDrag.id,nodeDrag.ox+dx,nodeDrag.oy+dy); drawWires(); return; }
  if(pan){ if(Math.abs(e.clientX-pan.x)+Math.abs(e.clientY-pan.y)>3)pan.moved=true;
    view.x=pan.vx+(e.clientX-pan.x); view.y=pan.vy+(e.clientY-pan.y); apply(); }
});
viewport.addEventListener("pointerup",e=>{
  if(nodeDrag&&nodeDrag.moved){ justDragged=true; setTimeout(()=>{justDragged=false;},60); }
  justPanned=!!(pan&&pan.moved); if(justPanned)setTimeout(()=>{justPanned=false;},0);
  pan=null; nodeDrag=null; viewport.classList.remove("grabbing");
});

/* ============================ inspector ============================ */
const inspector=$("#inspector");
function openInspector(kind,role,title,body){
  $("#ih").style.setProperty("--nc",COL[kind]);
  $("#ih").innerHTML=`<div class="ic">${ICON[kind]}</div><div><div class="role">${esc(role)}</div><h2>${esc(title)}</h2></div><button class="x" id="ix">×</button>`;
  $("#ibody").innerHTML=body; inspector.classList.add("open"); $("#ix").onclick=closePanels;
  $("#conv").classList.remove("open");
}
function closePanels(){ inspector.classList.remove("open"); $("#conv").classList.remove("open");
  Object.values(N).forEach(n=>n.el.classList.remove("sel")); }
function modelInspector(r){
  const msgs=[];
  (r.thinking||[]).forEach(t=>msgs.push(`<div class="msg thinking"><div class="mr" style="color:var(--accent-deep)">reasoning</div><div class="mc">${esc(t)}</div></div>`));
  (r.decided_tool_calls||[]).forEach(t=>msgs.push(`<div class="msg"><div class="mr" style="color:var(--accent-deep)">tool call</div><div class="mc">${esc(t)}</div></div>`));
  (r.text_out||[]).forEach(t=>msgs.push(`<div class="msg"><div class="mr" style="color:#5b53c4">text</div><div class="mc">${esc(t)}</div></div>`));
  const tools=(r.available_tools||[]).map(t=>`<div class="toolitem"><code>${esc(t.name)}</code><span style="color:var(--muted)">${esc((t.description||"").slice(0,70))}</span></div>`).join("");
  return `<div class="grid2 mb">
    <div class="metric"><div class="ml">Input tokens</div><div class="mv">${nfmt(r.input_tokens)}</div></div>
    <div class="metric"><div class="ml">Output tokens</div><div class="mv">${nfmt(r.output_tokens)}</div></div>
    <div class="metric"><div class="ml">Reasoning tok</div><div class="mv">${nfmt(r.reasoning_tokens)}</div></div>
    <div class="metric"><div class="ml">Duration</div><div class="mv">${r.duration_s?r.duration_s.toFixed(2):"?"}<small style="font-size:12px;color:var(--muted)">s</small></div></div>
  </div>
  ${M.cost_known&&r.cost_usd!=null?`<div class="field"><div class="fl">Cost (genai-prices)</div><pre>input:  ${r.cost_input_usd!=null?"$"+r.cost_input_usd.toFixed(6):"—"}
output: ${r.cost_output_usd!=null?"$"+r.cost_output_usd.toFixed(6):"—"}
total:  ${fmtCost(r.cost_usd)}</pre></div>`:""}
  <div class="field"><div class="fl">Request</div><pre>model:    ${esc(r.model)}
provider: ${esc(r.provider||"—")} (${esc(r.server||"—")})
finish:   ${esc((r.finish_reasons||[]).join(", ")||"—")}
thinking: ${esc(JSON.stringify(r.thinking_config||"default"))}
response: ${esc(r.response_id||"—")}</pre></div>
  ${tools?`<div class="field"><div class="fl">Tools available to the model (${r.available_tools.length})</div>${tools}</div>`:""}
  <div class="field"><div class="fl">Output</div>${msgs.join("")||'<div class="txt">—</div>'}</div>`;
}
function toolInspector(t){
  return `<div class="field"><div class="fl">Tool</div><pre>${esc(t.name)}</pre></div>
    <div class="field"><div class="fl">Arguments (input)</div><pre>${esc(fmtArgs(t.arguments))}</pre></div>
    <div class="field"><div class="fl">Result (output)</div><pre>${esc(t.result||"—")}</pre></div>
    <div class="field"><div class="fl">Duration</div><pre>${(t.duration_s*1000).toFixed(1)} ms</pre></div>
    ${t.nested?`<div class="field"><div class="fl">Nested agent</div><pre>${esc(t.nested.agent_name)} — ${t.nested.rounds.length} model call(s), ${t.nested.rounds.reduce((s,r)=>s+r.tools.length,0)} tool(s)</pre></div>`:""}`;
}
function openFor(id){
  const n=N[id]; if(!n)return; const d=n.data;
  Object.values(N).forEach(o=>o.el.classList.remove("sel")); n.el.classList.add("sel");
  if(d.type==="model")openInspector("model","Model call","Request to the model",modelInspector(d.rnd));
  else if(d.type==="tool")openInspector("tool","Tool",d.tool.name,toolInspector(d.tool));
  else if(d.type==="user")openInspector("user","User message","Prompt",`<div class="field"><div class="fl">Text</div><div class="txt">${esc(d.text||"—")}</div></div>`);
  else if(d.type==="output")openInspector("output","Answer","Final answer",
    `<div class="field"><div class="fl">Answer</div><div class="txt">${esc(d.text||"—")}</div></div>
     <div class="field"><div class="fl">Agent</div><pre>${esc(d.agent.agent_name)} · ${esc(d.agent.model)}</pre></div>`);
}
// node click → inspector (unless dragged)
Object.keys(N).forEach(id=>{
  N[id].el.addEventListener("click",e=>{ if(justDragged)return;
    if(e.target.closest("[data-expand]")){ openModal(id); return; } openFor(id); });
});

/* ============================ modal (full content) ============================ */
function fullTextFor(id){ const d=N[id].data;
  if(d.type==="user")return {t:"User message",x:d.text};
  if(d.type==="output")return {t:"Final answer",x:d.text};
  if(d.type==="tool")return {t:"Tool: "+d.tool.name,x:"INPUT\n"+fmtArgs(d.tool.arguments)+"\n\nOUTPUT\n"+(d.tool.result||"—")};
  if(d.type==="model"){ const r=d.rnd; let s="";
    if(r.thinking&&r.thinking.length)s+="REASONING\n"+r.thinking.join("\n\n")+"\n\n";
    if(r.text_out&&r.text_out.length)s+="ANSWER\n"+r.text_out.join("\n");
    if(r.decided_tool_calls&&r.decided_tool_calls.length)s+="TOOL CALLS\n"+r.decided_tool_calls.join(", ");
    return {t:"Model call",x:s||"—"}; }
  return {t:"Details",x:"—"};
}
function openModal(id){ const f=fullTextFor(id); $("#mtitle").textContent=f.t; $("#mbody").textContent=f.x;
  $("#mscrim").classList.add("open"); $("#modal").classList.add("open"); }
function closeModal(){ $("#mscrim").classList.remove("open"); $("#modal").classList.remove("open"); }
$("#mscrim").onclick=closeModal; $("#mclose").onclick=closeModal;

/* ============================ conversation panel ============================ */
function renderConversation(){
  const flow=el("div","convflow");
  (RUN.conversation||[]).forEach(m=>{
    if(m.role==="user")flow.appendChild(el("div","bubble user",`<div class="who">User</div><div class="txt">${esc(m.text)}</div>`));
    else if(m.role==="tool")flow.appendChild(el("div","bubble tool",`<div class="who">Tools</div><div class="txt">${esc(m.text)}</div>`));
    else{
      let meta="";
      if(m.tool_calls&&m.tool_calls.length)meta=`<div class="meta">${m.tool_calls.map(t=>`<span class="tchip">${esc(t)}</span>`).join("")}</div>`;
      let think=(m.thinking&&m.thinking.length)?`<div class="thinkrow">${BRAIN} ${esc(clean(m.thinking[0]))}</div>`:"";
      const txt=m.text?`<div class="txt">${esc(m.text)}</div>`:`<div class="txt" style="opacity:.6">(used tools — see chips)</div>`;
      flow.appendChild(el("div","bubble assistant",`<div class="who">Assistant</div>${txt}${meta}${think}`));
    }
  });
  $("#convBody").innerHTML=""; $("#convBody").appendChild(flow);
}
$("#convBtn").onclick=()=>{ renderConversation(); $("#conv").classList.toggle("open"); inspector.classList.remove("open"); };
$("#convClose").onclick=()=>$("#conv").classList.remove("open");

/* resizable side panels */
let resizing=null;
document.querySelectorAll("[data-resize]").forEach(h=>{
  h.addEventListener("pointerdown",e=>{ const panel=h.closest(".panel"); resizing=panel;
    panel.classList.add("resizing"); h.setPointerCapture(e.pointerId); e.preventDefault(); e.stopPropagation(); });
  h.addEventListener("pointermove",e=>{ if(!resizing)return;
    const w=clamp(window.innerWidth-e.clientX, 330, Math.min(860, window.innerWidth-60));
    document.documentElement.style.setProperty("--panel-w", w+"px"); });
  h.addEventListener("pointerup",()=>{ if(resizing){resizing.classList.remove("resizing"); resizing=null;} });
});

/* ============================ guided tour (auto + manual) ============================ */
const narr=$("#narr");
const tour={active:false,i:0,auto:false,timer:null};
function stepTitle(id){ const d=N[id].data;
  if(d.type==="user")return ["User message","The starting goal for this turn."];
  if(d.type==="model"){ const r=d.rnd; return (r.decided_tool_calls&&r.decided_tool_calls.length)
    ? ["Model decides", "The model reasons and chooses which tools to call ("+r.decided_tool_calls.join(", ")+")."]
    : ["Model responds", "The model turns the gathered results into the final answer."]; }
  if(d.type==="tool")return ["Tool: "+d.tool.name, d.tool.nested?"This tool runs another agent with its own tools.":"Real code runs and returns a result to the model."];
  if(d.type==="output")return ["Answer","The final response the user receives for this turn."];
  return ["Step",""];
}
function dimAll(on){ Object.values(N).forEach(n=>n.el.classList.toggle("dim",on)); }
function showStep(){
  const id=seq[tour.i]; if(!id)return;
  Object.values(N).forEach((n,k)=>{ n.el.classList.remove("cur"); });
  // reveal up to i, dim the rest
  seq.forEach((sid,k)=>{ N[sid].el.classList.toggle("dim", k>tour.i); });
  const n=N[id]; n.el.classList.add("cur");
  const [title,text]=stepTitle(id);
  $("#nstep").textContent=`Step ${tour.i+1} / ${seq.length}`;
  $("#ndot").style.background=COL[n.kind];
  $("#ntitle").textContent=title; $("#ntext").textContent=text;
  $("#nbar").style.width=((tour.i+1)/seq.length*100)+"%";
  $("#nprev").disabled=tour.i===0; $("#nnext").disabled=tour.i>=seq.length-1;
  centerOn(id);
}
function centerOn(id){ const n=N[id]; const r=viewport.getBoundingClientRect();
  const cx=(n.x+n.w/2)*view.k, cy=(n.y+n.h/2)*view.k;
  setAnimate(true);  // smooth glide to the focused node
  view.x=r.width/2-cx; view.y=r.height/2-cy-40; apply(); }
function startTour(auto){
  tour.active=true; tour.i=0; tour.auto=auto; document.body.classList.add("explain-on");
  layoutAll();   // explain captions appear → nodes grow → re-flow so cards never overlap
  narr.classList.add("show"); $("#play").classList.add("on"); $("#step").classList.add("on");
  view.k=clamp(view.k,0.7,1.1); showStep();
  $("#nauto").textContent=auto?"⏸ Pause":"▶ Auto"; if(auto)runAuto();
}
function runAuto(){ tour.auto=true; $("#nauto").textContent="⏸ Pause"; clearTimeout(tour.timer);
  const tick=()=>{ if(!tour.active||!tour.auto)return; if(tour.i>=seq.length-1){tour.auto=false;$("#nauto").textContent="▶ Auto";return;}
    next(); tour.timer=setTimeout(tick,2400); }; tour.timer=setTimeout(tick,2400); }
function stopAuto(){ tour.auto=false; clearTimeout(tour.timer); $("#nauto").textContent="▶ Auto"; }
function next(){ if(tour.i<seq.length-1){tour.i++;showStep();} }
function prev(){ if(tour.i>0){tour.i--;showStep();} }
function endTour(){ tour.active=false; stopAuto(); narr.classList.remove("show");
  document.body.classList.remove("explain-on"); $("#play").classList.remove("on"); $("#step").classList.remove("on");
  Object.values(N).forEach(n=>n.el.classList.remove("dim","cur")); layoutAll(); }
$("#play").onclick=()=>{ if(tour.active&&tour.auto){endTour();} else if(tour.active){runAuto();} else startTour(true); };
$("#step").onclick=()=>{ if(tour.active&&!tour.auto){endTour();} else startTour(false); };
$("#nnext").onclick=()=>{stopAuto();next();};
$("#nprev").onclick=()=>{stopAuto();prev();};
$("#nauto").onclick=()=>{ if(tour.auto)stopAuto(); else runAuto(); };
$("#nclose").onclick=endTour;
// click on canvas advances during manual tour
viewport.addEventListener("click",e=>{
  if(e.target.closest(".node")||e.target.closest(".panel")||e.target.closest(".narr")||e.target.closest(".toolbar"))return;
  if(justPanned||justDragged)return;
  if(tour.active&&!tour.auto){ next(); return; }   // during manual tour, empty-canvas click advances
  closePanels();                                    // otherwise an empty-canvas click closes the sidebar
});
document.addEventListener("keydown",e=>{
  if(e.key==="Escape"){ closeModal(); if(tour.active)endTour(); return; }
  if(!tour.active)return;
  if(e.key===" "||e.key==="ArrowRight"||e.key==="Enter"){ e.preventDefault(); stopAuto(); next(); }
  else if(e.key==="ArrowLeft"||e.key==="Backspace"){ e.preventDefault(); stopAuto(); prev(); }
});

/* ============================ boot ============================ */
function boot(){ layoutAll(); fit(); }
window.addEventListener("resize",()=>{ const k=view.k; layoutAll(); });
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(boot); else window.addEventListener("load",boot);
setTimeout(()=>{ if(!worldW)boot(); },500);
</script>
</body>
</html>
"""
