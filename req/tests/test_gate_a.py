"""Gate A: the frozen spec's demo inputs, with Patsak's tolerance of ±4 (answer 1, 3 Nov 2026)."""
import hashlib
from reality4 import readers
from reality4.kernel import check
from conftest import DEMO

DATA = {
    "out_nearest.tsv": "0d6d1bd1d59b7956cfe276a9f6d9f07599fae16a4e9216323ca1e9bd0074869c",
    "out_bilinear.tsv": "979cb9d62803637d56d0e6a492e10b6d174a0e560286e57e2fa17c2f96719ba9",
    "out_stylised.tsv": "0ba99fa7585ae1ba50f888be39530234fd79aaf7d1bd8e28232bbb5d44facc39",
    "drops_published.tsv": "ae92af6e52eaa3e80a1334033abe77cd9d0e90f751db92e9426ef5cdacdfc5b3",
    "drops_shaded.tsv": "1f93834f9787b6f81596ec60091fa814e77ae3276e2f4249bb3ac80d96597136",
}
FRAGMENTS = {
    "M1.fragment": "77874fb1cc9dffe6c00ede3f2f16e6bd8d2a4e17d9c2d038620f234abade5c24",
    "M2.fragment": "04b200687c49249cc26cef8bf5b8c986bca7963697878bdcf912e7880db5e4a2",
    "F1.fragment": "d57a76b2700c9b751f8cdf0917e2c2dc02c54eb023bd8021228c8f667f3dc299",
    "F2.fragment": "458a038a02458c665bece7403f3a1c8725fc1ef871ad6ac4e93398bba967a477",
    "P1.fragment": "d01eec1a6b0f0050ccc43a73c14a6293f35ae9e7f5b770b9aebbd8e631f8afbf",
    "P1b.fragment": "918edb7c286f81725b255a3dbe16c10f91cd496c7a789adc402ba8cd9818b508",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_producers_reproduce_pinned_data(demo_data):
    for name, h in DATA.items():
        assert sha(demo_data / name) == h, name


def test_fragments_pinned_and_m1_is_plus_minus_4():
    for name, h in FRAGMENTS.items():
        assert sha(DEMO / name) == h, name
    m1 = (DEMO / "M1.fragment").read_text()
    assert m1.count("c = 4)") == 12 and m1.count("c = -4)") == 12 and "c = 2)" not in m1


def run(fragment, data):
    h = sha(data)
    prog = f"file d = sha256:{h}\nlet t = tsv(d)\n".encode() + (DEMO / fragment).read_bytes()
    return check(prog, readers.Store([str(data)], []))


def test_stylised_still_fails_m1_at_4_on_red_and_blue(demo_data):
    ok, lines = run("M1.fragment", demo_data / "out_stylised.tsv")
    v001 = [l for l in lines if "[V001, item 5]" in l]
    assert ok is False and len(v001) == 8
    assert sum(l.endswith(" holds") for l in lines) == 16
    assert "at most 4; computed from the bytes it is 4.3888916015625" in v001[0]
    assert "at least -4; computed from the bytes it is -7.134326171875" in v001[1]
    assert [l.split("it is ")[1] for l in v001] == [
        "4.3888916015625", "-7.134326171875", "4.3958740234375", "-7.1330810546875",
        "4.400732421875", "-7.1302978515625", "4.403466796875", "-7.12861328125"]


def test_bilinear_holds_m1_and_shaded_table_fails_f1(demo_data):
    ok, lines = run("M1.fragment", demo_data / "out_bilinear.tsv")
    assert ok is True and sum(l.endswith(" holds") for l in lines) == 24
    ok, lines = run("F1.fragment", demo_data / "drops_shaded.tsv")
    assert ok is False and [l.split("it is ")[1] for l in lines if "V001" in l] == ["0.054", "0.006"]


def test_playtest_1_is_37_of_50_and_playtest_2_is_42_of_50(demo_data):
    ok, lines = run("P1.fragment", demo_data / "playtest_1.tsv")
    assert ok is False and [l.split("it is ")[1] for l in lines if "V001" in l] == ["0.74"]
    assert any("= 37/50 (Exact)" in l for l in lines)
    ok, lines = run("P1.fragment", demo_data / "playtest_2.tsv")
    assert ok is True and any("= 42/50 (Exact)" in l for l in lines)
    ok, lines = run("P1b.fragment", demo_data / "playtest_1.tsv")
    assert ok is True
