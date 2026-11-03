# Finding 19: call 4 (S012) is "one value, one tolerance in one program". It is keyed on the
# spelling of the widened sort, so the same cell (row 1, column 3: the bytes "30") is used with
# tolerance 1, tolerance 5 and no tolerance, in three formed claims of one program.
file f = sha256:71b87b82cad447a40934dfc1ad1bfc91d6864e86a36df871209170a9c0763e2e
let t = tsv(f)
claim exceeds(widen(number(cell(t, 1, 3)), tolerance = 1), c = 28)
claim below(widen(number(cell(t, key(1, "s1"), 3)), tolerance = 5), c = 36)
claim atleast(number(cell(t, 1, 3)), c = 30)
