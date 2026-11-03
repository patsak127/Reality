"""Not in the default suite (tests/): it is Linux-only, so on the Mac and the PC it would be
skipped and the four machines would differ in outcome. Run it with
`pytest tests_env` on Linux, or `xrun.py run --tests tests_env --hosts box,deck`.

Clause 4 across interpreter settings: tools/envmatrix.py must find zero differences (memory
limits, PYTHONIOENCODING, int digit limits, recursion limits, hash seeds). Linux only: it
sets RLIMIT_AS, which macOS and Windows do not support."""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="RLIMIT_AS is Linux-only")
def test_zero_differences():
    r = subprocess.run([sys.executable, os.path.join(HERE, "..", "tools", "envmatrix.py")], capture_output=True, timeout=1800)
    # nothing printed: the corpus lives in a temporary directory whose name is in the output
    assert r.returncode == 0 and b"0 difference(s)" in r.stdout
