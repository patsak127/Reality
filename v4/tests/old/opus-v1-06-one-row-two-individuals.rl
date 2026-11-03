# a and b are declared from the same row (participant s1), c and d from s2's row. Each pair is
# two "different" individuals, so the same two people form two "independent" groups.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
effect e { variable: Length, modulation: parametric, direction: positive }
individual a : Participant from t row 1
individual b : Participant from t row 1
individual c : Participant from t row 2
individual d : Participant from t row 2
group G1 of Participant { members: {a, c} }
group G2 of Participant { members: {b, d} }
test tt { compares: G1 > G2, design: independent, effect: e, statistic: t(df: 2, df_method: pooled), sign: positive_means G1 > G2, correction: uncorrected(alpha: 0.05) }
result r = significant(tt) from t row 3
claim k = differs(e: G1 > G2) by r
ask same[identity](a, b)
