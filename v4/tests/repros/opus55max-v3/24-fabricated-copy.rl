dataset d = sha256:62e9c0a6c1a31923bc4149de60d81cc279ba93460655951da5821dadbd4a69b4
let b = bids(d)
let r = recording(b, "001", "MGT", "01")
claim volumes(r)
claim tr(r)
claim onset(r, 1)
claim exceeds(onset(r, 1), c = 3 s)
claim exceeds(onset(r, 64), c = 400 s)
