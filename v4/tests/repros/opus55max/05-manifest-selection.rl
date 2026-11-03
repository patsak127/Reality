dataset full = sha256:15c7cce9f71a20580532aa22e34d0104d75c21962b3a5c5ec16cb5faccd69313
dataset nosub02 = sha256:14f2238b6e98e0d88f74d9880122ac0eba3d83e6771a397f54ea5c733cd1b512
dataset norun2 = sha256:6c5364c529fa7ce7a05020aced8ac6a272556b9beed804627a8fbc64c509c34b
claim count(participants(bids(full)))
# sub-02's folder (4 images, 2 events files, a sidecar) left out; its row is still there
claim count(participants(bids(nosub02)))
claim extra(participant(bids(nosub02), "02"), "group")
# sub-01 run 2 (BOLD and events) left out, though sub-01's phasediff.json IntendedFor names it
claim volumes(recording(bids(norun2), "01", "x", "1"))
claim volumes(recording(bids(norun2), "01", "x", "2"))
