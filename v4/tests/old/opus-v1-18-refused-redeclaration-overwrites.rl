# The second 'group A' is refused (N002), but it has already replaced the first A's members,
# so the test on line 9 is refused too (E033), although it is about the first A.
entity P
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
effect e { variable: Length, modulation: parametric, direction: positive }
group A of P { members: t rows where "group" is "A", key: "id" }
group A of P { members: t rows where "group" is "B", key: "id" }
group B of P { members: t rows where "group" is "B", key: "id" }
test tt { compares: A > B, design: independent, effect: e, statistic: z, sign: positive_means A > B, correction: uncorrected(alpha: 0.05) }
