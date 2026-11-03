"""The fixed readers: each ambiguity is refused with the rule that names it."""
import gzip
import hashlib
import struct
from fractions import Fraction

import pytest

import bidsfix
import helpers
from reality4 import readers as R
from reality4.readers import Refusal


def tsv(data):
    return R.parse_tsv(data, "0" * 64, R.Steps())


def code(f, *a):
    with pytest.raises(Refusal) as e:
        f(*a)
    print(e.value.code, e.value.msg)
    return e.value.code


def test_tsv_plain():
    t = tsv(b"a\tb\n1\t2\n3\t4\n")
    assert t.header == ["a", "b"] and t.rows == [["1", "2"], ["3", "4"]]
    assert tsv(b"a\tb\n1\t2").rows == [["1", "2"]]          # last line without LF: one reading
    assert tsv(b"a\n").rows == []


@pytest.mark.parametrize("data,c", [
    (b"a\tb\r1\t2\n", "T002"),       # a lone CR: line end or part of a cell
    (b"a\n\xff\n", "T001"),               # not UTF-8
    (b"", "T003"),                        # no header
    (b"a\n1\n\n2\n", "T003"),             # empty line: a row with one empty cell or no row
    (b"a\n\n", "T003"),
    (b"a\tb\n1\n", "T004"),               # ragged
    (b"a\n1\t2\n", "T004"),
])
def test_tsv_refusals(data, c):
    assert code(tsv, data) == c


def test_decimal():
    assert R.decimal("4.071") == Fraction(4071, 1000)
    assert R.decimal("-0.5") == Fraction(-1, 2)
    assert R.decimal("007") is None and R.decimal("0") == 0   # taste call 5 (26 Oct 2026): no leading zero, as in JSON
    # v4 SPEC 6.4: one grammar with JSON, so exponents read exactly (Patsak, 25 Oct 21:36)
    assert R.decimal("1e3") == 1000 and R.decimal("1.5E-2") == Fraction(3, 200) and R.decimal("-2e+1") == -20
    for bad in ("", "-", "1.", ".5", "e3", "1e", "1e+", "1e1.5", "1e3e1", "+1", "1,5", "\u0661", " 1", "n/a", "NaN", "1.2.3"):
        assert R.decimal(bad) is None, bad


def test_json():
    assert R.parse_json(b'{"RepetitionTime": 1.5}', "x") == {"RepetitionTime": Fraction(3, 2)}
    assert R.parse_json(b'{"a": 0.1}', "x")["a"] == Fraction(1, 10)      # exact, not a float
    assert code(R.parse_json, b'{"a": 1, "a": 2}', "x") == "J002"
    assert code(R.parse_json, b'{"a": NaN}', "x") == "J003"
    assert code(R.parse_json, b'{"a": Infinity}', "x") == "J003"
    assert code(R.parse_json, b'{"a": 1,}', "x") == "J001"
    assert code(R.parse_json, b'{"a": "\\ud800"}', "x") == "J003"
    assert code(R.parse_json, b'\xef\xbb\xbf{}', "x") == "T001"


def test_nifti_header_both_versions_and_gzip(tmp_path):
    img = bidsfix.nifti1((2, 2, 2, 7), tr=0.72)
    hd = R.nifti_header(img, "x")
    assert hd.version == 1 and hd.dim[:5] == [4, 2, 2, 2, 7] and hd.pixdim[4] == Fraction(struct.unpack("<f", struct.pack("<f", 0.72))[0])
    p = tmp_path / "a.nii.gz"
    p.write_bytes(bidsfix.gzip_stored(img))
    assert R.nifti_read(str(p), True, "a", full=True).dim[4] == 7
    assert gzip.decompress(p.read_bytes()) == img          # the stored-block gzip is real gzip
    # NIfTI-2
    h2 = bytearray(544)
    struct.pack_into("<i", h2, 0, 540)
    h2[4:12] = b"n+2\x00\r\n\x1a\n"
    struct.pack_into("<2h", h2, 12, 16, 32)
    struct.pack_into("<8q", h2, 16, 3, 4, 5, 6, 1, 1, 1, 1)
    struct.pack_into("<q", h2, 168, 544)
    hd2 = R.nifti_header(bytes(h2), "y")
    assert hd2.version == 2 and hd2.dim[:4] == [3, 4, 5, 6] and hd2.data_bytes() == 544 + 120 * 4


