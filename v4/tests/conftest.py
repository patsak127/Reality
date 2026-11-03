import os

import pytest

import bidsfix
import helpers


@pytest.fixture(scope="session")
def box(tmp_path_factory):
    """(manifest dir, root, manifest sha256) for the box copy of ds001734."""
    d = tmp_path_factory.mktemp("box-manifest")
    root = bidsfix.box_copy()
    h = helpers.manifest(root, str(d))
    return str(d), root, h


@pytest.fixture(scope="session")
def complete(tmp_path_factory):
    """The FABRICATED complete copy (see bidsfix.py): box copy plus tiny made-up images."""
    base = tmp_path_factory.mktemp("complete")
    root = bidsfix.complete_copy(os.path.join(str(base), "ds"))
    md = os.path.join(str(base), "m")
    os.makedirs(md)
    h = helpers.manifest(root, md)
    return md, root, h
