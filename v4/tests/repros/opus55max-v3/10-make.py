"""Finding 10: an events file for task y, for which no BOLD image exists anywhere.
10-ds:  at the participant level, sub-01/sub-01_task-y_events.tsv  -> v3: an extra file, forms
10b-ds: at the root, task-y_events.tsv                            -> v3: B14 ("an inherited tsv file")
BIDS 1.0.1 section 3.5: "Any metadata file (.json, .bvec, .tsv, etc.) may be defined at any
directory level"; section 8.5: "Each task events file requires a corresponding task imaging data file"."""
import _lib as L
ev = "onset\tduration\n1\t2\n"
for nn, rel, name in (("10", "sub-01/sub-01_task-y_events.tsv", "participant-level-events"),
                      ("10b", "task-y_events.tsv", "control-root-events")):
    f = L.base_files(); f[rel] = ev
    m = L.build(nn, f)
    L.program(nn, name, 'dataset d = sha256:%s\nlet b = bids(d)\nclaim count(participants(b))\n' % m)
