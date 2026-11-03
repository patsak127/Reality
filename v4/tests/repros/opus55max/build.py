"""Build every supplied file, made-up dataset, manifest and program used by the findings.

    python -I findings\\build.py

Deterministic: every byte is written by this script (no compressor, no clock), so the hashes
named in the .rl files are the same on every machine. Datasets go to findings\\NN-ds\\, their
Reality manifests to findings\\NN-m\\<sha256>.manifest (the dataset's name). The two large
generated inputs of findings 13 and 14 are written by 13-gen.py and 14-gen.py instead.
Everything made up here is a TEST FIXTURE, not data from any study."""
import hashlib
import os
import shutil
import struct
import sys

F = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(F)
sys.path.insert(0, os.path.join(ROOT, "src"))
from reality2 import readers  # noqa: E402

BOX = os.path.join(ROOT, "tests", "data", "ds001734-box")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def put(rel, data):
    p = os.path.join(F, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data.encode("utf-8") if isinstance(data, str) else data)
    return p


def program(name, text):
    assert "\r" not in text
    put(name, text)


def nifti1(dims, pixdim4, units=10):
    """Single-file NIfTI-1, uint8, header + 4 extension bytes + zeros (as tests/bidsfix.py)."""
    hdr = bytearray(348)
    struct.pack_into("<i", hdr, 0, 348)
    d = [len(dims)] + list(dims) + [1] * (7 - len(dims))
    struct.pack_into("<8h", hdr, 40, *d)
    struct.pack_into("<2h", hdr, 70, 2, 8)
    struct.pack_into("<8f", hdr, 76, 1.0, 1.0, 1.0, 1.0, pixdim4, 0.0, 0.0, 0.0)
    struct.pack_into("<f", hdr, 108, 352.0)
    hdr[123] = units
    hdr[344:348] = b"n+1\x00"
    n = 1
    for x in dims:
        n *= x
    return bytes(hdr) + b"\x00" * 4 + b"\x00" * n


def nifti2(dims, pixdim4, units=10):
    """Single-file NIfTI-2, uint8; pixdim is float64 in NIfTI-2."""
    h = bytearray(544)
    struct.pack_into("<i", h, 0, 540)
    h[4:12] = b"n+2\x00\r\n\x1a\n"
    struct.pack_into("<2h", h, 12, 2, 8)
    d = [len(dims)] + list(dims) + [1] * (7 - len(dims))
    struct.pack_into("<8q", h, 16, *d)
    struct.pack_into("<8d", h, 104, 1.0, 1.0, 1.0, 1.0, pixdim4, 0.0, 0.0, 0.0)
    struct.pack_into("<q", h, 168, 544)
    struct.pack_into("<i", h, 500, units)
    n = 1
    for x in dims:
        n *= x
    return bytes(h) + b"\x00" * n


DESC = '{"Name": "made-up test fixture", "BIDSVersion": "1.0.1"}'


def dataset(nn, files, edit=None, tag=""):
    """Write findings/NN-ds{tag}/ and its manifest findings/NN-m{tag}/<sha>.manifest. -> sha."""
    ds = os.path.join(F, f"{nn}-ds{tag}")
    md = os.path.join(F, f"{nn}-m{tag}")
    for d in (ds, md):
        if os.path.isdir(d):
            shutil.rmtree(d)
    for rel, data in files.items():
        put(f"{nn}-ds{tag}/{rel}", data)
    man = readers.make_manifest(ds)
    if edit:
        man = edit(man)
    h = sha(man)
    put(f"{nn}-m{tag}/{h}.manifest", man)
    return h


def manifest_only(nn, man, tag=""):
    md = os.path.join(F, f"{nn}-m{tag}")
    if os.path.isdir(md):
        shutil.rmtree(md)
    h = sha(man)
    put(f"{nn}-m{tag}/{h}.manifest", man)
    return h


