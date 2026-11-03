use si
# One test, two decisions, two contradictory claims (v0 review #7, back). test_meaning
# compares the effect's kind, the correction's procedure (and a region's space) by name.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
procedure m from t row 1
procedure m2 from t row 1
dimension Mass2 = Mass
effect e1 { variable: Mass, modulation: parametric, direction: positive }
effect e2 { variable: Mass2, modulation: parametric, direction: positive }
group A of Participant { members: t rows where "group" is "A", key: "id" }
group B of Participant { members: t rows where "group" is "B", key: "id" }
test t1 { compares: A > B, design: independent, effect: e1, statistic: t(df: 3, df_method: pooled), sign: positive_means A > B, correction: fwe(alpha: 0.05, method: m) }
test t2 { compares: A > B, design: independent, effect: e2, statistic: t(df: 3, df_method: pooled), sign: positive_means A > B, correction: fwe(alpha: 0.05, method: m2) }
result r1 = significant(t1) from t row 1
result r2 = not_significant(t2) from t row 2
claim k1 = differs(e1: A > B) by r1
claim k2 = not_shown(e2: A > B) by r2
