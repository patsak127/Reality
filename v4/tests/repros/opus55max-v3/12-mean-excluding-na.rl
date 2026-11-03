# Finding 12: the selection excludes the n/a row by a written condition, yet mean/sum/max/min
# refuse because an unselected row of the base holds n/a (V005, "skipping a row would be a
# choice no byte states"). The choice is stated in the text: ne(3, "n/a").
file f = sha256:dd6d02b4e8e7177fe9bd587d0da2ab53d6d69b9c04739570b72a3bfdc6365b97
let t = tsv(f)
let known = where(t, ne(3, "n/a"))
claim count(known)
claim mean(known, 3)
claim max(known, "age")
