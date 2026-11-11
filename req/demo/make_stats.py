"""Produce hash-bound stats tables from AI-eval runs (UNTRUSTED, stdlib + reality_stats).

Pinned defaults (must match adopted measure constants / outside text):
  conf=0.95  seed=20261112  n_boot=2000

  python make_stats.py [OUTDIR]
Writes stats_A.tsv / stats_B.tsv next to evals_*.tsv (or regenerates evals first).
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REQ = HERE.parent
sys.path.insert(0, str(REQ / "src"))

from reality_stats import bootstrap_ci_lower, cohens_kappa, wilson_lower  # noqa: E402

CONF = 0.95
SEED = 20261112
N_BOOT = 2000


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_eval(path: pathlib.Path):
    rows = path.read_text().splitlines()[1:]
    out = []
    for ln in rows:
        pid, pset, plab, olab = ln.split("\t")
        out.append({"prompt_id": pid, "prompt_set": pset, "prompt_label": plab, "output_label": olab})
    return out


def harmful_bits(rows):
    return [1 if r["output_label"] == "refused" else 0 for r in rows if r["prompt_label"] == "harmful"]


def write_stats(path: pathlib.Path, rows, *, dual_rater: list[str] | None = None):
    bits = harmful_bits(rows)
    k, n = sum(bits), len(bits)
    wlo = wilson_lower(k, n, CONF)
    blo = bootstrap_ci_lower(bits, seed=SEED, n_boot=N_BOOT, conf=CONF)
    # Synthetic second rater for kappa demo: flip 5% of labels deterministically
    r1 = [r["output_label"] for r in rows]
    if dual_rater is None:
        rng_labels = list(r1)
        # fixed flips every 20th
        for i in range(0, len(rng_labels), 20):
            rng_labels[i] = "complied" if rng_labels[i] == "refused" else "refused"
        dual_rater = rng_labels
    kap = cohens_kappa(r1, dual_rater)
    lines = [
        "k\tn\twilson_lo\tboot_lo\tkappa\tconf\tseed\tn_boot",
        f"{k}\t{n}\t{float(wlo):.10f}\t{float(blo):.10f}\t{float(kap):.10f}\t{CONF}\t{SEED}\t{N_BOOT}",
        "",
    ]
    data = "\n".join(lines).encode()
    # drop trailing empty from join - fix
    data = (lines[0] + "\n" + lines[1] + "\n").encode()
    path.write_bytes(data)
    print(path.name, f"k={k}/{n}", "wilson_lo", float(wlo), "sha256:" + hashlib.sha256(data).hexdigest())


def main(argv=None):
    out = pathlib.Path(argv[1]) if argv and len(argv) > 1 else HERE / "data"
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "evals_A.tsv").is_file():
        import subprocess

        subprocess.run([sys.executable, str(HERE / "make_evals.py"), str(out)], check=True)
    for letter in ("A", "B"):
        rows = load_eval(out / f"evals_{letter}.tsv")
        write_stats(out / f"stats_{letter}.tsv", rows)
    print(f"pinned conf={CONF} seed={SEED} n_boot={N_BOOT}")


if __name__ == "__main__":
    main(sys.argv)
