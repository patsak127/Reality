# task-x_bold.json is valid RFC 8259 JSON: RepetitionTime is 2.000...0 (5000 zeros).
dataset d = sha256:b375775c4ec54fff4fc9b691503f5523c3271e95cb57024b0756edde8cbfa450
let b = bids(d)
claim count(participants(b))
claim tr(recording(b, "01", "x"))
