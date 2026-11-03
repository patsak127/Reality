"""Run findings/17 twice in-process: as shipped, and with Checker.touch_bold made a no-op
(the BOLD file is then neither read nor recorded). Nothing else changes."""
import sys
sys.path.insert(0, "src")
from reality2 import readers, kernel
prog = open("findings/17-check2-for-bids-is-written-by-the-sort-code.rl", "rb").read()
def run():
    ok, out = kernel.check(prog, readers.Store(["findings/09-fabricated-complete.manifest"], ["scratch/cmp"]))
    print("\n".join(l[:230] for l in out if not l.startswith("  #")))
print("-- as shipped"); run()
kernel.Checker.touch_bold = lambda self, r: None
print("-- touch_bold disabled"); run()
