# F with 9 numerator df for a comparison of two groups; 3 permutations at alpha 0.05 (the
# smallest permutation p-value is then 1/4); words given arguments nobody reads.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
effect e2 { variable: Length, modulation: parametric(anything: 7), direction: positive(why: 3) }
group A of Participant { members: t rows where "group" is "A", key: "id" }
group B of Participant { members: t rows where "group" is "B", key: "id" }
test tt { compares: A <> B, design: independent, effect: e2, statistic: F(df1: 9, df2: 3, df_method: pooled), sign: positive_means A > B, correction: uncorrected(alpha: 0.05) }
test t3 { compares: in A for positive_effect, effect: e2, statistic: tfce(permutations: 3), sign: positive_means positive_effect, correction: uncorrected(alpha: 0.05) }
result r = significant(tt) from t row 1
result r3 = significant(t3) from t row 1
claim k = differs(e2: A <> B) by r
claim k3 = effect(e2 for A) by r3
