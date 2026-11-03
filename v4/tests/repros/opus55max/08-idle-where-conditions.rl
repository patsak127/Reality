file f = sha256:09e291c283748047a0b0677fa92b33bf8c56bb94e392e0dd1c0bbabc3b010ea0
let t = tsv(f)
claim count(where(t, eq(2, "A")))
claim count(where(t, eq(2, "A"), eq(2, "A")))
claim count(where(t, eq(2, "A"), ne(2, "B")))
claim count(where(t, ne(2, "\xff")))
claim count(where(t, ne(2, "A\x09B")))
claim count(where(t, eq(2, "A"), ne(2, "A")))
claim share(where(t, ne(2, "\xff")))
