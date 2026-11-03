# Control: the same two tolerances on the same spelling of the cell are refused (S012).
file f = sha256:71b87b82cad447a40934dfc1ad1bfc91d6864e86a36df871209170a9c0763e2e
let t = tsv(f)
claim exceeds(widen(number(cell(t, 1, 3)), tolerance = 1), c = 28)
claim below(widen(number(cell(t, 1, 3)), tolerance = 5), c = 36)
