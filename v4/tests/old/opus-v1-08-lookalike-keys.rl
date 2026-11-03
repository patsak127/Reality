# 08-site-y.tsv has the key "sub" U+2011 "001" (a non-breaking hyphen): it looks exactly
# like site X's "sub-001". The same participant is in both "independent" groups.
entity P
artifact a = file "08-site-x.tsv" sha256 "ab277d6d8daabcc4a6c50dfddb241848197c7ff1811332fbb180a097d6dc6d8d"
artifact b = file "08-site-y.tsv" sha256 "5a6bf410cbae138cbe7cf75421bbff2a8aec45464415a3f2fb116c966488ca04"
effect e { variable: Length, modulation: parametric, direction: positive }
group X of P { members: a rows, key: "id" }
group Y of P { members: b rows, key: "id" }
test tt { compares: X > Y, design: independent, effect: e, statistic: t(df: 2, df_method: pooled), sign: positive_means X > Y, correction: uncorrected(alpha: 0.05) }
result r = significant(tt) from a row 1
claim k = differs(e: X > Y) by r
