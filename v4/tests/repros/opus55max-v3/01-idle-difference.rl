# Finding 01: values that cannot depend on the bytes form (item 1). v3 refuses difference(x, x)
# with S008 "the bytes do not bear on the answer (it is 0 whatever they hold)" and refuses
# atleast(count, c = 0) as "a cutoff no value can fail", but only when the two sorts are
# spelled identically or the value is directly a count. Every claim below has the same
# answer for every table Reality can read.
file f = sha256:71b87b82cad447a40934dfc1ad1bfc91d6864e86a36df871209170a9c0763e2e
let t = tsv(f)
claim difference(rows(t), count(t)) is 0
claim difference(count(where(t, eq(1, "s2"), eq(2, "B"))), count(where(t, eq(2, "B"), eq(1, "s2")))) is 0
claim difference(widen(max(t, 3), tolerance = 1), max(t, 3))
claim atleast(difference(rows(t), count(where(t, eq(2, "B")))), c = 0)
claim atleast(difference(max(t, 3), min(t, 3)), c = 0)
# The two forms v3 does refuse, for comparison:
claim difference(rows(t), rows(t))
claim atleast(count(where(t, eq(2, "B"))), c = 0)