def mini(subjects=("01",), events="onset\tduration\n1.5\t2\n", task_json='{"TaskName": "x", "RepetitionTime": 2}'):
    files = {"dataset_description.json": DESC, "task-x_bold.json": task_json,
             "participants.tsv": "participant_id\tgroup\n" + "".join(f"sub-{s}\ta\n" for s in subjects)}
    for s in subjects:
        files[f"sub-{s}/func/sub-{s}_task-x_bold.nii"] = nifti1((2, 2, 2, 5), 2.0)
        files[f"sub-{s}/func/sub-{s}_task-x_events.tsv"] = events
    return files


hashes = {}

# ---- 01: the int-to-str digit limit of the interpreter decides the verdict -------------------
long_cell = "v\n" + "1" * 5000 + "\n"
put("01-long-cell.tsv", long_cell)
h01 = sha(long_cell.encode())
program("01-int-digit-limit.rl",
        f"# The cell holds a decimal of 5000 digits (valid under the decimal reader -?[0-9]+).\n"
        f"file f = sha256:{h01}\n"
        "claim rows(tsv(f))\n"
        "claim exceeds(number(cell(tsv(f), 1, 1)), c = 1)\n")
f01 = mini()
f01["task-x_bold.json"] = '{"TaskName": "x", "RepetitionTime": 2.' + "0" * 5000 + "}"
m01 = dataset("01", f01)
program("01-int-digit-limit-b.rl",
        f"# task-x_bold.json is valid RFC 8259 JSON: RepetitionTime is 2.000...0 (5000 zeros).\n"
        f"dataset d = sha256:{m01}\n"
        "let b = bids(d)\n"
        "claim count(participants(b))\n"
        "claim tr(recording(b, \"01\", \"x\"))\n")
program("01-int-digit-limit-c.rl",
        f"file f = sha256:{h01}\n"
        "claim rows(tsv(f))\n"
        "claim rows(tsv(f)) is " + "0" * 4400 + "1\n")

# ---- 02: N17's text forms from the box copy through a zero-subject manifest -------------------
box_man = readers.make_manifest(BOX)
hb = manifest_only("02", box_man, tag="-box")
lines = box_man.decode("utf-8").split("\n")
root_only = "\n".join([lines[0]] + [ln for ln in lines[1:-1] if "/" not in ln.split("\t")[2]]) + "\n"
m02 = manifest_only("02", root_only.encode("utf-8"))
head02 = f"dataset d = sha256:{m02}\nlet b = bids(d)\n"
program("02-n17-zero-subject-dataset.rl",
        "# The manifest lists the box copy's 8 root files, byte for byte, and nothing under sub-*/.\n"
        + head02 +
        "claim count(where(participants(b), eq(\"group\", \"equalRange\"))) is 54\n"
        "claim share(where(participants(b), eq(\"group\", \"equalRange\"))) is 54/108\n"
        "claim count(where(participants(b), eq(\"gender\", \"F\"))) is 60\n")
program("02-n17-box.rl",
        "# N17 as the acceptance test writes it: the box copy's full manifest.\n"
        f"dataset d = sha256:{hb}\nlet b = bids(d)\n"
        "claim count(where(participants(b), eq(\"group\", \"equalRange\"))) is 54\n")

# ---- 03: difference() of onsets measured from different reference events ---------------------
f03 = mini(subjects=("01", "02"))
f03["sub-01/func/sub-01_task-x_events.tsv"] = "onset\tduration\n1.5\t2\n9.25\t2\n"
f03["sub-02/func/sub-02_task-x_events.tsv"] = "onset\tduration\n7.25\t2\n"
f03["sub-02/func/sub-02_task-x_bold.nii"] = nifti1((2, 2, 2, 6), 2.0)   # a different image from sub-01's
m03 = dataset("03", f03)
program("03-onset-difference-across-recordings.rl",
        f"dataset d = sha256:{m03}\n"
        "let b = bids(d)\n"
        "let r1 = recording(b, \"01\", \"x\")\n"
        "let r2 = recording(b, \"02\", \"x\")\n"
        "# onsets are seconds from the first volume of *their own* recording (two different events)\n"
        "claim difference(onset(r2, 1), onset(r1, 1))\n"
        "claim exceeds(difference(onset(r2, 1), onset(r1, 1)), c = 5)\n"
        "# a duration minus a time point\n"
        "claim difference(tr(r1), onset(r1, 1))\n"
        "# for contrast, a meaningful one: two events of one recording\n"
        "claim difference(onset(r1, 2), onset(r1, 1))\n")

