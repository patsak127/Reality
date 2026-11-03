# Two claims with different byte literals print the same sort with different values.
file f = sha256:7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b
let t = tsv(f)
claim count(where(t, eq(2, "#1"))) is 1
claim count(where(t, eq(2, "@7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b"))) is 0
claim count(where(t, ne(2, "@7da0a7c98d0f07a7a5de598aef1921d231b176087cfe50f0ead7cbae3804888b"))) is 2
