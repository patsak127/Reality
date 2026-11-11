# Authoring controls (Menthol-pattern slice)

Personal **EDIT ME** controls for a Reality project criterion — not an addon dashboard.
Named intention handles rewrite real artifacts; the real checker supplies the preview.
Foreground result is a plain parsed exploratory trial (**UNSIGNED — NOT adopted**); full
`reality_req` log stays collapsed. First-slice only.

## Run in-repo

Prerequisite: **Python >= 3.13**.

```sh
python3 req/demo/authoring_controls/serve.py --host 127.0.0.1 --port 8765
# or: HOST=127.0.0.1 PORT=8765 bash req/demo/authoring_controls/run.sh
```

Optional bind: `--host 0.0.0.0` (still local process; no public infra). Never signs.

## Standalone pack (no REALITY_ROOT, no .git)

```sh
python3 req/demo/authoring_controls/pack_standalone.py \
  --out /path/to/authoring-controls/standalone
# unzip the zip; bash start.sh | start.command | start.bat
```

The pack bundles `vendor/req/src` + `vendor/v4/src`. Verified extract-and-run evidence is
written next to the archive as `VERIFY.json`.

## Tests

```sh
cd req && python3 -m pytest -q tests/test_authoring_controls.py
```