# ---- 04: let-chain, exponential time ----------------------------------------------------------
cells04 = "id\tv\na\t1\nb\t2\n"
put("04-cells.tsv", cells04)
h04 = sha(cells04.encode())


def lets(n):
    out = [f"file f = sha256:{h04}", "let x0 = number(cell(tsv(f), 1, 2))"]
    out += [f"let x{i} = difference(x{i - 1}, x{i - 1})" for i in range(1, n + 1)]
    return "\n".join(out + [f"claim exceeds(x{n}, c = -1)"]) + "\n"


program("04-let-chain-exponential.rl", lets(20))
program("04-let-chain-exponential-n16.rl", lets(16))
program("04-let-chain-exponential-n18.rl", lets(18))

# ---- 05: the manifest decides which subjects and runs the dataset has (judgement call) --------
f05 = {"dataset_description.json": DESC,
       "task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, '
                           '"EffectiveEchoSpacing": 0.0003, "PhaseEncodingDirection": "j-"}',
       "participants.tsv": "participant_id\tgroup\nsub-01\ta\nsub-02\tb\n"}
for s in ("01", "02"):
    for run in ("1", "2"):
        f05[f"sub-{s}/func/sub-{s}_task-x_run-{run}_bold.nii"] = nifti1((2, 2, 2, 5 + int(run)), 2.0)
        f05[f"sub-{s}/func/sub-{s}_task-x_run-{run}_events.tsv"] = f"onset\tduration\n{run}.5\t2\n"
    f05[f"sub-{s}/fmap/sub-{s}_phasediff.nii"] = nifti1((2, 2, 2), 1.0)
    f05[f"sub-{s}/fmap/sub-{s}_magnitude1.nii"] = nifti1((2, 2, 2), 1.0)
    f05[f"sub-{s}/fmap/sub-{s}_phasediff.json"] = (
        '{"EchoTime1": 0.0049, "EchoTime2": 0.0074, "IntendedFor": '
        f'["func/sub-{s}_task-x_run-1_bold.nii", "func/sub-{s}_task-x_run-2_bold.nii"]}}')
m05_full = dataset("05", f05)
full = open(os.path.join(F, "05-m", m05_full + ".manifest"), "rb").read().decode().split("\n")
keep_b = [ln for ln in full[1:-1] if not ln.split("\t")[2].startswith("sub-02/")]
keep_c = [ln for ln in full[1:-1] if "run-2" not in ln.split("\t")[2] or not ln.split("\t")[2].startswith("sub-01/")]
mb = "\n".join([full[0]] + keep_b) + "\n"
mc = "\n".join([full[0]] + keep_c) + "\n"
m05_b = sha(mb.encode())
m05_c = sha(mc.encode())
put(f"05-m/{m05_b}.manifest", mb)
put(f"05-m/{m05_c}.manifest", mc)
program("05-manifest-selection.rl",
        f"dataset full = sha256:{m05_full}\n"
        f"dataset nosub02 = sha256:{m05_b}\n"
        f"dataset norun2 = sha256:{m05_c}\n"
        "claim count(participants(bids(full)))\n"
        "# sub-02's folder (4 images, 2 events files, a sidecar) left out; its row is still there\n"
        "claim count(participants(bids(nosub02)))\n"
        "claim extra(participant(bids(nosub02), \"02\"), \"group\")\n"
        "# sub-01 run 2 (BOLD and events) left out, though sub-01's phasediff.json IntendedFor names it\n"
        "claim volumes(recording(bids(norun2), \"01\", \"x\", \"1\"))\n"
        "claim volumes(recording(bids(norun2), \"01\", \"x\", \"2\"))\n")

