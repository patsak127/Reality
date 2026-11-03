# N17 as the acceptance test writes it: the box copy's full manifest.
dataset d = sha256:b6850de7d9ed854e78149bb842325892c4e888e312969b8812ea1fc9f9f0e4f2
let b = bids(d)
claim count(where(participants(b), eq("group", "equalRange"))) is 54
