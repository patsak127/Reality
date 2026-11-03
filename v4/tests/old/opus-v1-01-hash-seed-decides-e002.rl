# A and A2 have the same members (every "A" row), built two ways. t1 and t2 are the same test
# (SPEC 3.7: meanings compare groups by their member sets), so E002 must refuse r2.
# Whether it does depends on PYTHONHASHSEED: test_meaning sorts the two groups of a '<>'
# comparison by repr(), and repr of a frozenset depends on hash order.
entity P
artifact t = file "01-ids.tsv" sha256 "ce5515c4cce4b9c0bbbb6930debd726d016f0585f1ef3ab359f87b7ffe04ada9"
effect e { variable: Length, modulation: parametric, direction: positive }
group A of P { members: t rows where "g" is "A", key: "id" }
group A2 of P { members: t rows minus t rows where "g" is "B", key: "id" }
group B of P { members: t rows where "g" is "B", key: "id" }
test t1 { compares: A <> B, design: independent, effect: e, statistic: z, sign: positive_means A > B, correction: uncorrected(alpha: 0.05) }
test t2 { compares: A2 <> B, design: independent, effect: e, statistic: z, sign: positive_means A2 > B, correction: uncorrected(alpha: 0.05) }
result r1 = significant(t1) from t row 1
result r2 = not_significant(t2) from t row 2
claim k1 = differs(e: A <> B) by r1
claim k2 = not_shown(e: A2 <> B) by r2