# ---- 06: memory decides the verdict -----------------------------------------------------------
wide = "\t".join(f"c{i}" for i in range(1000)) + "\n" + ("\t".join(["12"] * 1000) + "\n") * 330
put("06-wide.tsv", wide)
program("06-memory-decides-verdict.rl",
        "# a 1 MB TSV; the reader's bounds allow 64 MB per file and 512 MB per check\n"
        f"file f = sha256:{sha(wide.encode())}\nclaim rows(tsv(f))\n")

# ---- 07: console encoding decides the output -------------------------------------------------
f07 = {"dataset_description.json": DESC, "participants.tsv": "participant_id\tgroup\nsub-\u03a901\ta\n"}
m07 = dataset("07", f07)
p07 = sha(f07["participants.tsv"].encode("utf-8"))
program("07-console-encoding.rl",
        f"dataset d = sha256:{m07}\nfile p = sha256:{p07}\n"
        "claim count(participants(bids(d)))\n"
        "claim rows(tsv(p))\n")

# ---- 08: idle conditions in where() ------------------------------------------------------------
t08 = "id\tgroup\ns1\tA\ns2\tB\ns3\tA\n"
put("08-table.tsv", t08)
program("08-idle-where-conditions.rl",
        f"file f = sha256:{sha(t08.encode())}\n"
        "let t = tsv(f)\n"
        "claim count(where(t, eq(2, \"A\")))\n"
        "claim count(where(t, eq(2, \"A\"), eq(2, \"A\")))\n"
        "claim count(where(t, eq(2, \"A\"), ne(2, \"B\")))\n"
        "claim count(where(t, ne(2, \"\\xff\")))\n"
        "claim count(where(t, ne(2, \"A\\x09B\")))\n"
        "claim count(where(t, eq(2, \"A\"), ne(2, \"A\")))\n"
        "claim share(where(t, ne(2, \"\\xff\")))\n")

# ---- 09: two columns named onset ----------------------------------------------------------------
f09 = mini(events="onset\tduration\tonset\n1.5\t2\t9.75\n")
m09 = dataset("09", f09)
e09 = sha(f09["sub-01/func/sub-01_task-x_events.tsv"].encode())
program("09-duplicate-onset-column.rl",
        f"dataset d = sha256:{m09}\nfile e = sha256:{e09}\n"
        "let r = recording(bids(d), \"01\", \"x\")\n"
        "claim onset(r, 1)\n"
        "claim header(tsv(e), 3)\n"
        "claim number(cell(tsv(e), 1, 3))\n"
        "claim number(cell(tsv(e), 1, \"onset\"))\n")

# ---- 10: sidecar precedence that 1.0.1 does not define ------------------------------------------
f10 = {"dataset_description.json": DESC,
       "task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2}',
       "participants.tsv": "participant_id\tgroup\nsub-01\ta\n",
       "sub-01/func/sub-01_task-x_acq-a_rec-b_run-1_bold.nii": nifti1((2, 2, 2, 5), 2.0),
       "sub-01/func/sub-01_task-x_acq-a_rec-b_run-1_events.tsv": "onset\tduration\n1.5\t2\n",
       "sub-01/func/sub-01_task-x_acq-a_rec-b_bold.json": '{"RepetitionTime": 2}',
       "sub-01/func/sub-01_task-x_run-1_bold.json": '{"RepetitionTime": 2.0000001}'}
m10 = dataset("10", f10)
program("10-sidecar-precedence.rl",
        f"dataset d = sha256:{m10}\n"
        "claim tr(recording(bids(d), \"01\", \"x\", \"1\"))\n")

