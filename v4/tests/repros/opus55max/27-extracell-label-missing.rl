dataset d = sha256:db55c056c38e8571ace1e4366796513ad73fa46abdb1ed83b924faa14ee7a82b
let p = participants(bids(d))
claim count(where(p, eq("age", "30")))
claim max(p, "age")
claim sum(where(p, eq("group", "b")), 3)
