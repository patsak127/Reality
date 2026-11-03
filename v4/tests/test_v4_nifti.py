"""v4 SPEC 7.6: one hashed file read as a NIfTI header, without the BIDS dataset check
(principle section 1 lists NIfTI among the file-level readers). Patsak 25 Oct 21:14: a header's
time value is Recorded, printed as the exact stored value."""
import gzip
import hashlib
import struct

from helpers import run


def header(ndim=4, n=240, step=1.52, unit=8, end="<", version=1):
    b = bytearray(352)
    struct.pack_into(end + "i", b, 0, 348)
    struct.pack_into(end + "8h", b, 40, ndim, 64, 64, 30, n, 1, 1, 1)
    struct.pack_into(end + "2h", b, 70, 16, 32)
    struct.pack_into(end + "8f", b, 76, 1, 3, 3, 3, step, 0, 0, 0)
    struct.pack_into(end + "f", b, 108, 352.0)
    b[123] = unit | 2
    b[344:348] = b"n+1\x00"
    return bytes(b)


def first(tmp_path, data, claim, name="bold.nii"):
    p = tmp_path / name
    p.write_bytes(data)
    h = hashlib.sha256(data).hexdigest()
    ok, text = run(f"file f = sha256:{h}\nlet n = nifti(f)\n{claim}\n", [str(p)])
    return ok, text.split("\n")[0]


def test_volumes_from_one_header(tmp_path):
    ok, line = first(tmp_path, header(), "claim dim(n, 4)")
    assert ok and line == "line 3: formed: Dim[NIfTI-1[#1], 4] = 240 (Exact)", line


def test_time_step_is_recorded_as_the_exact_float(tmp_path):
    ok, line = first(tmp_path, header(), "claim pixdim(n, 4)")
    assert ok and line == "line 3: formed: Pixdim[NIfTI-1[#1], 4] is recorded as 1.519999980926513671875 s (Recorded[s])", line


def test_time_step_in_ms_is_converted_exactly(tmp_path):
    ok, line = first(tmp_path, header(step=1520, unit=16), "claim pixdim(n, 4)")
    assert ok and line.endswith("is recorded as 1.52 s (Recorded[s])"), line


def test_recorded_step_compares_against_a_cutoff(tmp_path):
    assert first(tmp_path, header(), "claim below(pixdim(n, 4), c = 1.52 s)")[0]   # 1.5199999... < 1.52
    ok, line = first(tmp_path, header(), "claim pixdim(n, 4) is 1.52 s")
    assert not ok and "[V001" in line, line


def test_gzip_by_magic_and_big_endian(tmp_path):
    ok, line = first(tmp_path, gzip.compress(header(end=">") + b"\0" * 64), "claim dim(n, 4)", name="x.bin")
    assert ok and line.endswith("= 240 (Exact)"), line


def test_three_d_header_has_no_time(tmp_path):
    for claim in ("claim dim(n, 4)", "claim pixdim(n, 4)"):
        ok, line = first(tmp_path, header(ndim=3), claim)
        assert not ok and "[V008" in line, line


def test_unknown_time_unit_refuses_i005(tmp_path):
    ok, line = first(tmp_path, header(unit=0), "claim pixdim(n, 4)")
    assert not ok and "[I005" in line, line
    ok, line = first(tmp_path, header(unit=32), "claim pixdim(n, 4)")   # Hz: not a time
    assert not ok and "[I005" in line, line


def test_spatial_pixdim_is_not_read(tmp_path):
    ok, line = first(tmp_path, header(), "claim pixdim(n, 1)")
    assert not ok and "[S006" in line, line


def test_not_nifti_and_broken_gzip_refuse(tmp_path):
    ok, line = first(tmp_path, b"hello world" * 40, "claim dim(n, 4)")
    assert not ok and "[I001" in line, line
    ok, line = first(tmp_path, b"\x1f\x8b" + b"\x00" * 400, "claim dim(n, 4)")
    assert not ok and "[I004" in line, line


def test_idle_nifti_value_refuses(tmp_path):
    ok, line = first(tmp_path, header(), "claim difference(dim(n, 4), dim(n, 4))")
    assert not ok and "[S008" in line, line
    p = tmp_path / "h.nii"
    p.write_bytes(header())
    h = hashlib.sha256(header()).hexdigest()
    ok, text = run(f"file f = sha256:{h}\nlet n = nifti(f)\nlet x = pixdim(n, 4)\nclaim below(difference(x, widen(x, tolerance = 1 s)), c = 2 s)\n", [str(p)])
    assert not ok and "W1" in text.split("\n")[0], text
