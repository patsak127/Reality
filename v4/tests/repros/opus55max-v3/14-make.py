"""Finding 14, BIDS variant: participants.tsv ends with one blank line."""
import _lib as L
f = L.base_files(); f["participants.tsv"] = "participant_id\tgroup\nsub-01\ta\n\n"
m = L.build("14b", f)
L.program("14b", "bids-trailing-blank-line", 'dataset d = sha256:%s\nlet b = bids(d)\nclaim count(participants(b))\n' % m)
