"""Print the steps reality3 charged to the last statement of a program (store.steps.n)."""
import sys
sys.path.insert(0, "src")
from reality3 import readers as R
from reality3.kernel import check
store = R.Store(sys.argv[2:])
ok, out = check(open(sys.argv[1], "rb").read(), store)
print(f"steps charged to the last statement: {store.steps.n:,}")
for line in out:
    print(line[:150] + (" ..." if len(line) > 150 else ""))
