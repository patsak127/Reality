#!/bin/sh
# Finding 17: `reality3 manifest DIR` (the documented way to name a dataset) crashes on file
# names that are not UTF-8, crashes on any non-ASCII name when the filesystem encoding is ASCII
# (LC_ALL=C PYTHONUTF8=0, an envmatrix setting), and writes manifests that the checker then
# refuses (a TAB or a line break in a file name). Run from the review folder.
set -u
D=/tmp/reality-review-17; rm -rf "$D"; mkdir -p "$D/a" "$D/b" "$D/c"
printf 'x' > "$D/a/ok.txt"; printf 'y' > "$(printf "$D/a/n\377m.txt")"
printf 'x' > "$(printf "$D/b/caf\303\251.txt")"
printf 'x' > "$D/c/ok.txt"; printf 'z' > "$(printf "$D/c/tab\tname.txt")"
echo '== 1. a file name that is not UTF-8 (byte 0xFF)'
PYTHONPATH=src .venv/bin/python -m reality3 manifest "$D/a" > /dev/null 2> "$D/err1"; echo "exit $?"; tail -1 "$D/err1"
echo '== 2. a UTF-8 file name, LC_ALL=C PYTHONUTF8=0'
env -i PATH=/usr/bin:/bin LC_ALL=C PYTHONUTF8=0 PYTHONPATH=src .venv/bin/python -m reality3 manifest "$D/b" > /dev/null 2> "$D/err2"; echo "exit $?"; tail -1 "$D/err2"
echo '== 3. a TAB in a file name: the manifest is written, then refused by the checker'
PYTHONPATH=src .venv/bin/python -m reality3 manifest "$D/c" --out "$D/c.manifest"
# findings/17-manifest-writer.rl names that manifest by its hash (the manifest's bytes do not
# depend on where D is, so the hash is fixed: d9743f82...).
PYTHONPATH=src .venv/bin/python -m reality3 check findings/17-manifest-writer.rl --files "$D/c.manifest" "$D/c"; echo "exit $?"
