"""Test fixtures for the BIDS 1.0.1 reader.

`box_copy()` is the box copy of OpenNeuro ds001734 (events and sidecars, no images), as the
spec's §4 describes it; tests/data/ds001734-box/ must be byte-identical to it (test_fixture_pin).

`complete_copy(dst)` is a FABRICATED test dataset: the box copy plus a tiny made-up NIfTI file
(2x2x64 voxels for BOLD, so the 64 SliceTiming entries match its slice axis; 2x2x2 otherwise) at every imaging path that KEYS.txt lists. It exists only to exercise the
reader's forming path. It is not ds001734 and no claim about NARPS rests on it; the real
complete dataset is checked on the PC (tests_pc/). Every byte is written by this file, so the
hashes are the same on every machine (no compressor is used: the .nii.gz files hold stored,
uncompressed deflate blocks).
"""

import os
import shutil
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
BOX = os.path.join(HERE, "data", "ds001734-box")
BOX_MANIFEST_SHA256 = "b6850de7d9ed854e78149bb842325892c4e888e312969b8812ea1fc9f9f0e4f2"
PARTICIPANTS_SHA256 = "d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8"


def box_copy():
    if not os.path.isdir(BOX):
        raise RuntimeError(f"missing fixture {BOX}: copy neuro/data/ds001734 there (see DATA.md / .gitignore)")
    return BOX


def nifti1(dims, tr=1.0, units=10, datatype=2, bitpix=8, pixdim4=None):
    """A minimal single-file NIfTI-1 image: header, 4 extension bytes, then zeros."""
    hdr = bytearray(348)
    struct.pack_into("<i", hdr, 0, 348)
    d = [len(dims)] + list(dims) + [1] * (7 - len(dims))
    struct.pack_into("<8h", hdr, 40, *d)
    struct.pack_into("<2h", hdr, 70, datatype, bitpix)
    pix = [1.0, 1.0, 1.0, 1.0, tr if pixdim4 is None else pixdim4, 0.0, 0.0, 0.0]
    struct.pack_into("<8f", hdr, 76, *pix)
    struct.pack_into("<f", hdr, 108, 352.0)
    hdr[123] = units
    hdr[344:348] = b"n+1\x00"
    n = 1
    for x in dims:
        n *= x
    return bytes(hdr) + b"\x00" * 4 + b"\x00" * (n * bitpix // 8)


def gzip_stored(data: bytes) -> bytes:
    """gzip with stored (uncompressed) deflate blocks: the same bytes on every machine."""
    out = bytearray(b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff")
    i = 0
    while True:
        blk = data[i:i + 65535]
        i += len(blk)
        final = 1 if i >= len(data) else 0
        out += bytes([final]) + struct.pack("<HH", len(blk), 0xFFFF ^ len(blk)) + blk
        if final:
            break
    out += struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data) & 0xFFFFFFFF)
    return bytes(out)


def complete_copy(dst, bold_volumes=453, skip=(), extra=None):
    """bold_volumes: 453 so that every onset of the box copy (at most 441.062 s, TR 1 s) lies
    inside its run (v4 taste call 3: onsets after the end refuse B30). The in-plane size is 1 x 1
    to keep the made-up files small; the real counts are checked in Phase H, not here."""
    shutil.copytree(box_copy(), dst)
    with open(os.path.join(dst, "KEYS.txt"), encoding="utf-8") as f:
        keys = [k.strip() for k in f if k.strip()]
    for k in keys:
        rel = k.split("/", 1)[1]
        if not rel.endswith(".nii.gz") or rel in skip:
            continue
        dims = (1, 1, 64, bold_volumes) if rel.endswith("_bold.nii.gz") else (2, 2, 2)
        os.makedirs(os.path.join(dst, *rel.split("/")[:-1]), exist_ok=True)
        with open(os.path.join(dst, *rel.split("/")), "wb") as f:
            f.write(gzip_stored(nifti1(dims)))
    if extra:
        for rel, data in extra.items():
            p = os.path.join(dst, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data)
    return dst


def write(dst, rel, data):
    p = os.path.join(dst, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def mini(dst, subjects=("01", "02"), version="1.0.1", participants=True, groups=None, extra=None,
         drop=(), task_json=None, events=None, ext="nii"):
    """A small made-up BIDS dataset (test fixture only): one task 'x', one run per subject."""
    os.makedirs(dst, exist_ok=True)
    if version is not None:
        write(dst, "dataset_description.json", '{"Name": "mini", "BIDSVersion": "%s"}' % version)
    write(dst, "README", "A made-up test dataset.\n")
    write(dst, "task-x_bold.json", task_json or '{"TaskName": "x", "RepetitionTime": 2}')
    if participants:
        rows = "".join(f"sub-{s}\t{(groups or {}).get(s, 'a')}\n" for s in subjects)
        write(dst, "participants.tsv", "participant_id\tgroup\n" + rows)
    for s in subjects:
        img = nifti1((2, 2, 2, 5), tr=2.0)
        write(dst, f"sub-{s}/func/sub-{s}_task-x_bold.{ext}", gzip_stored(img) if ext == "nii.gz" else img)
        write(dst, f"sub-{s}/func/sub-{s}_task-x_events.tsv", events or "onset\tduration\tkind\n1.5\t2\tA\n7.25\t2\tB\n")
    for rel in drop:
        os.remove(os.path.join(dst, *rel.split("/")))
    for rel, data in (extra or {}).items():
        write(dst, rel, data)
    return dst
