"""Finding 20: key() is not charged the 1 step SPEC 9.8 gives "evaluating any call to a
computation (9.12)" (9.12 lists key()). Steps are not printed, so the observable is R002 at
the bound. Writes /tmp/reality-review-20/{t.tsv,u49991.tsv,u49992.tsv} and
findings/20-key-step.rl (Ru = 49 991) and findings/20b-key-step-control.rl (Ru = 49 992).
By SPEC 9.8 the claim line costs: difference 1, sum 1, where 1, two column scope checks
2(R+1), the where filter R x 3996 conditions, sum's R+1, number 1, cell 1, key 1 (the step the
code omits), key's column scope Ru+1. With R = 50 000 that is 199 950 010 + Ru (spec) and
199 950 009 + Ru (code). The bound is "steps > 200 000 000 is R002"."""
import hashlib, itertools, os
D = "/tmp/reality-review-20"; os.makedirs(D, exist_ok=True)
R = 50_000
t = ("c1\tc2\n" + "a\t2\n" + "a\t1\n" * (R - 1)).encode()            # col 2 = 2 in one row only
open(f"{D}/t.tsv", "wb").write(t)
safe = "abcdefghjkpqstuvwxyz"                                        # no o, i, l, m, r, n, digits
lits = ["".join(p) for p in itertools.product(safe, repeat=3)][:3995]
def conds(ls):
    return ", ".join(f'ne(1, "{x}")' for x in ls)
for Ru in (49_991, 49_992):
    u = ("c1\tc2\n" + "k\t5\n" + "a\t5\n" * (Ru - 1)).encode()
    open(f"{D}/u{Ru}.tsv", "wb").write(u)
    prog = "\n".join([
        f"file g = sha256:{hashlib.sha256(t).hexdigest()}",
        f"file h = sha256:{hashlib.sha256(u).hexdigest()}",
        "let t = tsv(g)", "let u = tsv(h)",
        f'let s1 = where(t, eq(2, "2"), {conds(lits[:1331])})',
        f"let s2 = where(s1, {conds(lits[1331:2663])})",
        f"let s3 = where(s2, {conds(lits[2663:3994])})",
        f'claim difference(sum(where(s3, ne(1, "{lits[3994]}")), 2), number(cell(u, key(1, "k"), 2)))', ""])
    name = "20-key-step.rl" if Ru == 49_991 else "20b-key-step-control.rl"
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), "w").write(prog)
