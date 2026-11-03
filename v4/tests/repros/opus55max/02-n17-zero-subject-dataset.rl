# The manifest lists the box copy's 8 root files, byte for byte, and nothing under sub-*/.
dataset d = sha256:d314232b0eefaa20f66920acac339d3d06008b435fd0ac82bc044ffc1285a8a7
let b = bids(d)
claim count(where(participants(b), eq("group", "equalRange"))) is 54
claim share(where(participants(b), eq("group", "equalRange"))) is 54/108
claim count(where(participants(b), eq("gender", "F"))) is 60
