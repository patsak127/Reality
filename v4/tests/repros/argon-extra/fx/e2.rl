dataset d = sha256:6583cb87fd81759bddd35e1ea2ef44a7eb451273b654a70a23ad41aeb8a1c575
let b = bids(d)
claim rows(participants(b))
claim volumes(recording(b, "01", "x"))
