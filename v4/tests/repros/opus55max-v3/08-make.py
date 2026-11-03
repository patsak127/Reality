"""Finding 08: participants.tsv with empty cells (two successive tabs, and a trailing tab) and a
blank fourth header name. BIDS 1.0.1 section 4.2: "Missing values should be coded as n/a", and
its footnote 2: two successive tabs "should not happen in an actual BIDS tsv file".
08b-ds: the control, a header name written twice (v3 refuses this whole file, B04)."""
import _lib as L
f = L.base_files(subjects=("01", "02"))
f["participants.tsv"] = "participant_id\tgroup\tage\t\nsub-01\t\t30\tx\nsub-02\ta\t\ty\n"
m = L.build("08", f)
L.program("08", "empty-cells", 'dataset d = sha256:%s\nlet b = bids(d)\n'
          'claim count(where(participants(b), eq("group", ""))) is 1\n'
          'claim extra(participant(b, "02"), "age") is ""\n'
          'claim extra(participant(b, "01"), 4)\n' % m)
f = L.base_files(subjects=("01", "02"))
f["participants.tsv"] = "participant_id\tgroup\tgroup\nsub-01\tb\tc\nsub-02\ta\td\n"
m = L.build("08b", f)
L.program("08b", "control-duplicate-header", 'dataset d = sha256:%s\nlet b = bids(d)\nclaim count(participants(b))\n' % m)
