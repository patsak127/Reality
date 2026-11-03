"""Finding 05: three small datasets.
05-ds:  image sub-01_task-x_run-01_bold.nii (pixdim[4] = 1 s), root task-x_bold.json (TR 1),
        and a sidecar sub-01_task-x_run-1_bold.json with RepetitionTime 2.   -> v3 forms TR = 1 s
05b-ds: the same, but the sidecar is named run-01 (applies)                 -> v3 refuses B09
05c-ds: two images, run-1 and run-01 (v3's own B13: "1.0.1 does not say whether they are one run")"""
import _lib as L
side = '{"RepetitionTime": 2}'
f = L.base_files(run="01"); f["sub-01/func/sub-01_task-x_run-1_bold.json"] = side
m = L.build("05", f)
L.program("05", "run-label-sidecar", 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x", "01"))\n' % m)
f = L.base_files(run="01"); f["sub-01/func/sub-01_task-x_run-01_bold.json"] = side
m = L.build("05b", f)
L.program("05b", "control-sidecar-applies", 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x", "01"))\n' % m)
f = L.base_files(run="01")
f["sub-01/func/sub-01_task-x_run-1_bold.nii"] = f["sub-01/func/sub-01_task-x_run-01_bold.nii"]
f["sub-01/func/sub-01_task-x_run-1_events.tsv"] = f["sub-01/func/sub-01_task-x_run-01_events.tsv"]
m = L.build("05c", f)
L.program("05c", "control-two-images", 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x", "01"))\n' % m)
