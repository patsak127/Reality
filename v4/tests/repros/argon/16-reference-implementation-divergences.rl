file f = sha256:85736ad40fb3e1fbb85e37ee21ff3eff7ba3a341c332368932b0db2f0049c395
claim cell(tsv(f), 0, 2)
claim cell(tsv(f), 1, 0)
claim widen(number(cell(tsv(f), 1, 2)), tolerance = -5)
claim share(where(tsv(f), eq(1, "a"))) is 99/100
claim count(where(tsv(f), eq(1, "@0000000000000000000000000000000000000000000000000000000000000000"))) is 0
