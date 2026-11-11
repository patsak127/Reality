"""Compatibility parse surface for ORD tests — delegates clause rules to reality4.questions.

Prefer `reality4.kernel.check` / `reality_ord.eval_ord.check_text` for evaluation.
Formation refusals use the same O-codes as the core question path.
"""
from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass
from fractions import Fraction

_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path[:0] = [str(_ROOT / "v4" / "src"), str(_ROOT / "req" / "src")]

from reality4.questions import parse_weighted_pair_body  # noqa: E402
from reality4.readers import Refusal  # noqa: E402
from reality4.syntax import SyntaxRefusal, group_program_lines, parse_line, split_program  # noqa: E402


class FormRefuse(Exception):
    def __init__(self, code: str, line: int, msg: str):
        super().__init__(msg)
        self.code, self.line, self.msg = code, line, msg


@dataclass(frozen=True)
class FileBind:
    line: int
    name: str
    sha256: str


@dataclass(frozen=True)
class Question:
    line: int
    name: str
    table: str
    candidate_col: str
    left: str
    right: str
    task1_col: str
    task2_col: str
    weights: tuple[Fraction, ...]
    equality: str


@dataclass(frozen=True)
class Program:
    files: tuple[FileBind, ...]
    question: Question


def parse(text: str) -> Program:
    if not text.endswith("\n"):
        text += "\n"
    try:
        raw = list(split_program(text.encode("ascii")))
        grouped = list(group_program_lines(raw))
    except SyntaxRefusal as e:
        raise FormRefuse(e.code, e.line, e.msg) from e
    except Exception as e:
        raise FormRefuse("O001", 1, str(e)) from e

    files: list[FileBind] = []
    q: Question | None = None
    for ln, block in grouped:
        try:
            st = parse_line(block, ln)
        except SyntaxRefusal as e:
            raise FormRefuse(e.code, e.line, e.msg) from e
        if st is None:
            continue
        if st.kind in ("file", "dataset"):
            files.append(FileBind(st.line, st.name, st.hash))
        elif st.kind == "question":
            if q is not None:
                raise FormRefuse("O001", ln, "ORD-EXP allows one question per program")
            try:
                qf = parse_weighted_pair_body(st.name, list(st.qbody or ()), st.line)
            except Refusal as e:
                raise FormRefuse(e.code, st.line, e.msg) from e
            q = Question(
                line=st.line,
                name=qf.name,
                table=qf.table,
                candidate_col=qf.candidate_col,
                left=qf.left,
                right=qf.right,
                task1_col=qf.task1_col,
                task2_col=qf.task2_col,
                weights=qf.weights,
                equality=qf.equality,
            )
        else:
            raise FormRefuse("O001", ln, f"expected file or question, got {st.kind}")
    if q is None:
        raise FormRefuse("O001", 1, "program forms no question")
    if not files:
        raise FormRefuse("O001", q.line, "question needs a file binding")
    return Program(tuple(files), q)
