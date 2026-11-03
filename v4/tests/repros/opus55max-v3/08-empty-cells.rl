dataset d = sha256:62b1ac4c1f45d8829f94b8182a857bc12f046d5ea6d4088f305fc9d7342066d9
let b = bids(d)
claim count(where(participants(b), eq("group", ""))) is 1
claim extra(participant(b, "02"), "age") is ""
claim extra(participant(b, "01"), 4)
