file f = sha256:22e0ef83e818b0a748fcb2f522d4744d0af0c9f39a9061e5251768aa436f451c
claim cell(tsv(f), 3, 1)
claim cell(tsv(f), 4, 1)
claim cell(tsv(f), 1, 1)
claim cell(tsv(f), 2, 1)
claim header(tsv(f), 3)
claim cell(tsv(f), 8, 1)
claim count(where(tsv(f), eq(1, "sub\xe2\x80\x91001")))
