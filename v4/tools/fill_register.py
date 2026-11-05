"""Fill the class, codes, decision and note columns of bids/REGISTER-1.0.1.tsv from the table
below (v4 SPEC 8.1). Later rows override earlier ones. Usage: fill_register.py [--check]
(--check: exit 1 if the register differs from what the table gives).

Codes: refusal codes the reader raises for the sentence, or `read` for a reading rule the
reader applies when it forms (a forming test pins it). Decisions name a choice point of SPEC
8.3 (`choice_point` in bids101.py cites the same ids)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "..", "bids", "REGISTER-1.0.1.tsv")

U_VAL = "whether the value is true of the scanner, the dataset or the people is not in the bytes"
NB = "call 2: an encouragement or recommendation is not a 'should', so it does not bind"
B14N = "a file kind v4 does not implement: a dataset with it refuses B14"
EX = "example or heading"

TABLE = [
    ("S0001-S0633", "notfiles", "", "", EX),
    ("S0001-S0057", "notfiles", "", "", "title, changelog or table of contents"),
    ("S0058-S0104", "notfiles", "", "", "motivation and definitions"),
    ("S0097", "unshowable", "", "", "whether a task was one acquisition is a fact of the experiment"),
    ("S0101", "checked", "B06", "", "onset and duration are the first two columns"),
    ("S0105-S0110", "notfiles", "", "", "about the standard"),
    ("S0111-S0114", "reality-call", "B17", "", "call 3: a file in a defined datatype folder that matches no template refuses B17; elsewhere an extra file is allowed"),
    ("S0115-S0131", "unshowable", "", "", "about how data were processed or kept"),
    ("S0123-S0124", "reality-call", "read", "", "code/, derivatives/, sourcedata/, stimuli/ are read as extra; their contents are not checked as raw BIDS data"),
    ("S0126", "reality-call", "B01", "", "Reality's own call (BB's call on Patsak's behalf 2026-10-26, reversible; replaces Patsak 22:29): the bytes are the floor. A README is required at derivatives/ or sourcedata/ whenever the manifest holds a file under that folder (B01); a folder with no file has no manifest entry, so the rule binds nothing there"),
    ("S0132", "checked", "B14 B03", "", "a metadata name at the root or in a subject folder is never extra: JSON is read (B03), TSV/bval/bvec not implemented (B14)"),
    ("S0133", "silent", "B30", "same-folder-values", "deeper folder wins (read); two files in one folder with different values: B30"),
    ("S0134-S0135", "checked", "B14", "", "tasks.tsv: an inherited TSV, " + B14N),
    ("S0136-S0137", "checked", "read", "", "inheritance never unsets a key"),
    ("S0138-S0139", "notfiles", "", "", "extensions"),
    ("S0140", "checked", "B05", "", "NIfTI-1 or NIfTI-2, whole header and data"),
    ("S0141-S0142", "unshowable", "", "", "about the conversion tool"),
    ("S0143-S0144", "notfiles", "", "", "tools"),
    ("S0145-S0148", "checked", "B04", "", "tab-separated with a header line; the required columns are checked by B06, B11, B22"),
    ("S0145", "reality-call", "B04", "", "tab-separated with a header line (B04). Line ends are Reality's own call (DESIGN 5.1; BB's call on Patsak's behalf 2026-10-26, reversible): CR LF ends a line like LF, in BIDS TSVs as in plain ones; mixed line ends refuse (T010; B04 in a BIDS TSV), a lone CR too (T002). 'aka csv files' is not read as fixing it"),
    ("S0149", "reality-call", "B04", "", "a double quote has two readings (quote-aware and plain readers): refused (T005 under B04)"),
    ("S0150", "checked", "B04", "", "an empty cell refuses (call 2)"),
    ("S0152-S0154", "checked", "B19", "", "dictionary keys name columns of the TSV it describes"),
    ("S0155-S0159", "unshowable", "", "", "what a description says about a column"),
    ("S0157", "checked", "B19", "", "the form only: Levels is a dictionary of values to string descriptions (v4-fixes 10); what they say is not in the bytes"),
    ("S0161", "checked", "B04", "", "two successive tabs are an empty cell: B04"),
    ("S0162", "checked", "B03", "", "JSON object"),
    ("S0163-S0165", "notfiles", "", "", "tools"),
    ("S0166", "checked", "B03", "", "JSON is read as strict UTF-8"),
    ("S0168", "checked", "B17 B11", "", "labels are [a-zA-Z0-9]+"),
    ("S0169", "reality-call", "", "", NB),
    ("S0170", "checked", "B11 B17", "", "sub- prefix in names and participant_id"),
    ("S0171-S0174", "unshowable", "", "", "the unit of a number is not in its bytes; RepetitionTime is cross-checked with pixdim[4] (B09)"),
    ("S0175-S0185", "unshowable", "", "", "dates and ages: about the world; scans.tsv acq_time is B14"),
    ("S0187", "checked", "B17 B14", "", "sub-<label>/<data_type>/; sessions B14"),
    ("S0188-S0191", "checked", "read", "", "optional folders, read as extra"),
    ("S0204-S0206", "checked", "B17", "", "extra files in a datatype folder: call 3, B17"),
    ("S0215", "checked", "B01", "", "dataset_description.json required"),
    ("S0217-S0219", "checked", "B01 B02", "", "Name and BIDSVersion strings; version 1.0.1 only"),
    ("S0220-S0230", "unshowable", "", "", U_VAL),
    ("S0222-S0223", "reality-call", "", "", NB),
    ("S0224", "checked", "B01", "", "the form only: Authors is a list of strings (v4-fixes 10); whether they are the authors is not in the bytes"),
    ("S0229", "checked", "B01", "", "the form only: ReferencesAndLinks is a list of strings (v4-fixes 10)"),
    ("S0233", "checked", "B01", "", "call 2: a missing root README refuses"),
    ("S0234", "checked", "read", "", "CHANGES optional"),
    ("S0235", "checked", "B31 B30", "", "CPAN::Changes::Spec 0.04 + CPAN::Meta::Spec Version Formats, pinned with sha256 (v4 SPEC 8.5; sources not in this repository); BIDS's well-formed example 1.0.1 wins on the leading v and zero components; a point with two readings refuses B30 (BB's call on Patsak's behalf 2026-10-26, reversible; replaces Patsak 22:29)"),
    ("S0236", "checked", "B18", "", ""),
    ("S0241", "checked", "read", "", "code/ read as extra"),
    ("S0242-S0243", "unshowable", "", "", "about the scripts"),
    ("S0244", "checked", "B17 B14", "", "anat template; sessions B14"),
    ("S0245", "unshowable", "", "", "about where source files are kept"),
    ("S0247-S0264", "checked", "read", "", "open list ('not limited to'): any suffix of key form is an anatomical image"),
    ("S0265-S0266", "silent", "B30", "run-index", "run-1 vs run-01, or a run omitted next to indexed runs: computed both ways, B30 when results differ"),
    ("S0269-S0275", "checked", "read", "", "acq, rec, sidecar JSON; entity order B17"),
    ("S0276-S0277", "checked", "B17 B14", "", "func template; sessions B14"),
    ("S0280", "unshowable", "B07", "", "whether a scan is task-based is a fact of the experiment; an events file needs its BOLD (B07)"),
    ("S0281", "checked", "read", "", "sbref"),
    ("S0282", "checked", "B08 B17", "", ""),
    ("S0283", "unshowable", "", "", "whether two labels name one task is about the experiment; B08 checks label = TaskName"),
    ("S0284-S0285", "silent", "B30", "run-index", "as S0265"),
    ("S0287-S0290", "checked", "read", "", "acq, rec"),
    ("S0291", "checked", "B08", "", ""),
    ("S0293", "checked", "B08 B21", "", "positive number"),
    ("S0294", "unshowable", "", "", "sparse acquisition is about the scan"),
    ("S0295", "checked", "B09", "", "pixdim[4] in xyzt_units, the float nearest to RepetitionTime"),
    ("S0296-S0298", "checked", "B08", "", ""),
    ("S0300", "reality-call", "", "", NB),
    ("S0301-S0346", "unshowable", "", "", U_VAL),
    ("S0308", "checked", "B21", "", "a number"),
    ("S0334", "checked", "B21", "", "a number"),
    ("S0336", "checked", "B21", "", "a number"),
    ("S0343", "checked", "B21", "", "a number"),
    ("S0347", "checked", "B10", "", "one of i j k i- j- k-"),
    ("S0348-S0351", "unshowable", "", "", "what the axis means for the scan"),
    ("S0352", "checked", "B10", "", "required with a fieldmap; the different-directions half cannot be shown when no direction is written"),
    ("S0353", "checked", "B21", "", "a number"),
    ("S0354", "notfiles", "", "", "a link"),
    ("S0355", "checked", "B10", "", ""),
    ("S0356", "checked", "B21", "", "a number"),
    ("S0357", "checked", "B14", "", "case 4 fieldmaps: " + B14N),
    ("S0359-S0360", "checked", "B21", "", "a number or a list of numbers"),
    ("S0361", "checked", "B10", "", ""),
    ("S0362", "unshowable", "", "", U_VAL),
    ("S0363", "checked", "B21", "", "a number"),
    ("S0364-S0365", "unshowable", "", "", U_VAL),
    ("S0366-S0369", "checked", "B10", "", "list of numbers, one per slice, in [0, TR)"),
    ("S0369", "silent", "B30", "slice-axis", "no default slice axis: without SliceEncodingDirection or slice_dim, a length fitting one spatial axis reads that axis; fitting several: B30; fitting none: B10"),
    ("S0370", "unshowable", "", "", "whether a sequence is sparse is about the scan"),
    ("S0371", "notfiles", "", "", "about analysis"),
    ("S0372", "checked", "B10", "", ""),
    ("S0373", "unshowable", "", "", "what the axis means for the scan"),
    ("S0374", "checked", "B10", "", "consistent with slice_dim"),
    ("S0375", "checked", "B21", "", "a number"),
    ("S0378", "unshowable", "", "", "what time 0 was in the scanner"),
    ("S0379", "checked", "B21", "", "a number"),
    ("S0380", "reality-call", "", "", NB),
    ("S0381", "unshowable", "", "", "what time 0 was in the scanner"),
    ("S0384", "checked", "B21", "", "a number"),
    ("S0385", "unshowable", "", "", U_VAL),
    ("S0387", "checked", "B21", "", "a number"),
    ("S0389-S0398", "unshowable", "", "", U_VAL),
    ("S0399", "reality-call", "", "", NB),
    ("S0401-S0403", "checked", "read", "", "root sidecar inherited; the subject's own file takes precedence (deeper wins)"),
    ("S0404-S0406", "checked", "B17 B07", "", "events template, matches its BOLD file"),
    ("S0409", "checked", "B07", "", ""),
    ("S0410", "checked", "B06", "", ""),
    ("S0411", "unshowable", "", "", "seconds or milliseconds is not in the bytes"),
    ("S0412", "reality-call", "B30", "", "Reality's own rule (DESIGN 5 call 3; BB's call on Patsak's behalf 2026-10-26, reversible): an onset at or after volumes x TR refuses B30. 1.0.1 does not say an event must fall inside its run; this is not a 1.0.1 ambiguity"),
    ("S0413-S0414", "unshowable", "", "", "which scans were discarded"),
    ("S0415", "checked", "B06", "", "onset a number (negative allowed), duration > 0"),
    ("S0416", "checked", "B06", "", "a number or n/a"),
    ("S0417-S0420", "checked", "B20", "", "stim_file names a file under stimuli/"),
    ("S0421-S0424", "checked", "read", "", "trial_type and extra columns"),
    ("S0426-S0427", "checked", "read", "", "extra columns"),
    ("S0429", "unshowable", "", "", "what happened before the scan"),
    ("S0430-S0456", "checked", "B14", "", "physiological and continuous recordings, behavioural data: " + B14N),
    ("S0457-S0458", "checked", "B14", "", "beh/: " + B14N),
    ("S0459-S0492", "checked", "B14", "", "diffusion data: " + B14N),
    ("S0474", "checked", "B14", "", "bval/bvec at any level: " + B14N),
    ("S0493-S0494", "notfiles", "", "", "introduction"),
    ("S0495", "silent", "B30", "intendedfor-source", "IntendedFor from the phasediff JSON or from any image JSON: B30 when the results differ"),
    ("S0497", "checked", "B12", "", "a path or list of paths to a scan of the subject"),
    ("S0499", "silent", "B10", "fieldmap-without-intendedfor", "no IntendedFor: v4 takes the fieldmap as corresponding to every scan of its subject (B10 fields required); the other reading (none) conforms only when they are missing, so the result is a refusal either way"),
    ("S0500-S0501", "silent", "B30", "run-index", "as S0265"),
    ("S0502", "checked", "read", "", "acq"),
    ("S0503-S0506", "checked", "B12", "", "case 1: phasediff and magnitude1, magnitude2 optional"),
    ("S0507", "notfiles", "", "", "about scanners"),
    ("S0508", "checked", "B12", "", "EchoTime1 and EchoTime2 numbers"),
    ("S0510", "notfiles", "", "", "example; cited by intendedfor-source"),
    ("S0511-S0538", "checked", "B14", "", "fieldmap cases 2-4: " + B14N),
    ("S0539-S0552", "checked", "B14", "", "scans files: " + B14N),
    ("S0553", "checked", "B11 B22 B19", "", "participants and phenotype files"),
    ("S0554", "checked", "read", "", "participants.tsv optional"),
    ("S0555", "unshowable", "", "", U_VAL),
    ("S0556", "checked", "B11", "", "exactly one participant_id column of sub-<label>, and it is the first (\"followed by\"; BB's call 12 on Patsak's behalf, 26 Oct 2026)"),
    ("S0557", "checked", "B11", "", "one row per participant; rows without a subject folder also refuse B11 (Reality's call 1, not a 1.0.1 sentence)"),
    ("S0559-S0561", "checked", "B22 B17", "", "phenotype/<name>.tsv with participant_id of the dataset's participants"),
    ("S0562-S0564", "checked", "B19", "", "dictionary keys name columns, or MeasurementToolMetadata, which has only the string keys Description and TermURL (v4-fixes 10)"),
    ("S0568", "checked", "B30", "", "a column description key other than LongName, Description, Levels, Units, TermURL (and Derivative in participants and phenotype files) fixes no reading: B30 (BB's call 12 on Patsak's behalf, 26 Oct 2026)"),
    ("S0569", "checked", "B19", "", "the form only: Derivative is true or false (v4-fixes 10); what it says is not in the bytes"),
    ("S0570-S0576", "checked", "B14", "", "sessions: " + B14N),
    ("S0610-S0616", "checked", "B14", "", "sessions files: " + B14N),
    ("S0617-S0627", "notfiles", "", "", "advice on multi-site studies"),
    ("S0628", "checked", "B17", "", "labels are [a-zA-Z0-9]+"),
    # BB's call on Patsak's behalf 2026-10-26, reversible (taste call 4): an example binds as BIDS's own reading only if it is
    # well-formed in its own kind's grammar; an example with no reading at all is an erratum and binds nothing (DESIGN §9 call 4).
    ("S0231-S0232", "notfiles", "", "", "erratum (PDF p.11): the dataset_description.json example has no comma after \"Authors\", so it is not JSON and binds nothing; JSON stays strict (B03)"),
    ("S0400", "notfiles", "", "", "erratum (PDF p.17): the bold JSON example writes \"InstitutionAddress: \"450 ... and no comma before DeviceSerialNumber, so it is not JSON and binds nothing; JSON stays strict (B03)"),
    ("S0565", "notfiles", "", "", "erratum (PDF p.28): the phenotype JSON example ends with a trailing comma, so it is not JSON and binds nothing; JSON stays strict (B03)"),
    ("S0237-S0240", "notfiles", "", "", "example (PDF p.11): well-formed, so BIDS's own reading of CHANGES: versions like 1.0.1 (no leading v, zero components) conform (S0235)"),
    ("S0545", "checked", "B14", "", "scans files: " + B14N + ". When implemented: the example 2009-06-15T13:45:30 is well-formed ISO 8601 local time, so an offset-less date-time conforms although RFC 3339 requires an offset (precedence, DESIGN §9 call 4)"),
]


def ids(spec):
    a, _, b = spec.partition("-")
    return range(int(a[1:]), int((b or a)[1:]) + 1)


def filled():
    lines = open(REG, encoding="utf-8").read().split("\n")
    head = lines[0].split("\t")
    rows = [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln]
    by = {int(r["id"][1:]): r for r in rows}
    for spec, cls, codes, dec, note in TABLE:
        for n in ids(spec):
            by[n].update({"class": cls, "codes": codes, "decision": dec, "note": note})
    return head, rows


def render(head, rows):
    return "\t".join(head) + "\n" + "".join("\t".join(r[k] for k in head) + "\n" for r in rows)


if __name__ == "__main__":
    head, rows = filled()
    out = render(head, rows)
    if "--check" in sys.argv:
        sys.exit(0 if open(REG, encoding="utf-8").read() == out else 1)
    with open(REG, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print(len(rows), "rows")
