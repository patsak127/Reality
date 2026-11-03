dataset d = sha256:de6cfc27f4cca47a2b5816c317eb91a85b6a00c8305fbb71079c177e31ce18fa
let b = bids(d)
claim tr(recording(b, "01", "x", "2"))
claim difference(tr(recording(b, "01", "x", "1")), tr(recording(b, "01", "x", "2")))
