"""Finding 15: participants.tsv describes two participants; only sub-01 has imaging data
(a participant recruited but not scanned, or whose data were withheld)."""
import _lib as L
f = L.base_files(); f["participants.tsv"] = "participant_id\tgroup\nsub-01\ta\nsub-02\tb\n"
m = L.build("15", f)
L.program("15", "row-without-folder", 'dataset d = sha256:%s\nlet b = bids(d)\nclaim count(participants(b))\nclaim tr(recording(b, "01", "x"))\n' % m)
