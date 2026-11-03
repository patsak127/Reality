"""Adoption and withdrawal signatures (req/SPEC.md 5.2). Trusted, with OpenSSH's ssh-keygen.

The keys come from the allowed_signers file given on the command line, never from the ledger.
A call returns True, or the reason the signature is not accepted.
"""
import pathlib
import subprocess

NAMESPACE = "reality-adopt"


class Verifier:
    def __init__(self, allowed_signers):
        self.allowed = str(pathlib.Path(allowed_signers).resolve())

    def __call__(self, payload: bytes, who: str, sig: pathlib.Path):
        if not sig.is_file():
            return f"no signature file {sig.name!r} next to the ledger"
        try:
            r = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", self.allowed, "-I", who, "-n", NAMESPACE, "-s", str(sig)],
                               input=payload, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"a signature that could not be checked (ssh-keygen did not run: {type(e).__name__})"
        return True if r.returncode == 0 else f"a signature that does not match {who}'s key in the allowed_signers file"
