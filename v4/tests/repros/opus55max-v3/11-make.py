"""Finding 11: BIDS 1.0.1 section 4.2: "Tabular files can be optionally accompanied by a simple
data dictionary in a JSON format ... The data dictionaries should have the same name as their
corresponding tabular files but with .json extensions."
11-ds:  sub-01/func/sub-01_task-x_events.json, the dictionary of sub-01_task-x_events.tsv -> B17
11b-ds: the same dictionary at the root as task-x_events.json                             -> forms"""
import _lib as L
dic = '{"onset": {"LongName": "Event onset", "Units": "s"}, "duration": {"Units": "s"}}'
for nn, rel, name in (("11", "sub-01/func/sub-01_task-x_events.json", "events-dictionary-in-func"),
                      ("11b", "task-x_events.json", "control-events-dictionary-at-root")):
    f = L.base_files(); f[rel] = dic
    m = L.build(nn, f)
    L.program(nn, name, 'dataset d = sha256:%s\nlet b = bids(d)\nclaim onset(recording(b, "01", "x"), 1)\n' % m)