def test_nifti_refusals(tmp_path):
    img = bidsfix.nifti1((2, 2, 2))
    assert code(R.nifti_header, b"xx", "x") == "I001"
    assert code(R.nifti_header, img[:344] + b"ni1\x00" + img[348:], "x") == "I001"
    bad = bytearray(img)
    struct.pack_into("<2h", bad, 70, 16, 8)          # float32 with 8 bits
    assert code(R.nifti_header, bytes(bad), "x") == "I002"
    short = tmp_path / "s.nii"
    short.write_bytes(img[:-1])
    assert code(R.nifti_read, str(short), False, "s", True) == "I003"
    cut = tmp_path / "c.nii.gz"
    cut.write_bytes(bidsfix.gzip_stored(img)[:-6])
    assert code(R.nifti_read, str(cut), True, "c", True) == "I004"


def test_manifest_roundtrip_and_refusals(tmp_path):
    (tmp_path / "d" / "s").mkdir(parents=True)
    (tmp_path / "d" / "b.txt").write_bytes(b"b")
    (tmp_path / "d" / "s" / "a.txt").write_bytes(b"a")
    m = R.make_manifest(str(tmp_path / "d"))
    ents = R.parse_manifest(m, "x")
    assert list(ents) == ["b.txt", "s/a.txt"]
    assert ents["b.txt"] == (hashlib.sha256(b"b").hexdigest(), 1)
    h = "a" * 64
    for bad in (b"reality-manifest 1\n" + f"{h}\t1\tb\n{h}\t1\ta\n".encode(),     # not sorted
                b"reality-manifest 1\n" + f"{h}\t1\ta\n{h}\t1\ta\n".encode(),     # twice
                b"reality-manifest 1\n" + f"{h}\t1\ta\n{h}\t1\ta/b\n".encode()):  # file and folder
        assert code(R.parse_manifest, bad, "x") == "M002"
    for bad in (b"reality-manifest 2\n", b"reality-manifest 1", b"reality-manifest 1\n" + f"{h}\t01\ta\n".encode(),
                b"reality-manifest 1\n" + f"{h}\t1\t../a\n".encode(), b"reality-manifest 1\n" + f"{h}\t1\t/a\n".encode(),
                b"reality-manifest 1\n" + f"{h}\t1\ta\\b\n".encode()):
        assert code(R.parse_manifest, bad, "x") == "M001"


def test_store_finds_by_hash_not_path(tmp_path):
    """Item 4: the verdict does not depend on where or in which order files are supplied."""
    a = tmp_path / "one"
    b = tmp_path / "two" / "deeper"
    a.mkdir()
    b.mkdir(parents=True)
    (a / "x.tsv").write_bytes(b"h\n1\n2\n")
    (b / "renamed.dat").write_bytes(b"h\n1\n2\n")
    h = helpers.sha(str(a / "x.tsv"))
    prog = f"file f = sha256:{h}\nclaim rows(tsv(f))\n"
    outs = {helpers.run(prog, fs)[1] for fs in ([str(a)], [str(b)], [str(b), str(a)], [str(a), str(b)])}
    assert len(outs) == 1
    ok, text = helpers.run(prog, [str(tmp_path / "two" / "nothing")])
    assert not ok and "[F001, text]" in text


def test_root_path_with_wrong_bytes_is_not_used(tmp_path):
    root = bidsfix.mini(str(tmp_path / "ds"))
    md = tmp_path / "m"
    md.mkdir()
    mh = helpers.manifest(root, str(md))
    (tmp_path / "ds" / "participants.tsv").write_bytes(b"participant_id\tgroup\nsub-01\tz\nsub-02\ta\n")
    ok, text = helpers.run(f"dataset d = sha256:{mh}\nclaim count(participants(bids(d)))\n", [str(md)], [root])
    assert not ok and "[F001, text]" in text and "participants.tsv" in text


