entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
effect e { variable: Length, modulation: parametric, direction: positive }
group G of Participant { members: t rows where "group" is "A", key: "id" }
test tt { compares: in G for positive_effect, effect: e, statistic: t(df: 1, df_method: 3), sign: positive_means positive_effect, correction: uncorrected(alpha: 0.05) }
