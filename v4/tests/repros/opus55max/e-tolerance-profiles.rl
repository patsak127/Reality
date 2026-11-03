file f = sha256:061576c484d6bbf1ad58cca5d2159dad833b2894d4f17e29d42df26699132e64
let t = tsv(f)
claim exceeds(widen(max(t, 3), tolerance = 0), c = 40)
claim below(widen(max(t, 3), tolerance = 5), c = 50)
