"""Shared helper for the review's generator scripts (findings/NN-make.py).

Writes small, made-up BIDS 1.0.1 datasets byte for byte (no compressor, no clock), then writes
the Reality manifest next to the dataset folder, so every hash is the same on every machine.
Uses only the standard library and reality3's own manifest writer (readers.make_manifest).
"""
import hashlib
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from reality3 import readers  # noqa: E402


def nifti1(dims, pixdim4=1.0, units=10, datatype=2, bitpix=8, dim_info=0):
    """A minimal single-file NIfTI-1 image: 348-byte header, 4 extension bytes, then zeros.
    units=10 is mm + seconds (xyzt_units & 0x38 == 8)."""
    hdr = bytearray(348)
    struct.pack_into("<i", hdr, 0, 348)
    hdr[39] = dim_info
    d = [len(dims)] + list(dims) + [1] * (7 - len(dims))
    struct.pack_into("<8h", hdr, 40, *d)
    struct.pack_into("<2h", hdr, 70, datatype, bitpix)
    struct.pack_into("<8f", hdr, 76, 1.0, 1.0, 1.0, 1.0, pixdim4, 0.0, 0.0, 0.0)
    struct.pack_into("<f", hdr, 108, 352.0)
    hdr[123] = units
    hdr[344:348] = b"n+1\x00"
    n = 1
    for x in dims:
        n *= x
    return bytes(hdr) + b"\x00" * 4 + b"\x00" * (n * bitpix // 8)


def write_dataset(root, files):
    """files: {relative path: bytes or str}. Replaces root."""
    if os.path.isdir(root):
        shutil.rmtree(root)
    for rel, data in files.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def manifest(root, out):
    data = readers.make_manifest(root)
    with open(out, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def base_files(subjects=("01",), tr=1, task="x", events="onset\tduration\n1.5\t2\n", run=None,
               taskname=None, extra=None, drop=()):
    """A small conformant dataset: one BOLD (2x2x2x5 voxels, pixdim[4] = tr) per subject."""
    files = {
        "dataset_description.json": '{"Name": "review fixture", "BIDSVersion": "1.0.1"}',
        "README": "A made-up dataset written by a review script.\n",
        f"task-{task}_bold.json": '{"TaskName": "%s", "RepetitionTime": %s}' % (taskname or task, tr),
        "participants.tsv": "participant_id\tgroup\n" + "".join(f"sub-{s}\ta\n" for s in subjects),
    }
    r = f"_run-{run}" if run else ""
    for s in subjects:
        files[f"sub-{s}/func/sub-{s}_task-{task}{r}_bold.nii"] = nifti1((2, 2, 2, 5), pixdim4=float(tr))
        if events is not None:
            files[f"sub-{s}/func/sub-{s}_task-{task}{r}_events.tsv"] = events
    for rel in drop:
        files.pop(rel)
    files.update(extra or {})
    return files


def build(nn, files):
    """Write findings/NN-ds/ and findings/NN-manifest.txt; return the manifest hash."""
    root = os.path.join(HERE, f"{nn}-ds")
    write_dataset(root, files)
    return manifest(root, os.path.join(HERE, f"{nn}-manifest.txt"))


def program(nn, name, text):
    with open(os.path.join(HERE, f"{nn}-{name}.rl"), "w", encoding="ascii") as f:
        f.write(text)
