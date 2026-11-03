"""Finding 09: BIDS 1.0.1 section 4.2: a tabular file's data dictionary has entries whose names
correspond to column names; section 8.11: phenotype files "can be accompanied with a JSON file
describing the columns in detail (see Section 4.2)". v3 checks this only for participants.json (B19).
09-ds:  phenotype/q.json describes columns that phenotype/q.tsv does not have
09b-ds: phenotype/q.json with no phenotype/q.tsv at all
09c-ds: the root events dictionary task-x_events.json describes columns no events file has
09d-ds, 09e-ds: the same two defects in participants.json (refused, B19)"""
import _lib as L
bad = '{"nonsense": {"Description": "no such column"}}'
cases = [("09", "data-dictionaries", {"phenotype/q.tsv": "participant_id\tscore\nsub-01\t3\n", "phenotype/q.json": bad}),
         ("09b", "phenotype-dictionary-alone", {"phenotype/q.json": bad}),
         ("09c", "events-dictionary", {"task-x_events.json": bad}),
         ("09d", "control-participants-json", {"participants.json": bad}),
         ("09e", "control-participants-json-alone", {"participants.json": bad})]
for nn, name, extra in cases:
    f = L.base_files(); f.update(extra)
    if nn == "09e":
        del f["participants.tsv"]
    m = L.build(nn, f)
    L.program(nn, name, 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x"))\n' % m)
