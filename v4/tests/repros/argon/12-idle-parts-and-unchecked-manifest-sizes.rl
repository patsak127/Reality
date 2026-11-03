dataset d = sha256:f407ec30d56ee1931deeae21bf67d184ad8bfb892c5df5931f5e2fb441f1aa03
file ghost = sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
file nums = sha256:433a36369cf140e6e22538705b8a6f0c198462f8fd57b667783bbd37768b3985
file prose = sha256:6802d2152377833c0b76f1de88a3406b12eaa1d93dcf92351e460450ee157fbf
claim rows(participants(bids(d))) is 2
claim count(where(tsv(nums), eq(1, "a"), ne(1, "b"))) is 1
claim sum(where(tsv(prose), eq(1, "x"), ne(1, "x")), 2) is 0
claim difference(number(cell(tsv(nums), 1, 2)), sum(where(tsv(prose), eq(1, "x"), ne(1, "x")), 2)) is 10
claim widen(number(cell(tsv(nums), 1, 2)), tolerance = 0) is 10
claim share(where(tsv(nums), eq(1, "z"))) is 0/-5
claim share(where(tsv(nums), eq(1, "a"))) is 54/108
claim exceeds(widen(number(cell(tsv(nums), 1, 2)), tolerance = 0.05), c = 9.9)
claim exceeds(widen(number(cell(tsv(nums), 1, 2)), tolerance = 5), c = 4)
