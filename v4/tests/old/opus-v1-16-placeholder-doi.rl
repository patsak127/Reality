use si
# A DOI "TBD" is a valid outside reference; a correction method "released" at it carries
# into a formed claim as a convention.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
artifact paper = ref doi "TBD"
procedure m from paper
effect e { variable: Length, modulation: parametric, direction: positive }
group A of Participant { members: t rows where "group" is "A", key: "id" }
test tt { compares: in A for positive_effect, effect: e, statistic: t(df: 1, df_method: one_sample), sign: positive_means positive_effect, correction: fwe(alpha: 0.05, method: m) }
result r = significant(tt) from t row 1
claim k = effect(e for A) by r
