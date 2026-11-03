file f = sha256:6802d2152377833c0b76f1de88a3406b12eaa1d93dcf92351e460450ee157fbf
claim sum(where(tsv(f), eq(1, "x")), 2)
claim sum(where(tsv(f), eq(1, "x"), ne(1, "x")), 2)
claim count(where(tsv(f), eq(1, "x"), ne(1, "x")))
claim share(where(tsv(f), eq(1, "x"))) is 1/-2
claim share(where(tsv(f), eq(1, "x"))) is 54/108
