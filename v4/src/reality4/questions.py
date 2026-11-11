"""Native stipulated-model questions (principle §1). Outside claim operands by type.

A QuestionAnswer is not a Meaning: it cannot be returned from meaning(), bound as a let
value, passed to a Call, or printed as `line N: formed: Sort value`. Writing derived
numbers into a new file is a new bytes floor (fabrication / outside reuse) — that is not
in-language laundering and is not stopped here.

Weight families are question content, not §10.1 claim-parameter slots.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from . import keys as K
from . import readers as R
from .readers import Refusal


# ---- answer type (structurally not Meaning) ----------------------------------------------

@dataclass(frozen=True)
class Witness:
    weight: Fraction
    score_left: Fraction
    score_right: Fraction

    @property
    def difference(self) -> Fraction:
        return self.score_left - self.score_right


@dataclass(frozen=True)
class OrderingBucket:
    ordering: str
    witnesses: tuple[Witness, ...]


@dataclass(frozen=True)
class Support:
    sha256: str
    candidate_col: int
    task1_col: int
    task2_col: int
    left_row: int
    right_row: int


@dataclass(frozen=True)
class QuestionAnswer:
    """Stipulated-model answer. Not a kernel Meaning; not a claim operand."""

    form: str
    name: str
    orderings: tuple[OrderingBucket, ...]
    robust: bool
    scope_note: str
    precision_note: str
    support: Support
    weights: tuple[Fraction, ...]


@dataclass(frozen=True)
class QuestionResult:
    """Returned from Checker.statement for questions — distinct from claim (M, named, value)."""

    answer: QuestionAnswer
    lines: tuple[str, ...]


@dataclass(frozen=True)
class QForm:
    form: str
    name: str
    table: str
    candidate_col: str
    left: str
    right: str
    task1_col: str
    task2_col: str
    weights: tuple[Fraction, ...]
    equality: str


def _ratio(tok: str, ln: int) -> Fraction:
    if "/" not in tok:
        raise Refusal("O001", "1", f"weight must be a ratio INT/INT, got {tok!r}")
    a, b = tok.split("/", 1)
    if not a.isdigit() or not b.isdigit():
        raise Refusal("O001", "1", f"weight ratio needs non-negative integers, got {tok!r}")
    d = int(b)
    if d < 1:
        raise Refusal("O001", "1", "weight denominator must be >= 1")
    w = Fraction(int(a), d)
    if w < 0 or w > 1:
        raise Refusal(
            "O009",
            "1",
            f"weight {tok} is outside [0, 1]; this question's score is a convex combination "
            f"w*task1+(1-w)*task2",
        )
    return w


def _string(s: str, ln: int) -> str:
    s = s.strip()
    if len(s) < 2 or s[0] != '"':
        raise Refusal("O001", "1", f"expected STRING, got {s!r}")
    end = s.find('"', 1)
    if end < 0:
        raise Refusal("O001", "1", f"unclosed STRING, got {s!r}")
    if s[end + 1 :].strip():
        raise Refusal("O001", "1", f"trailing tokens after STRING: {s[end + 1 :]!r}")
    body = s[1:end]
    if '"' in body or "\\" in body:
        raise Refusal("O001", "1", "escapes other than none are not used in this question form")
    return body


def parse_weighted_pair_body(name: str, body_lines: list[str], start_line: int) -> QForm:
    pending: dict = {"line": start_line, "name": name}
    for raw in body_lines:
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line[:1] not in " \t":
            raise Refusal("O001", "1", f"question clause must be indented, got {line!r}")
        body = line.strip()
        def setc(k, v):
            if k in pending:
                raise Refusal("O001", "1", f"duplicate clause {k!r}; two writings, one answer required")
            pending[k] = v

        if body.startswith("table "):
            t = body[len("table ") :].strip()
            if not t.isidentifier() or len(t) > 64 or any(c.isspace() for c in t):
                raise Refusal("O001", "1", f"table name must be one identifier, got {t!r}")
            setc("table", t)
        elif body.startswith("candidate_col "):
            setc("candidate_col", _string(body[len("candidate_col ") :], start_line))
        elif body.startswith("left "):
            setc("left", _string(body[len("left ") :], start_line))
        elif body.startswith("right "):
            setc("right", _string(body[len("right ") :], start_line))
        elif body.startswith("task1_col "):
            setc("task1_col", _string(body[len("task1_col ") :], start_line))
        elif body.startswith("task2_col "):
            setc("task2_col", _string(body[len("task2_col ") :], start_line))
        elif body.startswith("weights "):
            rest = body[len("weights ") :].strip()
            if not rest:
                raise Refusal("O002", "1", "weights family is empty")
            parts = [p.strip() for p in rest.split(",")]
            if any(p == "" for p in parts):
                raise Refusal("O001", "1", "empty token in weights list (trailing/double comma)")
            ws = tuple(_ratio(p, start_line) for p in parts)
            if len(set(ws)) != len(ws):
                raise Refusal("O007", "1", "duplicate weight in family; each weight is listed once")
            setc("weights", ws)
        elif body.startswith("equality "):
            eq = body[len("equality ") :].strip()
            if eq != "exact":
                raise Refusal("O003", "1", f"equality must be exactly the token 'exact', got {eq!r}")
            setc("equality", eq)
        else:
            raise Refusal("O001", "1", f"unknown question clause: {body!r}")

    need = ("table", "candidate_col", "left", "right", "task1_col", "task2_col", "weights", "equality")
    missing = [k for k in need if k not in pending]
    if missing:
        raise Refusal("O001", "1", f"question missing required clause(s): {', '.join(missing)}")
    if pending["left"] == pending["right"]:
        raise Refusal("O008", "1", "left and right must be distinct literals")
    if pending["task1_col"] == pending["task2_col"]:
        raise Refusal(
            "O010",
            "1",
            "task1_col and task2_col name the same column; every weight is idle "
            "(score ignores the weight family), so the question does not say what it asks",
        )
    return QForm(
        form="weighted_pair_orderings",
        name=pending["name"],
        table=pending["table"],
        candidate_col=pending["candidate_col"],
        left=pending["left"],
        right=pending["right"],
        task1_col=pending["task1_col"],
        task2_col=pending["task2_col"],
        weights=pending["weights"],
        equality=pending["equality"],
    )


def _cell_decimal(text: str, hint: str) -> Fraction:
    try:
        q = R.decimal(text)
    except Refusal as e:
        raise Refusal("O006", "1", f"task cell {text!r} ({hint}): {e.msg}") from e
    if q is None:
        raise Refusal(
            "O006",
            "1",
            f"non-numeric task cell {text!r} ({hint}): not Reality decimal grammar",
        )
    return q


def _resolve_col(header: list[str], name: str, what: str) -> int:
    if not K.is_header_name(name):
        raise Refusal(
            "O005",
            "1",
            f"{what}: column {name!r} is not an addressable header (ASCII letters, digits, '_')",
        )
    hits = [i for i, h in enumerate(header) if h == name]
    if not hits:
        raise Refusal("O005", "1", f"{what}: no header is {name!r}")
    if len(hits) > 1:
        raise Refusal(
            "O005",
            "1",
            f"{what}: header {name!r} repeats (columns {', '.join(str(i + 1) for i in hits)})",
        )
    for h in header:
        c = K.invisible(h)
        if c is not None:
            raise Refusal("O005", "1", f"{what}: header holds invisible/format character U+{ord(c):04X}")
    pair = K.lookalikes(header)
    if pair is not None:
        raise Refusal(
            "O005",
            "1",
            f"{what}: headers {pair[0]!r} and {pair[1]!r} look alike (UTS #39); refused",
        )
    return hits[0]


def evaluate_weighted_pair(qf: QForm, store: R.Store, env: dict) -> QuestionAnswer:
    b = env.get(qf.table)
    if b is None:
        raise Refusal("O001", "1", f"table {qf.table!r} is not a bound file name")
    if b[0] == "refused":
        raise Refusal(
            "O004",
            "1",
            f"table {qf.table!r} comes from a refused file binding (line {b[1]}); "
            f"no supporting bytes under the question",
        )
    if b[0] != "file":
        raise Refusal("O001", "1", f"table {qf.table!r} must name a file binding, not {b[0]}")
    hx = b[1]
    try:
        path = store.path(hx)
    except Refusal as e:
        raise Refusal("O004", "1", e.msg) from e
    data = open(path, "rb").read()
    try:
        tab = R.parse_tsv(data, hx, R.Steps(), bids=False)
    except Refusal as e:
        raise Refusal("O004", "1", e.msg) from e

    header = list(tab.header)
    rows = [list(r) for r in tab.rows]
    if not rows:
        raise Refusal("O005", "1", "table has no data rows")

    ci = _resolve_col(header, qf.candidate_col, "candidate_col")
    i1 = _resolve_col(header, qf.task1_col, "task1_col")
    i2 = _resolve_col(header, qf.task2_col, "task2_col")
    if i1 == i2:
        raise Refusal("O010", "1", "task1_col and task2_col resolve to the same column position")

    cand_vals = [qf.left, qf.right] + [r[ci] for r in rows]
    for v in cand_vals:
        c = K.invisible(v)
        if c is not None:
            raise Refusal("O005", "1", f"candidate key holds invisible/format character U+{ord(c):04X}")
    pair = K.lookalikes(cand_vals)
    if pair is not None:
        raise Refusal(
            "O005",
            "1",
            f"candidate keys {pair[0]!r} and {pair[1]!r} look alike (UTS #39); refused",
        )

    def row_for(alias: str):
        hits = [(i, r) for i, r in enumerate(rows) if r[ci] == alias]
        if len(hits) != 1:
            raise Refusal("O005", "1", f"need exactly one row for candidate {alias!r}, found {len(hits)}")
        return hits[0]

    left_i, left_r = row_for(qf.left)
    right_i, right_r = row_for(qf.right)
    t1l = _cell_decimal(left_r[i1], "left.task1")
    t2l = _cell_decimal(left_r[i2], "left.task2")
    t1r = _cell_decimal(right_r[i1], "right.task1")
    t2r = _cell_decimal(right_r[i2], "right.task2")

    buckets: dict[str, list[Witness]] = {"left>right": [], "left<right": [], "left=right": []}
    for w in qf.weights:
        sl = w * t1l + (1 - w) * t2l
        sr = w * t1r + (1 - w) * t2r
        if sl > sr:
            key = "left>right"
        elif sl < sr:
            key = "left<right"
        else:
            key = "left=right"
        buckets[key].append(Witness(w, sl, sr))

    orderings = tuple(OrderingBucket(k, tuple(v)) for k, v in buckets.items() if v)
    support = Support(hx, ci + 1, i1 + 1, i2 + 1, left_i + 1, right_i + 1)
    scope = (
        f"scope: weights={list(map(str, qf.weights))}; equality={qf.equality}; "
        f"left={qf.left!r} right={qf.right!r}; tasks=({qf.task1_col!r},{qf.task2_col!r}); "
        "declared family only — not exhaustive real-world criteria; "
        "question content (not a §10.1 claim-parameter slot)"
    )
    precision = (
        "precision: Exact-as-decoded under Reality decimal reader (byte identity). "
        "Recorded measurement sense only — not claimed measurement precision (§10.2)."
    )
    return QuestionAnswer(
        form=qf.form,
        name=qf.name,
        orderings=orderings,
        robust=len(orderings) == 1,
        scope_note=scope,
        precision_note=precision,
        support=support,
        weights=qf.weights,
    )


def format_answer_lines(ln: int, ans: QuestionAnswer) -> tuple[str, ...]:
    """Print as question answer lines — never `formed: Sort value` claim shape."""
    s = ans.support
    lines = [
        f"line {ln}: question {ans.name}: formed",
        "  representation: QuestionAnswer (not Meaning; not a claim operand)",
        f"  {ans.scope_note}",
        f"  {ans.precision_note}",
        (
            f"  support: sha256:{s.sha256}; candidate_col={s.candidate_col}; "
            f"task1_col={s.task1_col}; task2_col={s.task2_col}; "
            f"left_row={s.left_row}; right_row={s.right_row}"
        ),
        f"  robust_same_ordering_throughout: {str(ans.robust).lower()}",
        f"  attained_orderings: {len(ans.orderings)}",
    ]
    for od in ans.orderings:
        lines.append(f"  ordering {od.ordering}:")
        for w in od.witnesses:
            lines.append(
                f"    witness weight={w.weight} score_left={w.score_left} "
                f"score_right={w.score_right} difference={w.difference}"
            )
    return tuple(lines)


def run_question(st, store: R.Store, env: dict) -> QuestionResult:
    if st.qform != "weighted_pair_orderings":
        raise Refusal("O001", "1", f"unknown question form {st.qform!r}")
    qf = parse_weighted_pair_body(st.name, st.qbody or [], st.line)
    ans = evaluate_weighted_pair(qf, store, env)
    return QuestionResult(ans, format_answer_lines(st.line, ans))
