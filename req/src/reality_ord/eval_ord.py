"""SPEC-ORD entry: shared Reality v4 checker path (not a standalone dialect CLI).

Programs with `file` + `question weighted_pair_orderings` are checked by `reality4.kernel.check`.
Question answers are `questions.QuestionAnswer` — structurally not claim Meanings.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Mapping, Sequence, Union

_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_ROOT / "v4" / "src"), str(_ROOT / "req" / "src")]

from reality4 import readers  # noqa: E402
from reality4.kernel import check  # noqa: E402

PathMap = Mapping[str, pathlib.Path]
PathList = Sequence[pathlib.Path]
PathsArg = Union[PathMap, PathList]


def check_text(text: str, file_paths: PathsArg) -> str:
    if isinstance(file_paths, Mapping):
        paths = [str(p) for p in file_paths.values()]
    else:
        paths = [str(p) for p in file_paths]
    store = readers.Store(paths, [])
    ok, lines = check(text.encode("ascii"), store)
    return "\n".join(lines) + "\n"
