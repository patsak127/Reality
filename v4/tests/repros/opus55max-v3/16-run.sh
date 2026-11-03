#!/bin/sh
# Finding 16: an unreadable file that no program names, inside a folder given to --files,
# ends the checker with a Python traceback; reached through --root it becomes X001.
# Run from the review folder: sh findings/16-run.sh   (works in /tmp/reality-review-16)
set -u
D=/tmp/reality-review-16
rm -rf "$D"; mkdir -p "$D/files" "$D/ds"
cp findings/01-small.tsv "$D/files/ok.tsv"
printf 'not used by any program\n' > "$D/files/locked.tsv"; chmod 000 "$D/files/locked.tsv"
echo '$ .venv/bin/python -m reality3 check findings/16-unreadable-file-crash.rl --files /tmp/reality-review-16/files'
PYTHONPATH=src .venv/bin/python -m reality3 check findings/16-unreadable-file-crash.rl --files "$D/files" 2>&1 | tail -4
echo "exit status of the checker: $(PYTHONPATH=src .venv/bin/python -m reality3 check findings/16-unreadable-file-crash.rl --files "$D/files" >/dev/null 2>&1; echo $?)"
# --root: the manifest lists ok.tsv; the file at the hinted path is unreadable
cp findings/01-small.tsv "$D/ds/ok.tsv"
PYTHONPATH=src .venv/bin/python -m reality3 manifest "$D/ds" --out "$D/manifest.txt" >/dev/null
chmod 000 "$D/ds/ok.tsv"
printf 'dataset d = sha256:%s\nclaim bids(d)\n' "$(sha256sum "$D/manifest.txt" | cut -d' ' -f1)" > "$D/root.rl"
echo '$ .venv/bin/python -m reality3 check /tmp/reality-review-16/root.rl --files /tmp/reality-review-16/manifest.txt --root /tmp/reality-review-16/ds'
PYTHONPATH=src .venv/bin/python -m reality3 check "$D/root.rl" --files "$D/manifest.txt" --root "$D/ds"; echo "exit $?"
chmod 600 "$D/files/locked.tsv" "$D/ds/ok.tsv"