# ---- 11: one run index, two recordings --------------------------------------------------------
f11 = {"dataset_description.json": DESC, "task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2}',
       "participants.tsv": "participant_id\tgroup\nsub-01\ta\nsub-02\tb\n",
       "sub-01/func/sub-01_task-x_run-1_bold.nii": nifti1((2, 2, 2, 5), 2.0),
       "sub-01/func/sub-01_task-x_run-1_events.tsv": "onset\tduration\n1.5\t2\n",
       "sub-01/func/sub-01_task-x_run-01_bold.nii": nifti1((2, 2, 2, 7), 2.0),
       "sub-01/func/sub-01_task-x_run-01_events.tsv": "onset\tduration\n3.25\t2\n",
       "sub-02/func/sub-02_task-x_bold.nii": nifti1((2, 2, 2, 4), 2.0),
       "sub-02/func/sub-02_task-x_events.tsv": "onset\tduration\n0.5\t2\n",
       "sub-02/func/sub-02_task-x_run-1_bold.nii": nifti1((2, 2, 2, 9), 2.0),
       "sub-02/func/sub-02_task-x_run-1_events.tsv": "onset\tduration\n6\t2\n"}
m11 = dataset("11", f11)
program("11-run-index-two-recordings.rl",
        f"dataset d = sha256:{m11}\nlet b = bids(d)\n"
        "claim volumes(recording(b, \"01\", \"x\", \"1\"))\n"
        "claim volumes(recording(b, \"01\", \"x\", \"01\"))\n"
        "claim onset(recording(b, \"01\", \"x\", \"1\"), 1)\n"
        "claim onset(recording(b, \"01\", \"x\", \"01\"), 1)\n"
        "claim volumes(recording(b, \"02\", \"x\"))\n"
        "claim volumes(recording(b, \"02\", \"x\", \"1\"))\n")

# ---- 12: phenotype files (BIDS 1.0.1 §8.11) are never checked -----------------------------------
f12 = mini()
f12["phenotype/bdi.tsv"] = "score\twho\n12\tsomeone\n"
f12["phenotype/bdi.json"] = '{"score": {"Description": "x"}, "score": 1}'
m12 = dataset("12", f12)
program("12-phenotype-files-skipped.rl",
        f"dataset d = sha256:{m12}\n"
        "claim count(participants(bids(d)))\n")
# 12-b: other files 1.0.1 describes whose content v2 never checks (softer cases, see the .md)
f12b = mini(task_json='{"TaskName": "x", "RepetitionTime": 2, "EchoTime": 0.03, '
                      '"EffectiveEchoSpacing": 0.0003, "PhaseEncodingDirection": "j-"}')
f12b["sub-01/func/sub-01_task-x_sbref.nii"] = nifti1((2, 2, 2), 1.0)
f12b["sub-01/func/sub-01_task-x_sbref.json"] = '{"TaskName": "zzz", "RepetitionTime": -4}'
f12b["sub-01/fmap/sub-01_magnitude1.json"] = '{"EchoTime": 0.005}'
f12b["sub-01/fmap/sub-01_magnitude2.json"] = '{"EchoTime": 0.007}'
m12b = dataset("12", f12b, tag="-b")
program("12-phenotype-files-skipped-b.rl",
        f"dataset d = sha256:{m12b}\n"
        "claim count(participants(bids(d)))\n"
        "claim tr(recording(bids(d), \"01\", \"x\"))\n")

# ---- 15: a JSON exponent stalls the BIDS reader -------------------------------------------------
for tag, exp in (("", 60000000), ("-small", 10000000)):
    m15 = dataset("15", {"dataset_description.json": '{"Name": "x", "BIDSVersion": "1.0.1", "Size": 1e%d}' % exp,
                          "participants.tsv": "participant_id\tgroup\nsub-01\ta\n"}, tag=tag)
    program(f"15-json-exponent-stall{tag}.rl", f"dataset d = sha256:{m15}\nclaim count(participants(bids(d)))\n")

