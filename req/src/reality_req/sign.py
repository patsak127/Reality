"""Signing helper for adoptions and withdrawals (req/SPEC.md 5.2). UNTRUSTED: what it writes is
checked by bind.py and form.py, so a mistake here can only make an adoption refuse.

python -m reality_req.sign adopt|withdraw LEDGER MEASURE PERSON --key PRIVATE_KEY --at TIME --sig FILE

Prints the requirement text, the whole fragment, the proposer's description and the number of
earlier trials; then reads one line: the measure's name and the first 8 hex digits of its hash,
e.g. 'M1 77874fb1'. There is no default answer: anything else signs nothing. Then it runs
ssh-keygen -Y sign (which asks for the key's passphrase if it has one), writes the signature to
FILE next to the ledger, and prints the statement to append to the ledger. It never edits the ledger.
"""
import argparse
import pathlib
import subprocess
import sys

from . import say
from .bind import NAMESPACE
from .form import Ledger


def main(argv):
    ap = argparse.ArgumentParser(prog="python -m reality_req.sign")
    ap.add_argument("act", choices=["adopt", "withdraw"])
    ap.add_argument("ledger"); ap.add_argument("measure"); ap.add_argument("person")
    ap.add_argument("--key", required=True); ap.add_argument("--at", required=True); ap.add_argument("--sig", required=True)
    ap.add_argument("--out", help="also write the statement to append to this file")
    a = ap.parse_args(argv)
    path = pathlib.Path(a.ledger)
    led = Ledger(path.parent)
    led.check(path.read_bytes())
    if a.measure not in led.measures:
        print(f"{a.measure} is not a measure that formed in {a.ledger}; nothing signed"); return 1
    m = led.measures[a.measure]
    req, r = m["req"], led.reqs[m["req"]]
    print(f"requirement {req}: {say.q(r['text'])} (owner {r['owner']}), sha256:{r['fp']}")
    print(f"measure {a.measure}, proposed by {m['by']}, sha256:{m['fp']}")
    print(f"the proposer's description (plain text, not checked): {say.q(m['says'])}")
    if m["outside"]:
        print(f"computed outside the checker, not checked: {say.q(m['outside'])}")
    print(f"{len(m['trials'])} trial run(s) of {a.measure} so far")
    print("---- fragment ----")
    print("\n".join(m["frag"]).rstrip("\n"))
    print("------------------")
    print(f"To {a.act} {a.measure} for {req} as {a.person}, type: {a.measure} {m['fp'][:8]}")
    answer = sys.stdin.readline().strip()
    if answer != f"{a.measure} {m['fp'][:8]}":
        print("not confirmed; nothing signed"); return 1
    payload = say.payload("adoption" if a.act == "adopt" else "withdrawal", req, r["fp"], a.measure, m["fp"], a.person, a.at)
    sig = path.parent / a.sig
    tmp = sig.with_suffix(".payload")
    tmp.write_bytes(payload)
    try:
        subprocess.run(["ssh-keygen", "-Y", "sign", "-f", a.key, "-n", NAMESPACE, str(tmp)], check=True)
        pathlib.Path(str(tmp) + ".sig").replace(sig)
    finally:
        tmp.unlink(missing_ok=True)
    stmt = (f"{a.act} {a.measure} for {req} by {a.person} at {say.q(a.at)}\n"
            f"  requirement_text sha256:{r['fp']} measure sha256:{m['fp']} sig {say.q(a.sig)}\n")
    print(stmt, end="")
    if a.out:
        pathlib.Path(a.out).write_text(stmt)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
