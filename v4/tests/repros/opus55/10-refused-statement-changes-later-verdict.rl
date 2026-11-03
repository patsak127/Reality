# The same claim, written twice. Between them, a let that is refused (B00).
file p = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
dataset d = sha256:b6850de7d9ed854e78149bb842325892c4e888e312969b8812ea1fc9f9f0e4f2
claim rows(tsv(p)) is 108
let b = bids(d)
claim rows(tsv(p)) is 108
