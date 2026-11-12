"""Resolve bundled vendor Reality sources or an in-repo checkout.

Standalone pack layout (preferred when present)::

    <pack>/
      app/                 # this package (build.py, serve.py, ...)
      vendor/req/src/
      vendor/v4/src/

In-repo layout falls back to ../../src and ../../../v4/src relative to this file.
If those fail but PYTHONPATH already provides reality_req + reality4, keep it
(used by tests that copy the app into a temp dir).
"""
from __future__ import annotations

import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def _ok(req_src: pathlib.Path, v4_src: pathlib.Path) -> bool:
    return (req_src / "reality_req").is_dir() and (v4_src / "reality4").is_dir()


def reality_roots(project_root: pathlib.Path | None = None) -> tuple[pathlib.Path, pathlib.Path]:
    candidates: list[tuple[pathlib.Path, pathlib.Path]] = []

    def add_vendor(base: pathlib.Path):
        candidates.append((base / "vendor" / "req" / "src", base / "vendor" / "v4" / "src"))

    # 1) Standalone: vendor next to app/ (project_root is app/)
    if project_root is not None:
        add_vendor(project_root.resolve().parent)
        add_vendor(project_root.resolve())  # if someone sets root to pack/
    # 2) Vendor next to this module's parent (app/ when running from pack)
    add_vendor(HERE.parent)
    add_vendor(HERE)

    # 3) Explicit env
    root = os.environ.get("REALITY_ROOT") or os.environ.get("AUTHORING_REALITY_ROOT")
    if root:
        r = pathlib.Path(root)
        candidates.append((r / "req" / "src", r / "v4" / "src"))

    # 4) In-repo from THIS file (not from a copied temp project root)
    candidates.append((HERE.parent.parent / "src", HERE.parent.parent.parent / "v4" / "src"))

    for req_src, v4_src in candidates:
        if _ok(req_src, v4_src):
            return req_src, v4_src
    raise FileNotFoundError(
        "Cannot find reality_req + reality4 sources. Expected vendor/ next to app/, "
        "or an in-repo checkout, or REALITY_ROOT pointing at a Reality tree."
    )


def pythonpath(project_root: pathlib.Path | None = None) -> str:
    try:
        req_src, v4_src = reality_roots(project_root)
        parts = [str(req_src), str(v4_src)]
        extra = os.environ.get("PYTHONPATH")
        if extra:
            parts.append(extra)
        return os.pathsep.join(parts)
    except FileNotFoundError:
        # Caller (tests / start.sh) may already have set a valid PYTHONPATH
        existing = os.environ.get("PYTHONPATH")
        if existing:
            return existing
        raise


def env_with_reality(project_root: pathlib.Path | None = None) -> dict:
    return {**os.environ, "PYTHONPATH": pythonpath(project_root)}