def test_tsv_bom_marks_only_the_first_header_name():
    """SPEC 6.1 (25 Oct 2026, with principle section 12): a byte-order mark makes the first header
    name ambiguous (with U+FEFF or not) and nothing else; the kernel refuses a use of that name
    (T011). The BIDS reader still refuses the file (T001)."""
    t = R.parse_tsv(b"\xef\xbb\xbfa\tb\n1\t2\n", "x", R.Steps())
    assert t.bom and t.header == ["a", "b"] and t.rows == [["1", "2"]]
    assert not R.parse_tsv(b"a\n1\n", "x", R.Steps()).bom
    with pytest.raises(R.Refusal) as e:
        R.parse_tsv(b"\xef\xbb\xbfa\n1\n", "x", R.Steps(), bids=True)
    assert e.value.code == "T001"


def test_gz_header_read_is_bounded_in_both_readers(tmp_path):
    """Phase G (25 Oct 2026): the BIDS reader's .nii.gz header read used gzip.open, which reads
    any number of compressed bytes to reach 544 header bytes (empty deflate blocks give none).
    Both readers now share gz_head, bounded by MAX_GZ_HEAD (R003)."""
    import zlib
    hdr = bidsfix.nifti1((2, 2, 2, 5), tr=2.0)
    empty = b"\x00\x00\x00\xff\xff" * (R.MAX_GZ_HEAD // 5 + 10)    # stored blocks of length 0
    body = zlib.compressobj(9, zlib.DEFLATED, -15)
    data = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff" + empty + body.compress(hdr) + body.flush()
    p = tmp_path / "x.nii.gz"
    p.write_bytes(data)
    with pytest.raises(Refusal) as e:
        R.nifti_read(str(p), True, "x.nii.gz", False)
    assert e.value.code == "R003"
    ok = tmp_path / "ok.nii.gz"
    ok.write_bytes(gzip.compress(hdr))
    assert R.nifti_read(str(ok), True, "ok.nii.gz", False).dim[4] == 5


def test_a_gzip_image_read_whole_is_counted_as_it_decompresses(tmp_path, monkeypatch):
    """(B05, Argon review 2 05) Store.nifti(full=True) (the BIDS gate's call on every image) charged a .nii.gz by its
    compressed size (size // 4096 + 1) and decompressed the whole stream with no count: a 8 MB file of gzip members of
    zeros took ~1,000 times the time of another of its size for the same 2,040 steps. Each chunk is now counted as it
    is read (per 4096 decompressed bytes), on the statement's steps (R002 stops the loop), and charged on every use;
    witness.MemStore.nifti (a certificate input) the same."""
    from reality4 import witness as W
    zeros = gzip.compress(b"\x00" * (16 << 20), compresslevel=9, mtime=0)
    data = gzip.compress(bidsfix.nifti1((2, 2, 2, 5)), mtime=0) + zeros * 4   # 64 MiB of zeros after the image
    p = tmp_path / "b.nii.gz"
    p.write_bytes(data)
    h = hashlib.sha256(data).hexdigest()
    least = (64 << 20) // 4096
    st = R.Store([str(p)], [])
    st.begin_program()
    st.begin()
    assert st.nifti(h, "b.nii.gz", True).dim[4] == 5 and st.steps.n >= least, st.steps.n
    st.begin()
    st.nifti(h, "b.nii.gz", True)
    assert st.steps.n >= least, st.steps.n   # charged again on a later use (the memo keeps the count)
    ms = W.MemStore({h: data})
    assert ms.nifti(h, "b.nii.gz", True).dim[4] == 5 and ms.steps.n >= least, ms.steps.n
    monkeypatch.setattr(R, "MAX_STEPS", least // 2)
    st = R.Store([str(p)], [])
    st.begin_program()
    st.begin()
    with pytest.raises(Refusal) as e:
        st.nifti(h, "b.nii.gz", True)
    assert e.value.code == "R002"
