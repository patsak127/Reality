dataset d = sha256:69afb96445b1476693779165a85d7dc414bb894deb7595291da441813c7a1188
let b = bids(d)
let r1 = recording(b, "01", "x")
let r2 = recording(b, "02", "x")
# onsets are seconds from the first volume of *their own* recording (two different events)
claim difference(onset(r2, 1), onset(r1, 1))
claim exceeds(difference(onset(r2, 1), onset(r1, 1)), c = 5)
# a duration minus a time point
claim difference(tr(r1), onset(r1, 1))
# for contrast, a meaningful one: two events of one recording
claim difference(onset(r1, 2), onset(r1, 1))
