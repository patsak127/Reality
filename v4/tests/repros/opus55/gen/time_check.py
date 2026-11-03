"""Run the checker in-process on PROGRAM with FILES; print seconds, counted steps, output size."""
import sys, time
sys.path.insert(0, "src")
from reality2 import readers
from reality2.kernel import check
prog = open(sys.argv[1], "rb").read()
st = readers.Store(sys.argv[2:])
t = time.perf_counter()
ok, out = check(prog, st)
dt = time.perf_counter() - t
print(f"seconds={dt:.2f} counted_steps={st.steps.n} output_chars={sum(len(x) for x in out)} accepted={ok}")
print("\n".join(x[:160] for x in out[-4:]))
