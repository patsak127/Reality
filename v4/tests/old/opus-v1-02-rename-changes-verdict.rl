# Group A's members are cell values of column "id"; group B's members are individuals.
# The paired-design check compares the two as strings, so it passes only because the
# individuals happen to be spelled like the cells. 02b renames s1, s2 to q1, q2: E033.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
individual s1 : Participant from t row 3
individual s2 : Participant from t row 4
group A of Participant { members: t rows where "group" is "A", key: "id" }
group B of Participant { members: {s1, s2} }
effect e { variable: Length, modulation: parametric, direction: positive }
test tt { compares: A <> B, design: paired, effect: e, statistic: t(df: 1, df_method: paired), sign: positive_means A > B, correction: uncorrected(alpha: 0.05) }
result r = significant(tt) from t row 3
claim c = differs(e: A <> B, paired) by r
