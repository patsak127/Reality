"""Build a standalone authoring-controls ZIP (no .git, no REALITY_ROOT).

  python pack_standalone.py [--out-dir DIR]

Writes reality-authoring-controls-<shortsha>.zip + VERIFY.json + STARTUP.md
under the out dir (default: store path when present, else ./standalone-out).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REQ = HERE.parent.parent
ROOT = REQ.parent
DEMO = HERE.parent
PY = sys.executable

DEFAULT_OUT = pathlib.Path(
    "/cursor/stores/self/internal/megajam-competing-models/authoring-controls/standalone"
)


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: pathlib.Path) -> str:
    return sha_bytes(p.read_bytes())


def git_sha() -> str:
    r = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


def copy_tree(src: pathlib.Path, dst: pathlib.Path, *, ignore=None):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=ignore)


def main():
    ap_out = DEFAULT_OUT if DEFAULT_OUT.parent.is_dir() else (HERE / "standalone-out")
    out_dir = pathlib.Path(sys.argv[sys.argv.index("--out-dir") + 1]) if "--out-dir" in sys.argv else ap_out
    out_dir.mkdir(parents=True, exist_ok=True)

    head = git_sha()
    short = head[:12]
    name = f"reality-authoring-controls-{short}"
    staging = pathlib.Path(tempfile.mkdtemp(prefix="ac-pack-")) / name
    staging.mkdir(parents=True)

    # app/
    app = staging / "app"
    app.mkdir()
    for fn in (
        "build.py", "check_run.py", "edit_me.json", "feedback.py", "paths.py",
        "run.sh", "serve.py", "README.md",
    ):
        src = HERE / fn
        if src.is_file():
            shutil.copy(src, app / fn)
    # data: playtest + pre-baked evals/stats so composite/stats modes work offline
    data = app / "data"
    data.mkdir()
    for fn in ("playtest_1.tsv", "playtest_2.tsv", "scores.tsv"):
        shutil.copy(HERE / "data" / fn, data / fn)
    env = {**os.environ, "PYTHONPATH": f"{REQ / 'src'}:{ROOT / 'v4' / 'src'}"}
    subprocess.run([PY, str(DEMO / "make_evals.py"), str(data)], check=True, env=env, capture_output=True)
    subprocess.run([PY, str(DEMO / "make_stats.py"), str(data)], check=True, env=env, capture_output=True)

    # vendor Reality sources
    vend_req = staging / "vendor" / "req" / "src"
    vend_v4 = staging / "vendor" / "v4" / "src"
    copy_tree(REQ / "src" / "reality_req", vend_req / "reality_req",
              ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    copy_tree(REQ / "src" / "reality_ord", vend_req / "reality_ord",
              ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    copy_tree(REQ / "src" / "reality_stats", vend_req / "reality_stats",
              ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    copy_tree(ROOT / "v4" / "src" / "reality4", vend_v4 / "reality4",
              ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if (ROOT / "v4" / "src" / "reality4_ref").is_dir():
        copy_tree(ROOT / "v4" / "src" / "reality4_ref", vend_v4 / "reality4_ref",
                  ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    # launchers
    (staging / "start.sh").write_text(
        "#!/usr/bin/env bash\n"
        "# Reality authoring controls — standalone (bundled vendor Reality).\n"
        "# Prerequisite: Python 3.13+ on PATH (python3 or PYTHON).\n"
        "set -euo pipefail\n"
        'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
        'export PYTHONPATH="$HERE/vendor/req/src:$HERE/vendor/v4/src${PYTHONPATH:+:$PYTHONPATH}"\n'
        'PY="${PYTHON:-python3}"\n'
        'HOST="${HOST:-127.0.0.1}"\n'
        'PORT="${PORT:-8765}"\n'
        'exec "$PY" "$HERE/app/serve.py" --host "$HOST" --port "$PORT" --root "$HERE/app"\n'
    )
    (staging / "start.sh").chmod(0o755)
    (staging / "start.command").write_text(
        '#!/bin/bash\ncd "$(dirname "$0")"\nexec bash ./start.sh\n'
    )
    (staging / "start.command").chmod(0o755)
    (staging / "start.bat").write_text(
        "@echo off\r\n"
        "set HERE=%~dp0\r\n"
        "set PYTHONPATH=%HERE%vendor\\req\\src;%HERE%vendor\\v4\\src\r\n"
        "set HOST=127.0.0.1\r\n"
        "set PORT=8765\r\n"
        "python \"%HERE%app\\serve.py\" --host %HOST% --port %PORT% --root \"%HERE%app\"\r\n"
    )
    (staging / "README.md").write_text(
        f"# Reality authoring controls (standalone)\n\n"
        f"Commit `{head}`.\n\n"
        f"Requires Python >= 3.13. No `.git`. No `REALITY_ROOT`.\n\n"
        f"```sh\nbash start.sh   # http://127.0.0.1:8765/\n```\n\n"
        f"Menthol EDIT ME: playtest, composite AI-eval Gate, Wilson stats bars. "
        f"Never signs. Draft trials only.\n"
    )

    # provenance
    files = []
    for p in sorted(staging.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(staging)).replace("\\", "/")
            files.append({"path": rel, "sha256": sha_file(p), "bytes": p.stat().st_size})
    tree_fp = sha_bytes("\n".join(f"{f['sha256']}  {f['path']}" for f in files).encode() + b"\n")
    (staging / "PROVENANCE.json").write_text(json.dumps({
        "name": "reality-authoring-controls-standalone",
        "source_git_commit": head,
        "python_requires": ">=3.13",
        "includes_git": False,
        "requires_REALITY_ROOT": False,
        "bind_default": "127.0.0.1",
        "tree_fingerprint": tree_fp,
        "file_count": len(files),
        "files": files,
    }, indent=2) + "\n")

    # zip
    zip_path = out_dir / f"{name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(staging.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=f"{name}/{p.relative_to(staging).as_posix()}")

    # verify: extract, build+check with cleared env
    vdir = pathlib.Path(tempfile.mkdtemp(prefix="ac-verify-"))
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(vdir)
    root = vdir / name
    venv = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PYTHONPATH": f"{root / 'vendor' / 'req' / 'src'}:{root / 'vendor' / 'v4' / 'src'}",
    }
    # strip REALITY_ROOT if present
    br = subprocess.run([PY, str(root / "app" / "build.py"), "--root", str(root / "app")],
                        env=venv, capture_output=True, text=True)
    cr = subprocess.run([PY, str(root / "app" / "check_run.py"), "--root", str(root / "app")],
                        env=venv, capture_output=True, text=True)
    ir = subprocess.run(
        [PY, "-c",
         "import reality4, reality_req, pathlib; "
         "print(pathlib.Path(reality4.__file__).resolve()); "
         "print(pathlib.Path(reality_req.__file__).resolve())"],
        env=venv, capture_output=True, text=True,
    )
    fb_status = None
    try:
        fb_status = json.loads(cr.stdout).get("feedback", {}).get("trial", {}).get("status")
    except Exception:
        pass
    verify = {
        "archive": zip_path.name,
        "archive_path": str(zip_path),
        "sha256": sha_file(zip_path),
        "bytes": zip_path.stat().st_size,
        "source_git_commit": head,
        "invocation": {
            "linux_macos": "bash start.sh",
            "macos_finder": "double-click start.command",
            "windows": "start.bat",
            "url": "http://127.0.0.1:8765/",
            "python": ">=3.13",
            "bind_default": "127.0.0.1",
            "optional_host": "HOST=0.0.0.0 bash start.sh",
        },
        "ok": br.returncode == 0 and cr.returncode == 0 and ir.returncode == 0,
        "build_exit": br.returncode,
        "check_exit": cr.returncode,
        "import_exit": ir.returncode,
        "import_stdout": ir.stdout,
        "feedback_status": fb_status,
        "check_stdout_head": cr.stdout[:800],
        "build_stderr": br.stderr,
        "check_stderr": cr.stderr,
    }
    (out_dir / "VERIFY.json").write_text(json.dumps(verify, indent=2) + "\n")
    (out_dir / "STARTUP.md").write_text(
        f"# Standalone startup (verified)\n\n"
        f"Archive: `{zip_path.name}`  \n"
        f"SHA-256: see VERIFY.json  \n"
        f"Python: **>=3.13** (no privileged install). Bundled `vendor/req/src` + `vendor/v4/src` "
        f"(includes `reality_stats`). No `.git`. No `REALITY_ROOT`.\n\n"
        f"```sh\nunzip {zip_path.name}\ncd {name}\nbash start.sh          # → http://127.0.0.1:8765/\n"
        f"# macOS Finder: start.command\n# Windows: start.bat\n"
        f"# Optional bind: HOST=0.0.0.0 PORT=8765 bash start.sh\n```\n\n"
        f"Verified: `VERIFY.json` → `\"ok\": {str(verify['ok']).lower()}` means extract-to-temp, "
        f"clear REALITY_ROOT/PYTHONPATH, build+check using only vendor sources.\n"
    )
    print(json.dumps({"zip": str(zip_path), "sha256": verify["sha256"], "ok": verify["ok"],
                      "bytes": verify["bytes"]}, indent=2))
    return 0 if verify["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
