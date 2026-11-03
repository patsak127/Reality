file f = sha256:061576c484d6bbf1ad58cca5d2159dad833b2894d4f17e29d42df26699132e64
let t = tsv(f)
claim cell(t, key(1, "B"), 3)
claim count(where(t, ne(1, "B")))
claim cell(t, key(1, "A1"), 3)
