"""Finding 24: build the FABRICATED complete copy exactly as the test suite does
(tests/bidsfix.py complete_copy) under /tmp/reality-review-24/, write its manifest, and write
findings/24-fabricated-copy.rl with F3, F8 and F11 plus two comparisons."""
import hashlib, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src"), os.path.join(HERE, "..", "tests")]
import bidsfix
from reality3 import readers
D = "/tmp/reality-review-24"
shutil.rmtree(D, ignore_errors=True); os.makedirs(D)
root = bidsfix.complete_copy(os.path.join(D, "ds"))
man = readers.make_manifest(root)
open(os.path.join(D, "manifest.txt"), "wb").write(man)
h = hashlib.sha256(man).hexdigest()
open(os.path.join(HERE, "24-fabricated-copy.rl"), "w").write(
    f"dataset d = sha256:{h}\nlet b = bids(d)\nlet r = recording(b, \"001\", \"MGT\", \"01\")\n"
    "claim volumes(r)\nclaim tr(r)\nclaim onset(r, 1)\n"
    "claim exceeds(onset(r, 1), c = 3 s)\nclaim exceeds(onset(r, 64), c = 400 s)\n")
print("manifest", h)
