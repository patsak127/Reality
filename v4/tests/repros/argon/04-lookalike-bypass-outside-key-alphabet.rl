file f = sha256:22e0ef83e818b0a748fcb2f522d4744d0af0c9f39a9061e5251768aa436f451c
claim count(where(tsv(f), eq("group", "ok"))) is 3
claim cell(tsv(f), key(1, "al"), "alb") is "20"
claim cell(tsv(f), key(1, "so1"), 2) is "ok"
claim count(where(tsv(f), eq(1, "sub-001"))) is 1
