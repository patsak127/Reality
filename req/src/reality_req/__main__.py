"""python -m reality_req check LEDGER [--files PATH...] [--allowed-signers FILE] [--run-from LINE]

Checks a requirements ledger (req/SPEC.md). --files: data files or folders, supplied by their
SHA-256 as in Reality v4. --allowed-signers: the ssh-keygen allowed_signers file whose keys verify
adoptions and withdrawals; without it every adoption refuses G012. --run-from: checks and trials on
earlier lines are formed but not run, and say so (for a demo that adds lines step by step). Exit 0 if every statement
formed (whatever a check found), 1 if any statement was refused, 2 for a usage error."""
import pathlib
import sys

from .bind import Verifier
from .form import Ledger
from .run import Runner


def main(argv):
    if len(argv) < 2 or argv[0] != "check":
        sys.stderr.write(__doc__ + "\n"); return 2
    ledger, opts, cur = argv[1], {"--files": [], "--allowed-signers": [], "--run-from": []}, None
    for a in argv[2:]:
        if a in opts:
            cur = a
        elif cur is None or a.startswith("--"):
            sys.stderr.write(__doc__ + "\n"); return 2
        else:
            opts[cur].append(a)
    if len(opts["--allowed-signers"]) > 1 or len(opts["--run-from"]) > 1 or not all(x.isdigit() for x in opts["--run-from"]):
        sys.stderr.write(__doc__ + "\n"); return 2
    path = pathlib.Path(ledger)
    try:
        data = path.read_bytes()
    except OSError as e:
        sys.stderr.write(f"reality_req: cannot read {ledger} ({e.strerror})\n"); return 2
    verifier = Verifier(opts["--allowed-signers"][0]) if opts["--allowed-signers"] else None
    led = Ledger(path.parent, runner=Runner(opts["--files"]), verifier=verifier,
                 run_from=int(opts["--run-from"][0]) if opts["--run-from"] else 0)
    for line in led.check(data):
        sys.stdout.buffer.write(line.encode("utf-8", "backslashreplace") + b"\n")
    return 1 if led.refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
