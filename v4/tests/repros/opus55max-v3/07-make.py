"""Finding 07: BIDS 1.0.1 section 3.5's example: "tasks.tsv may be specified at the participant
level, setting TR to a specific value". The image's pixdim[4] and the root task-x_bold.json
say 1 s; tasks.tsv says 2.
07-ds:  sub-01/tasks.tsv (participant level, the example's own placement)
07b-ds: tasks.tsv at the root
07c-ds: task-x_tasks.tsv at the root (the same kind of file with an entity: B14)"""
import _lib as L
for nn, rel, name in (("07", "sub-01/tasks.tsv", "tasks-tsv-example"),
                      ("07b", "tasks.tsv", "tasks-tsv-root"),
                      ("07c", "task-x_tasks.tsv", "control-root-tsv-with-entity")):
    f = L.base_files(); f[rel] = "RepetitionTime\n2\n"
    m = L.build(nn, f)
    L.program(nn, name, 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x"))\n' % m)