# ---- 16: X001 from valid JSON ------------------------------------------------------------------
f16 = mini(task_json='{"TaskName": "x", "RepetitionTime": 2, "PhaseEncodingDirection": ["j-"]}')
m16a = dataset("16", f16, tag="-a")
program("16-x001-from-valid-json.rl", f"dataset d = sha256:{m16a}\nclaim count(participants(bids(d)))\n")
m16b = dataset("16", {"dataset_description.json": '{"Name": "x", "BIDSVersion": "1.0.1", "Extra": '
                      + "[" * 970 + "]" * 970 + "}",
                      "participants.tsv": "participant_id\tgroup\nsub-01\ta\n"}, tag="-b")
program("16-x001-from-valid-json-b.rl",
        f"dataset d = sha256:{m16b}\n"
        "# the same dataset, read first from a deeper expression, then from a shallow one\n"
        "claim exceeds(widen(widen(widen(widen(widen(widen(widen(widen(number(extra(participant(bids(d), \"01\"), 2)), "
        "tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), tolerance = 0), c = 0)\n"
        "claim count(participants(bids(d)))\n")

# ---- 17: counts and shares cannot be compared --------------------------------------------------
P = "d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8"
program("17-counts-and-shares-cannot-be-compared.rl",
        f"file p = sha256:{P}\nlet t = tsv(p)\n"
        "claim exceeds(count(where(t, eq(2, \"equalRange\"))), c = 49)\n"
        "claim exceeds(share(where(t, eq(2, \"equalRange\"))), c = 0.4)\n"
        "claim difference(count(where(t, eq(2, \"equalRange\"))), count(where(t, eq(2, \"equalIndifference\"))))\n"
        "claim exceeds(sum(t, 4), c = 2000)\n"
        "claim exceeds(number(cell(t, 1, 4)), c = 20)\n")

# ---- 18: the differential test never checks 'is' -------------------------------------------------
t18 = "id\tgroup\tage\ns1\tA\t30\ns2\tB\t41\ns3\tA\t29\n"
put("18-table.tsv", t18)
program("18-differential-is.rl",
        f"file f = sha256:{sha(t18.encode())}\nlet t = tsv(f)\n"
        "claim share(where(t, eq(2, \"A\"))) is 1/3\n"
        "claim exceeds(number(cell(t, 1, 3)), c = 0) is 1\n")

# ---- 20: check 2 cannot see a reader that attaches the wrong file -------------------------------
f20 = {"dataset_description.json": DESC, "task-x_bold.json": '{"TaskName": "x", "RepetitionTime": 2}',
       "participants.tsv": "participant_id\tgroup\nsub-01\ta\n",
       "sub-01/func/sub-01_task-x_run-1_bold.nii": nifti1((2, 2, 2, 5), 2.0),
       "sub-01/func/sub-01_task-x_run-1_events.tsv": "onset\tduration\n1.5\t2\n",
       "sub-01/func/sub-01_task-x_run-2_bold.nii": nifti1((2, 2, 2, 6), 2.0),
       "sub-01/func/sub-01_task-x_run-2_events.tsv": "onset\tduration\n8.75\t2\n"}
m20 = dataset("20", f20)
program("20-check2-not-independent.rl",
        f"dataset d = sha256:{m20}\nclaim onset(recording(bids(d), \"01\", \"x\", \"1\"), 1)\n")

# ---- 21: renaming crosses the program-size bound -----------------------------------------------
t21 = "id\tgroup\ns1\tA\ns2\tB\ns3\tA\n"
put("21-table.tsv", t21)
body = lambda n: (f"file f = sha256:{sha(t21.encode())}\nlet {n} = tsv(f)\nclaim rows({n})\n"
                  f"claim count(where({n}, eq(2, \"A\")))\n")
a = body("t")
a += "# " + "x" * (1_000_000 - len(a) - 3) + "\n"
b = a.replace("let t =", "let tt =").replace("rows(t)", "rows(tt)").replace("where(t,", "where(tt,")
assert len(a) == 1_000_000 and len(b) == 1_000_003
program("21-rename-crosses-program-bound.rl", a)
program("21-rename-crosses-program-bound-renamed.rl", b)

# ---- 22: the manifest's sizes and extra entries are never checked ------------------------------
f22 = mini()


