file f = sha256:e11498baaa5375a62624ff098ae19d3c3c70f01395f1dc9fccf8ad6ef018f993
let t = tsv(f)
claim rows(t)
claim count(where(t, eq(1, "k5")))
