"""Finding 06: a case-1 fieldmap whose phasediff sidecar (the JSON 1.0.1 section 8.9.1 defines)
has no IntendedFor, so by v3's own reading (RULES-1.0.1.md, B10) it may correspond to any scan
of sub-01 and the BOLD needs EchoTime, EffectiveEchoSpacing and PhaseEncodingDirection.
06-ds adds sub-01_magnitude1.json (no 1.0.1 template) whose IntendedFor names only the T1w.
06b-ds is the same dataset without that file."""
import _lib as L
def files(with_mag_json):
    f = L.base_files()                      # the BOLD's metadata has no EchoTime, EffectiveEchoSpacing, PED
    f["sub-01/anat/sub-01_T1w.nii"] = L.nifti1((2, 2, 2))
    f["sub-01/fmap/sub-01_phasediff.nii"] = L.nifti1((2, 2, 2))
    f["sub-01/fmap/sub-01_magnitude1.nii"] = L.nifti1((2, 2, 2))
    f["sub-01/fmap/sub-01_phasediff.json"] = '{"EchoTime1": 0.00492, "EchoTime2": 0.00738}'
    if with_mag_json:
        f["sub-01/fmap/sub-01_magnitude1.json"] = '{"IntendedFor": "anat/sub-01_T1w.nii"}'
    return f
for nn, flag, name in (("06", True, "magnitude-intendedfor"), ("06b", False, "control-no-magnitude-json")):
    m = L.build(nn, files(flag))
    L.program(nn, name, 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x"))\n' % m)
