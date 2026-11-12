"""Offline browser authoring surface (stdlib only). Menthol pattern: EDIT ME + thematic frames + machinery.

  python serve.py [--port 8765] [--host 127.0.0.1] [--root DIR]

Default bind is loopback. Optional --host for LAN bind; no public internet/infra.
Does not sign. Saves edit_me.json, rebuilds artifacts, runs checker, returns preview JSON.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = pathlib.Path(__file__).resolve().parent
PY = sys.executable

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from paths import env_with_reality  # noqa: E402

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>EDIT ME - Reality draft controls</title>
<style>
  :root {
    --bg: #1a1c1e; --panel: #24282c; --edit: #2a3328; --mach: #2a2a30;
    --ink: #e8e6e1; --muted: #9a968c; --accent: #c4a35a; --ok: #7dba6a;
    --bad: #d07070; --line: #3a3f44;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: "IBM Plex Sans", "Source Sans 3", "Segoe UI", sans-serif;
    background: radial-gradient(1200px 600px at 10% -10%, #2c3036, var(--bg));
    color: var(--ink); min-height: 100vh;
  }
  header { padding: 1.25rem 1.5rem 0.5rem; border-bottom: 1px solid var(--line); }
  header h1 { margin: 0; font-size: 1.35rem; font-weight: 600; }
  header p { margin: 0.35rem 0 0; color: var(--muted); font-size: 0.92rem; max-width: 52rem; }
  .badge { display: inline-block; margin-left: 0.5rem; padding: 0.1rem 0.45rem;
    border: 1px solid var(--accent); color: var(--accent); font-size: 0.7rem;
    letter-spacing: 0.06em; text-transform: uppercase; }
  main { display: grid; grid-template-columns: 1.05fr 1fr; gap: 1rem; padding: 1rem 1.5rem 2rem; }
  @media (max-width: 960px) { main { grid-template-columns: 1fr; } }
  .frame { background: var(--panel); border: 1px solid var(--line); padding: 0.85rem 1rem 1rem; margin-bottom: 0.85rem; }
  .frame.edit { background: var(--edit); border-color: #3d4a38; }
  .frame.mach { background: var(--mach); }
  .frame h2 { margin: 0 0 0.65rem; font-size: 0.95rem; font-weight: 600; color: var(--accent); }
  .frame h2 span { color: var(--muted); font-weight: 400; font-size: 0.8rem; }
  label { display: block; margin: 0.65rem 0 0.2rem; font-size: 0.9rem; color: var(--ink); }
  .hint { display: block; font-size: 0.75rem; color: var(--muted); margin: 0 0 0.25rem; }
  input[type=text], input[type=number] {
    width: 100%; padding: 0.4rem 0.5rem; background: #15171a; border: 1px solid var(--line);
    color: var(--ink); font: inherit;
  }
  .toggle { display: flex; align-items: center; gap: 0.55rem; margin: 0.35rem 0 0.2rem; }
  .toggle input { width: 1.1rem; height: 1.1rem; }
  button.apply {
    margin-top: 0.85rem; padding: 0.55rem 0.9rem; background: var(--accent); color: #1a1510;
    border: 0; font: inherit; font-weight: 600; cursor: pointer;
  }
  button.apply:disabled { opacity: 0.5; cursor: wait; }
  button.secondary {
    margin-top: 0.5rem; margin-right: 0.4rem; padding: 0.4rem 0.7rem; background: transparent;
    color: var(--muted); border: 1px solid var(--line); font: inherit; cursor: pointer;
  }
  .result {
    white-space: pre-wrap; font-size: 0.95rem; line-height: 1.45; padding: 0.75rem;
    background: #12141a; border: 1px solid var(--line); margin: 0.4rem 0 0.6rem;
  }
  .result.ok { border-color: #3d5a38; }
  .result.bad { border-color: #5a3838; }
  .result.nc { border-color: #5a5030; }
  .banner { font-size: 0.78rem; letter-spacing: 0.04em; text-transform: uppercase;
    color: var(--accent); margin-bottom: 0.35rem; }
  .meta { font-size: 0.82rem; color: var(--muted); margin: 0.25rem 0 0.6rem; }
  .preview {
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.75rem; white-space: pre-wrap;
    background: #12141a; border: 1px solid var(--line); padding: 0.75rem; max-height: 22rem; overflow: auto;
  }
  details summary { cursor: pointer; color: var(--muted); font-size: 0.85rem; margin-bottom: 0.4rem; }
  .note { font-size: 0.78rem; color: var(--muted); margin-top: 0.5rem; }
  .qbox { margin-top: 0.75rem; padding-top: 0.55rem; border-top: 1px solid var(--line); }
</style>
</head>
<body>
<header>
  <h1>EDIT ME - design controls <span class="badge">unsigned draft</span></h1>
  <p>Menthol EDIT ME: playtest share bar, composite AI-eval Gate parts, or Wilson stats bars.
  Apply writes real fragment and draft ledger files, then runs the real checker. Plain result above;
  machinery collapsed. Trials are exploratory candidates — never adopted or signed here.</p>
</header>
<main>
  <section id="controls"></section>
  <section>
    <div class="frame">
      <h2>Result <span>- exploratory trial beside the controls</span></h2>
      <div id="banner" class="banner">UNSIGNED candidate trial — NOT adopted</div>
      <div id="result" class="result nc">Apply to see a plain result.</div>
      <div id="meta" class="meta"></div>
      <div id="question" class="qbox" hidden></div>
      <details>
        <summary>Full checker log (collapsed)</summary>
        <div id="preview" class="preview">(empty until apply)</div>
      </details>
      <p class="note">Official check without adopt is refused (G002). Question answers are not claims. Stats arithmetic is outside the trusted base.</p>
    </div>
    <div class="frame mach">
      <h2>Pattern machinery — no need to touch</h2>
      <details>
        <summary>Show generated fragments + draft.rq (+ optional compare.ro)</summary>
        <div id="machinery" class="preview" style="margin-top:0.5rem">(empty until apply)</div>
      </details>
    </div>
  </section>
</main>
<script>
const FRAME_ORDER = [
  "EDIT ME - design controls",
  "COMPOSITE AI-EVAL (EDIT ME)",
  "STATS BARS (EDIT ME)",
  "ALTERNATIVES (EDIT ME)",
  "COMPARE ORDERINGS (EDIT ME) - question, not a claim"
];
let state = null;
let defaults = null;

async function load() {
  const r = await fetch("/api/state");
  state = await r.json();
  defaults = JSON.parse(JSON.stringify(state));
  render();
}

function render() {
  const host = document.getElementById("controls");
  host.innerHTML = "";
  for (const fname of FRAME_ORDER) {
    const frame = state.frames[fname];
    if (!frame) continue;
    const div = document.createElement("div");
    div.className = "frame edit";
    const h = document.createElement("h2");
    h.textContent = fname;
    div.appendChild(h);
    for (const [key, spec] of Object.entries(frame)) {
      const kind = spec.kind || "number";
      const lab = document.createElement("label");
      lab.textContent = spec.label || key;
      lab.htmlFor = key;
      div.appendChild(lab);
      if (spec.hint) {
        const hint = document.createElement("span");
        hint.className = "hint";
        hint.textContent = spec.hint;
        div.appendChild(hint);
      }
      if (kind === "toggle") {
        const row = document.createElement("div");
        row.className = "toggle";
        const inp = document.createElement("input");
        inp.type = "checkbox";
        inp.id = key;
        inp.dataset.frame = fname;
        inp.dataset.key = key;
        inp.dataset.kind = "toggle";
        inp.checked = Number(spec.value) === 1;
        const onoff = document.createElement("span");
        onoff.textContent = inp.checked ? "On" : "Off";
        inp.addEventListener("change", () => { onoff.textContent = inp.checked ? "On" : "Off"; });
        row.appendChild(inp);
        row.appendChild(onoff);
        div.appendChild(row);
      } else {
        const inp = document.createElement("input");
        inp.id = key;
        inp.dataset.frame = fname;
        inp.dataset.key = key;
        inp.dataset.kind = kind;
        if (kind === "number") { inp.type = "number"; inp.step = "any"; }
        else { inp.type = "text"; }
        inp.value = spec.value;
        div.appendChild(inp);
      }
    }
    host.appendChild(div);
  }
  const btn = document.createElement("button");
  btn.className = "apply";
  btn.textContent = "Apply — write artifacts & check";
  btn.onclick = apply;
  host.appendChild(btn);
  const reset = document.createElement("button");
  reset.className = "secondary";
  reset.textContent = "Reset controls to defaults";
  reset.onclick = () => {
    state = JSON.parse(JSON.stringify(defaults));
    render();
  };
  host.appendChild(reset);
  const note = document.createElement("p");
  note.className = "note";
  note.textContent = "Edits persist in edit_me.json and work/. No export/presets. Reset only restores the loaded defaults in this browser session until Apply.";
  host.appendChild(note);
}

function collectFrames() {
  const frames = JSON.parse(JSON.stringify(state.frames));
  document.querySelectorAll("[data-frame]").forEach(inp => {
    const f = inp.dataset.frame, k = inp.dataset.key, kind = inp.dataset.kind;
    let val;
    if (kind === "toggle") val = inp.checked ? 1 : 0;
    else if (kind === "number") val = Number(inp.value);
    else val = inp.value;
    frames[f][k].value = val;
  });
  return frames;
}

async function apply() {
  const frames = collectFrames();
  const btn = document.querySelector("button.apply");
  btn.disabled = true;
  try {
    const r = await fetch("/api/apply", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({frames})
    });
    const out = await r.json();
    state.frames = out.edit_me.frames;
    showPreview(out);
  } finally {
    btn.disabled = false;
  }
}

function showPreview(out) {
  const box = document.getElementById("result");
  const meta = document.getElementById("meta");
  const qel = document.getElementById("question");
  const pre = document.getElementById("preview");
  const mach = document.getElementById("machinery");
  const fb = out.feedback || (out.check && out.check.feedback) || {};
  const trial = fb.trial || {};
  let cls = "nc";
  if (trial.status === "met") cls = "ok";
  else if (trial.status === "not_met" || trial.status === "parse_failed") cls = "bad";
  else if (trial.status === "missing") cls = "nc";
  box.className = "result " + cls;
  box.textContent = trial.plain || "No structured feedback; see full log. No favorable result claimed.";
  const ctrls = fb.controls || {};
  meta.textContent = [
    trial.requirement ? ("Requirement: " + trial.requirement) : null,
    ctrls.log ? ("Data: " + ctrls.log) : null,
    ctrls.pass_bar != null ? ("Pass bar: " + ctrls.pass_bar) : null,
    ctrls.wilson_lo_bar != null ? ("Wilson lo bar: " + ctrls.wilson_lo_bar) : null,
    ctrls.bar_a != null ? ("Composite bars A/B: " + ctrls.bar_a + "/" + ctrls.bar_b) : null,
    trial.data_sha_short ? ("Data sha: " + trial.data_sha_short) : null,
    "UNSIGNED — not adopted"
  ].filter(Boolean).join(" · ");
  if (fb.question && fb.question.plain) {
    qel.hidden = false;
    qel.innerHTML = "<strong>Question</strong><pre class='result nc' style='margin-top:0.4rem'>" +
      escapeHtml(fb.question.plain) + "</pre>";
  } else {
    qel.hidden = true;
    qel.innerHTML = "";
  }
  let body = "";
  if (out.check && out.check.req && out.check.req.text)
    body += "=== reality_req check (draft.rq) ===\n" + out.check.req.text + "\n";
  if (out.check && out.check.question && out.check.question.text)
    body += "\n=== reality4 question (compare.ro) ===\n" + out.check.question.text + "\n";
  pre.textContent = body || "(none)";
  mach.textContent = out.machinery || "(none)";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

load().then(() => {
  if (new URLSearchParams(location.search).get("preview") === "1") apply();
});
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    root: pathlib.Path = HERE

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self):
        data = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._html()
        if path == "/api/state":
            edit = json.loads((self.root / "edit_me.json").read_text())
            return self._json(200, edit)
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/apply":
            return self.send_error(404)
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n).decode())
        edit_path = self.root / "edit_me.json"
        edit = json.loads(edit_path.read_text())
        if "frames" in body:
            # Preserve kind/hint/label; update values
            for fname, ctrls in body["frames"].items():
                if fname not in edit["frames"]:
                    edit["frames"][fname] = ctrls
                    continue
                for k, spec in ctrls.items():
                    if k in edit["frames"][fname] and isinstance(spec, dict) and "value" in spec:
                        edit["frames"][fname][k]["value"] = spec["value"]
                    else:
                        edit["frames"][fname][k] = spec
        edit_path.write_text(json.dumps(edit, indent=2) + "\n")
        env = env_with_reality(self.root)
        br = subprocess.run([PY, str(self.root / "build.py"), "--root", str(self.root)], capture_output=True, text=True, env=env)
        cr = subprocess.run([PY, str(self.root / "check_run.py"), "--root", str(self.root)], capture_output=True, text=True, env=env)
        try:
            check = json.loads(cr.stdout or "{}")
        except json.JSONDecodeError:
            check = {"ok": False, "error": (cr.stdout or "") + (cr.stderr or ""), "feedback": {
                "trial": {
                    "status": "parse_failed",
                    "plain": "Could not parse checker driver output; see full log. No favorable result claimed.",
                    "unsigned": True,
                    "adopted": False,
                }
            }}
        work = self.root / "work"
        machinery_parts = []
        for name in (
            "ledger/PassBar.fragment", "ledger/PassBarLoose.fragment",
            "ledger/Gate_RefusalA.fragment", "ledger/Gate_NoRegressB.fragment",
            "ledger/WilsonBar.fragment", "ledger/draft.rq", "compare.ro", "edit_me.json",
        ):
            p = work / name
            if p.is_file():
                machinery_parts.append(f"----- {name} -----\n{p.read_text()}")
        build_meta = {}
        mp = work / "build_meta.json"
        if mp.is_file():
            build_meta = json.loads(mp.read_text())
        self._json(200, {
            "edit_me": edit,
            "build": build_meta,
            "build_stdout": br.stdout,
            "check": check,
            "feedback": check.get("feedback"),
            "machinery": "\n\n".join(machinery_parts),
        })


def main(argv=None):
    argv = list(argv or sys.argv[1:])
    port = 8765
    host = "127.0.0.1"
    root = HERE
    i = 0
    while i < len(argv):
        if argv[i] == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1]); i += 2
        elif argv[i] == "--host" and i + 1 < len(argv):
            host = argv[i + 1]; i += 2
        elif argv[i] == "--root" and i + 1 < len(argv):
            root = pathlib.Path(argv[i + 1]).resolve(); i += 2
        else:
            print("usage: serve.py [--port N] [--host 127.0.0.1] [--root DIR]", file=sys.stderr)
            return 2
    Handler.root = root
    subprocess.run([PY, str(root / "build.py"), "--root", str(root)], check=False, env=env_with_reality(root))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Authoring controls at http://{host}:{port}/  (root={root})")
    print("Draft/unsigned only - never signs. Ctrl+C to stop.")
    httpd.serve_forever()


if __name__ == "__main__":
    sys.exit(main() or 0)
