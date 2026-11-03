"""Finding 03: writes 03-ds/ (a small conformant BIDS 1.0.1 dataset plus one extra file whose
name is not ASCII), 03-manifest.txt and 03-locale-root.rl. Deterministic: same hashes everywhere."""
import _lib as L
files = L.base_files()
files["notes-été.txt"] = "An extra file (not BIDS). Its name is not ASCII.\n"
mh = L.build("03", files)
L.program("03", "locale-root", 'dataset d = sha256:%s\nlet b = bids(d)\nclaim tr(recording(b, "01", "x"))\n' % mh)
print("manifest", mh)
