"""Finding 25: a file that changes after the checker hashed it. README says such a file is
refused (F002). That holds for files read whole (tsv(), JSON, manifests); bytes() and size()
open the path again without re-hashing it, so they form claims about bytes the named hash
does not have.

    python -I findings\\25-file-changes-during-check.py

The script copies findings\\25-before.tsv ("id\\nAAAA\\n", the file 25-file-changes-during-check.rl
names) to scratch\\25-changing.tsv, lets the Store hash it (as `python -m reality2 check` does
before it checks anything), then overwrites it with "id\\nBBBB\\n" (same length) and checks the
program: the moment between the two is the same as another process writing the file while a
long check runs. The temporary file is deleted at the end."""
import os
import shutil
import sys

F = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(F)
sys.path.insert(0, os.path.join(ROOT, "src"))
from reality2 import readers  # noqa: E402
from reality2.kernel import check  # noqa: E402

p = os.path.join(ROOT, "scratch", "25-changing.tsv")
shutil.copyfile(os.path.join(F, "25-before.tsv"), p)
prog = open(os.path.join(F, "25-file-changes-during-check.rl"), "rb").read()
store = readers.Store([p])            # the file is hashed now: it is the file the program names
with open(p, "wb") as f:              # then it changes on disk
    f.write(b"id\nBBBB\n")
ok, out = check(prog, store)
print("\n".join(out))
os.remove(p)
