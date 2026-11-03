"""Build findings/12-nifti2/: a minimal BIDS 1.0.1 dataset whose one BOLD file is NIfTI-2 with
pixdim[4] = 0.72 (float64, as NIfTI-2 stores it) and RepetitionTime 0.72 in the sidecar."""
import os, struct
root = "findings/12-nifti2"
def w(rel, data):
    p = os.path.join(root, *rel.split("/")); os.makedirs(os.path.dirname(p) or root, exist_ok=True)
    open(p, "wb").write(data if isinstance(data, bytes) else data.encode())
h = bytearray(540)
struct.pack_into("<i", h, 0, 540); h[4:12] = b"n+2\x00\r\n\x1a\n"
struct.pack_into("<2h", h, 12, 2, 8)                      # uint8
struct.pack_into("<8q", h, 16, 4, 2, 2, 2, 3, 1, 1, 1)
struct.pack_into("<8d", h, 104, 1.0, 1.0, 1.0, 1.0, 0.72, 0, 0, 0)
struct.pack_into("<q", h, 168, 544)
struct.pack_into("<i", h, 500, 10)                        # mm + s
img = bytes(h) + b"\x00" * 4 + b"\x00" * 24
w("dataset_description.json", '{"Name": "n2", "BIDSVersion": "1.0.1"}')
w("task-x_bold.json", '{"TaskName": "x", "RepetitionTime": 0.72}')
w("participants.tsv", "participant_id\tgroup\nsub-01\ta\n")
w("sub-01/func/sub-01_task-x_bold.nii", img)
w("sub-01/func/sub-01_task-x_events.tsv", "onset\tduration\n0.5\t1\n")
