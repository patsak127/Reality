file p = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
let t = tsv(p)
claim exceeds(count(where(t, eq(2, "equalRange"))), c = 49)
claim exceeds(share(where(t, eq(2, "equalRange"))), c = 0.4)
claim difference(count(where(t, eq(2, "equalRange"))), count(where(t, eq(2, "equalIndifference"))))
claim exceeds(sum(t, 4), c = 2000)
claim exceeds(number(cell(t, 1, 4)), c = 20)