def bad(man):
    ls = man.decode().split("\n")
    out = [ls[0]] + [f"{x.split(chr(9))[0]}\t1\t{x.split(chr(9))[2]}" for x in ls[1:-1]]
    out.append("0" * 64 + "\t999999999\tnotes/never-supplied.txt")
    out.sort(key=lambda s: s.split("\t")[2].encode() if "\t" in s else b"")
    return ("\n".join(out) + "\n").encode()


m22 = dataset("22", f22, edit=bad)
program("22-manifest-unchecked-fields.rl",
        f"dataset d = sha256:{m22}\nlet b = bids(d)\n"
        "claim count(participants(b))\n"
        "claim volumes(recording(b, \"01\", \"x\"))\n")

# ---- 23: NIfTI-2 RepetitionTime checked as float32 ----------------------------------------------
f23 = mini(task_json='{"TaskName": "x", "RepetitionTime": 0.8}')
f23["sub-01/func/sub-01_task-x_bold.nii"] = nifti2((2, 2, 2, 5), 0.8)
m23 = dataset("23", f23)
program("23-nifti2-tr-float32.rl", f"dataset d = sha256:{m23}\nclaim tr(recording(bids(d), \"01\", \"x\"))\n")

# ---- 24: lookalike scope is the literal, not the key column -------------------------------------
t24 = "id\tgroup\tage\nA1\tx\t30\nAl\ty\t41\nB\tx\t29\n"
put("24-keys.tsv", t24)
program("24-lookalike-scope.rl",
        f"file f = sha256:{sha(t24.encode())}\nlet t = tsv(f)\n"
        "claim cell(t, key(1, \"B\"), 3)\n"
        "claim count(where(t, ne(1, \"B\")))\n"
        "claim cell(t, key(1, \"A1\"), 3)\n")

# ---- 25: a file that changes after it was hashed (bytes() and size() do not re-hash) -----------
before25 = "id\nAAAA\n"
put("25-before.tsv", before25)
program("25-file-changes-during-check.rl",
        f"file f = sha256:{sha(before25.encode())}\n"
        "claim bytes(f, 3, 4)\n"
        "claim size(f)\n"
        "claim cell(tsv(f), 1, 1)\n")

# ---- 28: smaller documentation mismatches ------------------------------------------------------
program("28-docs-mismatches.rl", "file f = sha256:" + "0" * 64 + "\ndataset d = sha256:" + "1" * 64 + "\n")

# ---- 19: a program inside the Lean model's fragment whose output differs from the model's ------
program("19-lean-model-distance.rl",
        f"file f = sha256:{sha(t08.encode())}\n"
        "let t = tsv(f)\n"
        "let t = tsv(undeclared)\n"
        "claim rows(t)\n")
program("28-docs-mismatches-b.rl", f"file f = sha256:{sha(t08.encode())}\nlet tbl = tsv(f)\nclaim rows(tbl) tbl\n")

# ---- 26: P007 does not check the denominator's sign ---------------------------------------------
put("26-table.tsv", t08)
program("26-negative-denominator.rl",
        f"file f = sha256:{sha(t08.encode())}\n"
        "claim share(where(tsv(f), eq(2, \"A\"))) is -2/-3\n"
        "claim share(where(tsv(f), eq(2, \"A\"))) is 2/-3\n")

# ---- 27: ExtraCell missing from the sort of max/min/sum over participants ------------------------
f27 = {"dataset_description.json": DESC, "participants.tsv": "participant_id\tgroup\tage\nsub-01\ta\t30\nsub-02\tb\t41\n"}
m27 = dataset("27", f27)
program("27-extracell-label-missing.rl",
        f"dataset d = sha256:{m27}\nlet p = participants(bids(d))\n"
        "claim count(where(p, eq(\"age\", \"30\")))\n"
        "claim max(p, \"age\")\n"
        "claim sum(where(p, eq(\"group\", \"b\")), 3)\n")

print("built")
