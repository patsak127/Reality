file f = sha256:6aa157755dadfb19dbe13e8f1e5bbcdb2a48b2a20a9b79402fb6ef4f1e4580c5
let t = tsv(f)
claim share(where(t, eq(2, "A"))) is 1/3
claim exceeds(number(cell(t, 1, 3)), c = 0) is 1
