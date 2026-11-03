dataset d = sha256:4bcaca20356772c332341b6a9d9bc9d4e65e4ab02e3e9bd8ae0dc6a2b3eb843d
let b = bids(d)
claim volumes(recording(b, "01", "x")) is 4
claim rows(participants(b))
claim count(where(participants(b), eq("group", "a")))
