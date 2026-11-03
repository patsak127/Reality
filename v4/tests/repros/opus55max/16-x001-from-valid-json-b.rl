dataset d = sha256:b9a4f467dbccbed70c3f7f23bf18fcd5bbba5f7ac699a360df63d06f1a454220
# the same dataset, read first from a deeper expression, then from a shallow one
claim exceeds(widen(widen(widen(widen(widen(widen(widen(widen(number(extra(participant(bids(d), "01"), 2)), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), c = 0)
claim count(participants(bids(d)))
