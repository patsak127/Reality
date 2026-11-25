#!/usr/bin/env python3
"""Turn the saved primary sources in source/ into Reality's LF-terminated TSV tables in tables/.

1. NASA/JPL Horizons (2024-Jan-01 to 2025-Dec-31, daily 00:00 UT, quantity 31):
   - source/horizons-mars-from-earth.txt     -> tables/mars-seen-from-earth.tsv
   - source/horizons-mars-from-sun.txt       -> tables/mars-seen-from-sun.tsv
   - source/horizons-jupiter-from-earth.txt  -> tables/jupiter-seen-from-earth.tsv
   For each day except the last, compare ecliptic longitude with the next day (handling
   the 360-to-0 wrap): `prograde` if step > 0, `retrograde` if step < 0. Last day dropped -> 730 rows.

2. Mirzadeh et al. (Apple, ICLR 2025), arXiv:2410.05229v1 Table 1:
   - source/arxiv-2410.05229v1-table1.html   -> tables/llm-gsm8k-100.tsv
                                                tables/llm-gsm-noop.tsv
                                                tables/llm-gsm8k-100-open.tsv
   Extracts `GSM8K (100)` (static 100-question subset) and `Symbolic-NoOp` (mean across 50
   symbolic instantiations per NoOp-augmented template) for all 25 evaluated models (2B to o1-preview).
   Marks `meets_80pct = yes` if accuracy >= 80.0 else `no`. Open-weights subset excludes the
   4 proprietary OpenAI models (GPT-4o-mini, GPT-4o, o1-mini, o1-preview) -> 21 rows.

Usage: python3 convert.py
"""
from decimal import Decimal
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROPRIETARY_MODELS = {"GPT-4o-mini", "GPT-4o", "o1-mini", "o1-preview"}


def convert_horizons() -> None:
    header = b"date\tseen_from\tecliptic_longitude_deg\tmotion"
    pairs = [
        ("source/horizons-mars-from-earth.txt", b"Earth", "tables/mars-seen-from-earth.tsv"),
        ("source/horizons-mars-from-sun.txt", b"Sun", "tables/mars-seen-from-sun.tsv"),
        ("source/horizons-jupiter-from-earth.txt", b"Earth", "tables/jupiter-seen-from-earth.tsv"),
    ]
    for src, observer, dst in pairs:
        text = (HERE / src).read_bytes()
        body = text.split(b"$$SOE\n", 1)[1].split(b"$$EOE", 1)[0]
        days = []
        for line in body.split(b"\n"):
            if not line.strip():
                continue
            cells = [c.strip() for c in line.split(b",")]
            assert len(cells) == 6 and cells[1] == cells[2] == cells[5] == b"", line
            date, hhmm = cells[0].split(b" ")
            assert hhmm == b"00:00", line
            days.append((date, cells[3]))
        assert len(days) == 731, (src, len(days))
        rows = []
        for (date, lon), (_, nxt) in zip(days, days[1:]):
            step = Decimal(nxt.decode()) - Decimal(lon.decode())
            step += 360 if step < -180 else -360 if step > 180 else 0
            assert abs(step) < 5, date
            assert step != 0, date
            rows.append(b"\t".join([date, observer, lon, b"prograde" if step > 0 else b"retrograde"]))
        (HERE / dst).write_bytes(b"\n".join([header] + rows) + b"\n")
        retro = [r.split(b"\t")[0].decode() for r in rows if r.endswith(b"retrograde")]
        print(f"{dst}: {len(rows)} rows, {len(retro)} retrograde"
              + (f" ({retro[0]} .. {retro[-1]})" if retro else ""))


def convert_gsm_symbolic() -> None:
    html = (HERE / "source/arxiv-2410.05229v1-table1.html").read_text(encoding="utf-8")
    parsed = []
    for match in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", html, re.S):
        row = match.group(1)
        if "<table" in row:
            continue
        cells = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
            for c in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.S)
        ]
        if len(cells) != 8:
            continue
        model = cells[0]
        gsm8k_100 = Decimal(cells[2])
        noop_val = Decimal(cells[7].split("(", 1)[0].strip())
        weights = "proprietary" if model in PROPRIETARY_MODELS else "open"
        parsed.append((model, weights, gsm8k_100, noop_val))
    assert len(parsed) == 25, f"expected 25 models, got {len(parsed)}"

    header = "model\tweights\teval_frame\taccuracy_pct\tmeets_80pct"

    def write_table(dst: str, frame: str, subset: list[tuple[str, str, Decimal]]) -> None:
        lines = [header]
        hits = 0
        for model, weights, acc in subset:
            meets = "yes" if acc >= Decimal("80.0") else "no"
            if meets == "yes":
                hits += 1
            lines.append(f"{model}\t{weights}\t{frame}\t{acc}\t{meets}")
        (HERE / dst).write_bytes(("\n".join(lines) + "\n").encode("ascii"))
        print(f"{dst}: {len(subset)} rows, {hits} meets_80pct")

    write_table("tables/llm-gsm8k-100.tsv", "gsm8k-100", [(m, w, g) for m, w, g, _ in parsed])
    write_table("tables/llm-gsm-noop.tsv", "gsm-symbolic-noop", [(m, w, n) for m, w, _, n in parsed])
    write_table("tables/llm-gsm8k-100-open.tsv", "gsm8k-100", [(m, w, g) for m, w, g, _ in parsed if w == "open"])


if __name__ == "__main__":
    (HERE / "tables").mkdir(exist_ok=True)
    convert_horizons()
    convert_gsm_symbolic()
