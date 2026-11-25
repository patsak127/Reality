"""Tests for steps one to four. Every table here is made up for the test; none is a measurement of anything.

The only keys used are throwaway keys generated per run by ssh-keygen and labeled
REALITY-TEST-KEY-NOT-PATSAK. Signing happens here, in test code, never in reality.py.
Ledger lines "written around the program" are written here with reality.record.
This file is not part of the trusted surface.
"""

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import reality
from reality import NotPresented, Refusal, Unreadable, WrongFiles

LABEL = "REALITY-TEST-KEY-NOT-PATSAK"
TABLE = b"id\tcolour\n1\tred\n2\tred\n3\tred\n4\tblue\n5\tgreen\n"  # made up: 3 of 5 rows have colour red
NO_COLOUR = b"id\tsize\n1\tbig\n2\tsmall\n"  # made up: a table in the format, with no column named colour
NON_QUESTIONS = {  # name: (made-up bytes, predicate, the F8 file token)
    "ragged row": (b"a\tb\n1\n", "column-equals a 1", "ragged-row"),
    "duplicate column": (b"a\ta\n1\t1\n", "column-equals a 1", "repeated-column"),
    "no final newline": (b"a\n1", "column-equals a 1", "no-final-newline"),
    "empty file": (b"", "column-equals a 1", "no-final-newline"),
    "no rows": (b"colour\n", "column-equals colour red", "no-rows"),
    "no such column": (TABLE, "column-equals size red", "no-such-column"),
    "carriage return is a cell byte": (TABLE.replace(b"\n", b"\r\n"), "column-equals colour red",
                                       "no-such-column"),
}
STATEMENT = re.compile(r"^outcome=[A-Z0-9-]+(?: [a-z0-9-]+=[0-9A-Za-z-]+)*$")
OFFERED = ("same ship", "the row is correct", "must be correct", "colour", "color", "size",
           "why it could pass", "why it is not", LABEL, "DOES NOT HOLD", "NOT CHECKED",
           "the named bytes were not presented")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def measure(n: int, d: int, table: bytes = TABLE, predicate: str = "column-equals colour red") -> bytes:
    return (f"reality 1\nquestion share-at-least\ntable sha256 {sha(table)}\n"
            f"predicate {predicate}\nat-least {n} of {d}\n").encode()


def agrees(first: bytes, second: bytes, predicate: str = "column-equals colour red") -> bytes:
    return (f"reality 1\nquestion share-agrees\ntable sha256 {sha(first)}\ntable sha256 {sha(second)}\n"
            f"predicate {predicate}\n").encode()


def made(matching: int, total: int) -> bytes:
    """A made-up table in which `matching` of `total` rows have colour red."""
    rows = "".join(f"{i}\t{'red' if i <= matching else 'blue'}\n" for i in range(1, total + 1))
    return ("id\tcolour\n" + rows).encode()


def new_key(path: Path) -> Path:
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", LABEL, "-f", str(path)], check=True)
    return path


def sign(key: Path, raw: bytes, namespace: str = reality.NAMESPACE) -> str:
    done = subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", namespace],
                          input=raw, capture_output=True, check=True)
    return done.stdout.decode()


class Steps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.key = new_key(Path(cls.tmp.name, "listed"))
        cls.unlisted = new_key(Path(cls.tmp.name, "unlisted"))

    def setUp(self):
        self.ledger = Path(tempfile.mkdtemp(dir=self.tmp.name))
        kind, blob = Path(f"{self.key}.pub").read_text().split()[:2]
        (self.ledger / "adopters").write_text(f"{LABEL} {kind} {blob}\n")
        self.table = self.ledger / "table.tsv"
        self.table.write_bytes(TABLE)

    def put(self, name: str, data: bytes) -> Path:
        path = self.ledger / name
        path.write_bytes(data)
        return path

    def adopted(self, raw: bytes, *tables: Path) -> bytes:
        tables = tables or (self.table,)
        reality.propose(self.ledger, raw, *tables)
        reality.adopt(self.ledger, raw, LABEL, sign(self.key, raw), *tables)
        return raw

    def logged(self, kind: str) -> list[dict]:
        return [e for e in reality.entries(self.ledger) if e["kind"] == kind]

    def parse(self, statement: str) -> dict[str, str]:
        statement = statement.strip()
        self.assertRegex(statement, STATEMENT, statement)
        for word in OFFERED:
            self.assertNotIn(word, statement)
        return dict(field.split("=", 1) for field in statement.split())

    def refused(self, rule: str, call, *args) -> dict[str, str]:
        with self.assertRaises(Refusal) as caught:
            call(*args)
        slots = self.parse(str(caught.exception))
        self.assertEqual(caught.exception.slots["rule"], rule)
        self.assertEqual(slots["outcome"], "REFUSED")
        self.assertEqual(slots["rule"], rule)
        return slots

    def not_presented(self, call, *args) -> dict[str, str]:
        with self.assertRaises(NotPresented) as caught:
            call(*args)
        self.assertNotIsInstance(caught.exception, Refusal)
        slots = self.parse(str(caught.exception))
        self.assertEqual(slots["outcome"], "NOT-RECORDED")
        return slots

    def cli(self, *argv) -> tuple[int, dict[str, str]]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = reality.main([str(arg) for arg in argv])
        text = out.getvalue()
        self.assertTrue(text.endswith("\n") and text.count("\n") == 1, text)
        slots = self.parse(text)
        self.assertEqual(code, reality.CODES[slots["outcome"]], text)
        return code, slots

    # ---- share-at-least (steps one and two) ----

    def test_holds_when_share_meets_bar(self):
        for n, d in ((3, 5), (1, 2), (6, 10)):
            with self.subTest(bar=(n, d)):
                slots = self.parse(reality.check(self.ledger, self.adopted(measure(n, d)), self.table))
                self.assertEqual(slots["outcome"], "HOLDS")
                self.assertEqual(slots["matching-1"], "3")
                self.assertEqual(slots["rows-1"], "5")
                self.assertNotIn("matching-2", slots)

    def test_does_not_hold_when_share_is_below_bar(self):
        for n, d in ((4, 5), (61, 100), (1, 1)):
            with self.subTest(bar=(n, d)):
                slots = self.parse(reality.check(self.ledger, self.adopted(measure(n, d)), self.table))
                self.assertEqual(slots["outcome"], "DOES-NOT-HOLD")
                self.assertEqual(slots["matching-1"], "3")
                self.assertEqual(slots["rows-1"], "5")

    def test_not_checked_when_named_bytes_are_not_presented(self):
        raw = self.adopted(measure(3, 5))
        mid = reality.ident(raw.decode())
        self.table.write_bytes(TABLE.replace(b"blue", b"red"))
        slots = self.parse(reality.check(self.ledger, raw, self.table))
        self.assertEqual(slots["outcome"], "NOT-CHECKED")
        self.assertEqual(slots["file-1"], "other-bytes")
        self.assertEqual(slots["measure"], mid)
        self.assertNotIn("matching-1", slots)
        slots = self.parse(reality.check(self.ledger, raw, self.ledger / "absent"))
        self.assertEqual(slots["outcome"], "NOT-CHECKED")
        self.assertEqual(slots["file-1"], "unreadable")
        self.assertEqual(self.logged("check"), [])  # NOT CHECKED is reported, not recorded
        self.table.write_bytes(TABLE)
        slots = self.parse(reality.check(self.ledger, raw, self.table))
        self.assertEqual(slots["outcome"], "HOLDS")
        checks = self.logged("check")
        self.assertEqual([self.parse(e["outcome"])["outcome"] for e in checks], ["HOLDS"])
        self.assertEqual(list(checks[0]), ["kind", "outcome"])

    def test_question_that_cannot_be_asked_of_its_named_bytes_is_refused(self):
        for name, (table, predicate, token) in NON_QUESTIONS.items():
            with self.subTest(name):
                self.table.write_bytes(table)
                raw = measure(1, 2, table, predicate)
                reality.form(raw)  # F1 to F4 pass: the measure text alone does not show the failure
                slots = self.refused("F8", reality.propose, self.ledger, raw, self.table)
                self.assertEqual(slots["file-1"], token)
                self.refused("F8", reality.adopt, self.ledger, raw, LABEL, sign(self.key, raw), self.table)
                self.refused("F8", reality.check, self.ledger, raw, self.table)
                self.assertEqual(reality.entries(self.ledger), [])

    def test_refusal_does_not_suggest_another_column(self):
        raw = measure(1, 2, TABLE, "column-equals color red")
        slots = self.refused("F8", reality.propose, self.ledger, raw, self.table)
        self.assertEqual(slots["file-1"], "no-such-column")
        self.assertNotIn("condition", slots)
        self.assertEqual(reality.entries(self.ledger), [])

    def test_handwritten_proposal_and_valid_signature_do_not_adopt_a_non_question(self):
        for name, (table, predicate, token) in NON_QUESTIONS.items():
            with self.subTest(name):
                self.setUp()  # a fresh ledger for each case
                self.table.write_bytes(table)
                raw = measure(1, 2, table, predicate)
                signature = sign(self.key, raw)  # nothing stops a signature being made outside the program
                reality.record(self.ledger, kind="proposal", measure=raw.decode())
                self.assertTrue(reality.signed(self.ledger, LABEL, raw.decode(), signature))
                slots = self.refused("F8", reality.adopt, self.ledger, raw, LABEL, signature, self.table)
                self.assertEqual(slots["file-1"], token)
                self.assertEqual(self.logged("adoption"), [])
                self.assertEqual(len(reality.entries(self.ledger)), 1)  # only the handwritten line

    def test_check_refuses_a_non_question_whatever_the_ledger_says(self):
        for name, (table, predicate, token) in NON_QUESTIONS.items():
            with self.subTest(name):
                self.setUp()  # a fresh ledger for each case
                self.table.write_bytes(table)
                raw = measure(1, 2, table, predicate)
                reality.record(self.ledger, kind="proposal", measure=raw.decode())
                reality.record(self.ledger, kind="adoption", measure=raw.decode(), adopter=LABEL,
                               signature=sign(self.key, raw))
                slots = self.refused("F8", reality.check, self.ledger, raw, self.table)
                self.assertEqual(slots["file-1"], token)
                self.assertEqual(self.logged("check"), [])
                # Without the named bytes the program cannot see the non-question. It says NOT-CHECKED
                # and records nothing.
                slots = self.parse(reality.check(self.ledger, raw, self.ledger / "absent"))
                self.assertEqual(slots["outcome"], "NOT-CHECKED")
                self.assertEqual(slots["file-1"], "unreadable")
                self.table.write_bytes(table + b"other bytes\n")
                slots = self.parse(reality.check(self.ledger, raw, self.table))
                self.assertEqual(slots["outcome"], "NOT-CHECKED")
                self.assertEqual(slots["file-1"], "other-bytes")
                self.assertEqual(self.logged("check"), [])
                self.assertEqual(len(reality.entries(self.ledger)), 2)

    def test_propose_and_adopt_record_nothing_when_named_bytes_are_not_presented(self):
        raw = measure(3, 5)
        other = self.put("other.tsv", TABLE.replace(b"blue", b"red"))
        absent = self.ledger / "absent"
        for given, token in ((other, "other-bytes"), (absent, "unreadable")):
            with self.subTest(operation="propose", given=given.name):
                slots = self.not_presented(reality.propose, self.ledger, raw, given)
                self.assertEqual(slots["file-1"], token)
                self.assertEqual(reality.entries(self.ledger), [])
        reality.propose(self.ledger, raw, self.table)
        signature = sign(self.key, raw)
        for given, token in ((other, "other-bytes"), (absent, "unreadable")):
            with self.subTest(operation="adopt", given=given.name):
                slots = self.not_presented(reality.adopt, self.ledger, raw, LABEL, signature, given)
                self.assertEqual(slots["file-1"], token)
                self.assertEqual(self.logged("adoption"), [])
        # A non-question whose bytes are not presented is not refused under F8: nothing was seen.
        self.not_presented(reality.propose, self.ledger, measure(1, 2, TABLE, "column-equals size red"), absent)
        self.assertEqual(len(reality.entries(self.ledger)), 1)
        # With the named bytes, the same proposal and signature go through.
        slots = self.parse(reality.adopt(self.ledger, raw, LABEL, signature, self.table))
        self.assertEqual(slots["outcome"], "ADOPTED")
        self.assertEqual(self.parse(reality.check(self.ledger, raw, self.table))["outcome"], "HOLDS")

    def test_english_sentence_is_refused(self):
        prose = b"At least 80% of the rows must be correct.\n"
        slots = self.refused("F1", reality.propose, self.ledger, prose, self.table)
        self.assertEqual(slots["condition"], "not-reality-1")
        self.assertEqual(slots["line"], "1")
        self.assertNotIn("measure", slots)
        self.assertNotIn("80%", str(slots))
        slots = self.refused("F3", reality.propose, self.ledger, measure(4, 5, predicate="the row is correct"),
                             self.table)
        self.assertEqual(slots["condition"], "not-a-predicate-line")
        self.assertEqual(reality.entries(self.ledger), [])

    def test_theseus_is_refused(self):
        question = self.put("theseus", b"Is it the same ship after every plank is replaced?\n")
        code, slots = self.cli("check", self.ledger, question, self.table)
        self.assertEqual(code, 3)
        self.assertEqual(slots, {"outcome": "REFUSED", "rule": "F1", "condition": "not-reality-1", "line": "1"})
        self.assertEqual(self.logged("check"), [])

    def test_malformed_forms_are_refused_by_the_named_rule(self):
        good = measure(3, 5)
        digest = sha(TABLE).encode()
        cases = [
            ("F1", "not-five-lines", good + good),
            ("F1", "no-such-question", good.replace(b"share-at-least", b"share-at-most")),
            ("F2", "not-a-table-line", good.replace(digest, digest[:-1])),
            ("F2", "not-a-table-line", good.replace(b"sha256", b"name")),
            ("F3", "not-a-predicate-line", measure(3, 5, predicate="column-contains colour re")),
            ("F3", "not-a-predicate-line", measure(3, 5, predicate="lambda row: True")),
            ("F4", "bar-above-whole", measure(6, 5)),
            ("F4", "not-a-bar-line", measure(0, 5)),
            ("F4", "not-a-bar-line", good.replace(b"3 of 5", b"0.6 of 1")),
            ("F4", "not-a-bar-line", good.replace(b"3 of 5", b"03 of 5")),
        ]
        for rule, condition, raw in cases:
            with self.subTest(raw=raw):
                slots = self.refused(rule, reality.form, raw)
                self.assertEqual(slots["condition"], condition)

    def test_check_without_adoption_is_refused(self):
        raw = measure(3, 5)
        slots = self.refused("F6", reality.check, self.ledger, raw, self.table)
        self.assertEqual(slots["condition"], "no-adoption")
        reality.propose(self.ledger, raw, self.table)
        slots = self.refused("F6", reality.check, self.ledger, raw, self.table)
        self.assertEqual(slots["condition"], "proposal-only")
        self.refused("F6", reality.check, self.ledger, raw, self.ledger / "absent")
        self.assertEqual(self.logged("check"), [])

    def test_only_a_proposed_measure_can_be_adopted(self):
        raw = measure(3, 5)
        slots = self.refused("F5", reality.adopt, self.ledger, raw, LABEL, sign(self.key, raw), self.table)
        self.assertEqual(slots["condition"], "not-proposed")
        self.assertEqual(self.logged("adoption"), [])

    def test_unsigned_or_unlisted_process_cannot_adopt(self):
        raw = measure(3, 5)
        reality.propose(self.ledger, raw, self.table)
        for signature in ("", sign(self.unlisted, raw), sign(self.key, raw, "file")):
            slots = self.refused("F5", reality.adopt, self.ledger, raw, LABEL, signature, self.table)
            self.assertEqual(slots["condition"], "not-verified")
        self.assertEqual(self.logged("adoption"), [])
        # A tool writes an adoption line straight into the ledger file, without a signature.
        reality.record(self.ledger, kind="adoption", measure=raw.decode(), adopter=LABEL, signature="by a tool")
        slots = self.refused("F6", reality.check, self.ledger, raw, self.table)
        self.assertEqual(slots["condition"], "adoption-not-verified")
        self.assertEqual(self.logged("check"), [])

    def test_in_place_change_of_adopted_bar_is_refused(self):
        high, low = measure(4, 5), measure(1, 2)
        signature = sign(self.key, high)
        reality.propose(self.ledger, high, self.table)
        reality.adopt(self.ledger, high, LABEL, signature, self.table)
        reality.propose(self.ledger, low, self.table)
        slots = self.refused("F7", reality.adopt, self.ledger, low, LABEL, signature, self.table)
        self.assertEqual(slots["condition"], "signed-other-measure")
        self.assertEqual(slots["measure"], reality.ident(low.decode()))
        self.assertEqual(slots["signed-measure"], reality.ident(high.decode()))
        self.refused("F6", reality.check, self.ledger, low, self.table)

    def test_adopted_bar_edited_in_the_ledger_file_is_refused(self):
        self.adopted(measure(4, 5))
        log = self.ledger / "log"
        log.write_text(log.read_text().replace("at-least 4 of 5", "at-least 1 of 2"))
        slots = self.refused("F6", reality.check, self.ledger, measure(1, 2), self.table)
        self.assertEqual(slots["condition"], "adoption-not-verified")
        # The edit also removed the record of the 4 of 5 adoption. The program does not prevent that; it refuses.
        slots = self.refused("F6", reality.check, self.ledger, measure(4, 5), self.table)
        self.assertEqual(slots["condition"], "no-adoption")

    def test_lower_bar_adopted_separately_leaves_first_verdict_standing(self):
        high = self.adopted(measure(4, 5))
        self.assertEqual(self.parse(reality.check(self.ledger, high, self.table))["outcome"], "DOES-NOT-HOLD")
        low = self.adopted(measure(1, 2))
        self.assertEqual(self.parse(reality.check(self.ledger, low, self.table))["outcome"], "HOLDS")
        self.assertEqual(self.parse(reality.check(self.ledger, high, self.table))["outcome"], "DOES-NOT-HOLD")
        self.assertEqual([e["measure"] for e in self.logged("adoption")], [high.decode(), low.decode()])
        names = {reality.ident(high.decode()): "high", reality.ident(low.decode()): "low"}
        seen = [(names[self.parse(e["outcome"])["measure"]], self.parse(e["outcome"])["outcome"])
                for e in self.logged("check")]
        self.assertEqual(seen, [("high", "DOES-NOT-HOLD"), ("low", "HOLDS"), ("high", "DOES-NOT-HOLD")])

    def test_command_line_reports_verdicts_and_refusals(self):
        raw = measure(3, 5)
        question = self.put("question", raw)
        mid = reality.ident(raw.decode())
        absent = self.ledger / "absent"
        code, slots = self.cli("propose", self.ledger, question)  # the table file is required
        self.assertEqual(code, 4)
        self.assertEqual(slots, {"outcome": "NOT-RUN", "condition": "usage"})
        code, slots = self.cli("propose", self.ledger, question, absent)
        self.assertEqual(code, 5)
        self.assertEqual(slots["outcome"], "NOT-RECORDED")
        self.assertEqual(slots["file-1"], "unreadable")
        self.assertEqual(slots["measure"], mid)
        self.assertEqual(reality.entries(self.ledger), [])
        code, slots = self.cli("propose", self.ledger, question, self.table)
        self.assertEqual(code, 8)
        self.assertEqual(slots, {"outcome": "PROPOSED", "measure": mid})
        code, slots = self.cli("check", self.ledger, question, self.table)
        self.assertEqual(code, 3)
        self.assertEqual(slots["condition"], "proposal-only")
        sigfile = self.put("question.sig", sign(self.key, raw).encode())
        self.assertEqual(self.cli("adopt", self.ledger, question, sigfile, LABEL)[0], 4)  # table file required
        self.assertEqual(self.cli("adopt", self.ledger, question, sigfile, LABEL, absent)[0], 5)
        self.assertEqual(self.logged("adoption"), [])
        code, slots = self.cli("adopt", self.ledger, question, sigfile, LABEL, self.table)
        self.assertEqual(code, 9)
        self.assertEqual(slots["outcome"], "ADOPTED")
        self.assertEqual(slots["measure"], mid)
        self.assertEqual(slots["adoption-line"], "2")
        code, slots = self.cli("check", self.ledger, question, self.table)
        self.assertEqual(code, 0)
        self.assertEqual(slots["outcome"], "HOLDS")
        self.assertEqual(slots["matching-1"], "3")
        self.assertEqual(slots["rows-1"], "5")
        self.assertEqual(slots["measure"], mid)
        self.assertEqual(slots["adoption-line"], "2")
        code, slots = self.cli("check", self.ledger, question, absent)
        self.assertEqual(code, 2)
        self.assertEqual(slots["outcome"], "NOT-CHECKED")
        self.assertEqual(slots["file-1"], "unreadable")
        self.assertEqual(len(self.logged("check")), 1)
        self.assertEqual(self.cli("amend", self.ledger, question)[0], 4)

    def test_command_line_refuses_a_non_question_and_records_nothing(self):
        raw = measure(1, 2, TABLE, "column-equals size red")
        question = self.put("question", raw)
        sigfile = self.put("question.sig", sign(self.key, raw).encode())
        for argv in (("propose", self.ledger, question, self.table),
                     ("adopt", self.ledger, question, sigfile, LABEL, self.table),
                     ("check", self.ledger, question, self.table)):
            with self.subTest(argv[0]):
                code, slots = self.cli(*argv)
                self.assertEqual(code, 3)
                self.assertEqual(slots["outcome"], "REFUSED")
                self.assertEqual(slots["rule"], "F8")
                self.assertEqual(slots["file-1"], "no-such-column")
                self.assertEqual(reality.entries(self.ledger), [])

    # ---- share-agrees (step three) ----

    def test_agrees_holds_when_shares_are_equal(self):
        for (a, b), (c, d) in (((3, 5), (6, 10)), ((1, 5), (2, 10)), ((5, 5), (2, 2))):
            with self.subTest(first=(a, b), second=(c, d)):
                first, second = self.put("first", made(a, b)), self.put("second", made(c, d))
                raw = self.adopted(agrees(made(a, b), made(c, d)), first, second)
                slots = self.parse(reality.check(self.ledger, raw, first, second))
                self.assertEqual(slots["outcome"], "HOLDS")
                self.assertEqual(slots["matching-1"], str(a))
                self.assertEqual(slots["rows-1"], str(b))
                self.assertEqual(slots["matching-2"], str(c))
                self.assertEqual(slots["rows-2"], str(d))
        self.assertEqual([self.parse(e["outcome"])["outcome"] for e in self.logged("check")], ["HOLDS"] * 3)

    def test_agrees_does_not_hold_when_shares_differ(self):
        first, second = self.put("first", made(3, 5)), self.put("second", made(2, 5))
        raw = self.adopted(agrees(made(3, 5), made(2, 5)), first, second)
        slots = self.parse(reality.check(self.ledger, raw, first, second))
        self.assertEqual(slots["outcome"], "DOES-NOT-HOLD")
        self.assertEqual((slots["matching-1"], slots["rows-1"], slots["matching-2"], slots["rows-2"]),
                         ("3", "5", "2", "5"))
        self.assertEqual([self.parse(e["outcome"])["outcome"] for e in self.logged("check")], ["DOES-NOT-HOLD"])

    def test_a_table_asked_against_itself_is_refused_from_the_text(self):
        # A file always agrees with itself, so the question asks nothing of the bytes: refused under F2 at form
        # time, before any file is read, whatever the files or the predicate.
        nocolour = self.put("nocolour", NO_COLOUR)
        for raw, files in ((agrees(TABLE, TABLE), (self.table, self.table)),
                           (agrees(NO_COLOUR, NO_COLOUR), (nocolour, nocolour)),
                           (agrees(TABLE, TABLE), (self.table,))):
            with self.subTest(files=len(files)):
                with self.assertRaises(Refusal) as caught:
                    reality.form(raw)
                slots = self.parse(str(caught.exception))
                self.assertEqual((slots["rule"], slots["condition"], slots["line"]), ("F2", "same-table", "4"))
                signature = sign(self.key, raw)
                for call, args in ((reality.propose, (self.ledger, raw, *files)),
                                   (reality.adopt, (self.ledger, raw, LABEL, signature, *files)),
                                   (reality.check, (self.ledger, raw, *files))):
                    self.assertEqual(self.refused("F2", call, *args)["condition"], "same-table")
                question = self.put("question", raw)
                code, slots = self.cli("propose", self.ledger, question, *files)
                self.assertEqual((code, slots["condition"]), (3, "same-table"))
        self.assertEqual(reality.entries(self.ledger), [])

    def test_agrees_is_refused_when_the_value_matches_no_row_in_either_file(self):
        first, second = self.put("first", made(0, 5)), self.put("second", made(0, 10))
        english = self.put("english", made(2, 10))
        cases = (("zero in both", agrees(made(0, 5), made(0, 10)), (first, second)),
                 ("an English value", agrees(TABLE, made(2, 10), "column-equals colour Is_it_the_same_ship?"),
                  (self.table, english)))
        for name, raw, files in cases:
            with self.subTest(name):
                reality.form(raw)  # F1 to F4 pass: the text alone does not show it
                signature = sign(self.key, raw)
                for call, args in ((reality.propose, (self.ledger, raw, *files)),
                                   (reality.adopt, (self.ledger, raw, LABEL, signature, *files)),
                                   (reality.check, (self.ledger, raw, *files))):
                    slots = self.refused("F8", call, *args)
                    self.assertEqual((slots["file-1"], slots["file-2"]), ("no-match", "no-match"))
                    self.assertNotIn("matching-1", slots)
                question = self.put("question", raw)
                sigfile = self.put("question.sig", signature.encode())
                for argv in (("propose", self.ledger, question, *files),
                             ("adopt", self.ledger, question, sigfile, LABEL, *files),
                             ("check", self.ledger, question, *files)):
                    code, slots = self.cli(*argv)
                    self.assertEqual((code, slots["rule"], slots["file-1"]), (3, "F8", "no-match"))
        self.assertEqual(reality.entries(self.ledger), [])

    def test_a_handwritten_adoption_does_not_check_an_empty_agreement(self):
        first, second = self.put("first", made(0, 5)), self.put("second", made(0, 10))
        raw = agrees(made(0, 5), made(0, 10))
        reality.record(self.ledger, kind="proposal", measure=raw.decode())
        reality.record(self.ledger, kind="adoption", measure=raw.decode(), adopter=LABEL,
                       signature=sign(self.key, raw))
        self.assertEqual(self.refused("F8", reality.check, self.ledger, raw, first, second)["file-1"], "no-match")
        self.assertEqual(self.logged("check"), [])

    def test_zero_matches_in_one_file_only_is_a_determinate_answer(self):
        for (a, b), (c, d) in (((0, 5), (2, 5)), ((2, 5), (0, 5))):
            with self.subTest(first=(a, b), second=(c, d)):
                first, second = self.put("first", made(a, b)), self.put("second", made(c, d))
                raw = self.adopted(agrees(made(a, b), made(c, d)), first, second)
                slots = self.parse(reality.check(self.ledger, raw, first, second))
                self.assertEqual(slots["outcome"], "DOES-NOT-HOLD")
                self.assertEqual((slots["matching-1"], slots["matching-2"]), (str(a), str(c)))

    def test_share_at_least_with_zero_matches_is_a_determinate_does_not_hold(self):
        raw = self.adopted(measure(1, 3, predicate="column-equals colour Is_it_the_same_ship?"))
        slots = self.parse(reality.check(self.ledger, raw, self.table))
        self.assertEqual((slots["outcome"], slots["matching-1"], slots["rows-1"]), ("DOES-NOT-HOLD", "0", "5"))

    def test_another_file_holding_the_named_bytes_is_those_bytes(self):
        other, copy = self.put("other", made(6, 10)), self.put("copy", TABLE)
        raw = self.adopted(agrees(TABLE, made(6, 10)), self.table, other)
        self.assertEqual(self.parse(reality.check(self.ledger, raw, copy, other))["outcome"], "HOLDS")

    def test_two_tables_that_both_hold_under_a_bar_need_not_agree(self):
        other = self.put("other", made(4, 5))
        self.assertEqual(self.parse(reality.check(self.ledger, self.adopted(measure(1, 2)), self.table))["outcome"],
                         "HOLDS")
        raw = self.adopted(measure(1, 2, made(4, 5)), other)
        self.assertEqual(self.parse(reality.check(self.ledger, raw, other))["outcome"], "HOLDS")
        raw = self.adopted(agrees(TABLE, made(4, 5)), self.table, other)
        slots = self.parse(reality.check(self.ledger, raw, self.table, other))
        self.assertEqual(slots["outcome"], "DOES-NOT-HOLD")
        self.assertEqual((slots["matching-1"], slots["rows-1"], slots["matching-2"], slots["rows-2"]),
                         ("3", "5", "4", "5"))

    def test_agrees_is_refused_when_either_table_has_no_such_column(self):
        nocolour = self.put("nocolour", NO_COLOUR)
        cases = (("file-2", "file-1", agrees(TABLE, NO_COLOUR), (self.table, nocolour)),
                 ("file-1", "file-2", agrees(NO_COLOUR, TABLE), (nocolour, self.table)))
        for failing, other, raw, files in cases:
            with self.subTest(failing):
                reality.form(raw)  # F1 to F4 pass: the measure text alone does not show the failure
                signature = sign(self.key, raw)
                slots = self.refused("F8", reality.propose, self.ledger, raw, *files)
                self.assertEqual(slots[failing], "no-such-column")
                self.assertEqual(slots[other], "passes")
                self.refused("F8", reality.adopt, self.ledger, raw, LABEL, signature, *files)
                self.refused("F8", reality.check, self.ledger, raw, *files)
                question = self.put("question", raw)
                sigfile = self.put("question.sig", signature.encode())
                for argv in (("propose", self.ledger, question, *files),
                             ("adopt", self.ledger, question, sigfile, LABEL, *files),
                             ("check", self.ledger, question, *files)):
                    code, slots = self.cli(*argv)
                    self.assertEqual(code, 3, slots)
                    self.assertEqual(slots["rule"], "F8")
                    self.assertEqual(slots[failing], "no-such-column")
                self.assertEqual(reality.entries(self.ledger), [])

    def test_same_ship_is_still_refused_and_no_share_agrees_measure_is_extracted(self):
        other = self.put("other", made(6, 10))
        real = self.adopted(agrees(TABLE, made(6, 10)), self.table, other)  # adopted, on these very files
        before = reality.entries(self.ledger)
        sentence = b"Is it the same ship?\n"
        for raw in (sentence, sentence + real, b"Do these two files agree?\n"):
            with self.subTest(raw=raw):
                slots = self.refused("F1", reality.check, self.ledger, raw, self.table, other)
                self.assertEqual(slots["condition"], "not-reality-1")
                self.assertNotIn("measure", slots)
                self.refused("F1", reality.propose, self.ledger, raw, self.table, other)
                self.refused("F1", reality.propose, self.ledger, raw, self.table)
        question = self.put("theseus", sentence)
        code, slots = self.cli("check", self.ledger, question, self.table, other)
        self.assertEqual(code, 3)
        self.assertEqual(slots, {"outcome": "REFUSED", "rule": "F1", "condition": "not-reality-1", "line": "1"})
        self.assertEqual(reality.entries(self.ledger), before)
        self.assertNotIn("same", repr(reality.FORMS))  # no line of either form is spelled with that word

    def test_agrees_propose_and_adopt_record_nothing_when_either_file_is_not_presented(self):
        first, second = self.table, self.put("second", made(6, 10))
        other, absent = self.put("other", made(4, 5)), self.ledger / "absent"
        raw = agrees(TABLE, made(6, 10))
        cases = (("file-1", "other-bytes", (other, second)), ("file-1", "unreadable", (absent, second)),
                 ("file-2", "other-bytes", (first, other)), ("file-2", "unreadable", (first, absent)))
        for which, token, files in cases:
            with self.subTest(operation="propose", files=[file.name for file in files]):
                slots = self.not_presented(reality.propose, self.ledger, raw, *files)
                self.assertEqual(slots[which], token)
        question = self.put("question", raw)
        code, slots = self.cli("propose", self.ledger, question, first, absent)
        self.assertEqual(code, 5)
        self.assertEqual(slots["outcome"], "NOT-RECORDED")
        self.assertEqual(slots["file-1"], "presented")
        self.assertEqual(slots["file-2"], "unreadable")
        self.assertEqual(reality.entries(self.ledger), [])
        reality.propose(self.ledger, raw, first, second)
        signature = sign(self.key, raw)
        for which, token, files in cases:
            with self.subTest(operation="adopt", files=[file.name for file in files]):
                slots = self.not_presented(reality.adopt, self.ledger, raw, LABEL, signature, *files)
                self.assertEqual(slots[which], token)
        sigfile = self.put("question.sig", signature.encode())
        self.assertEqual(self.cli("adopt", self.ledger, question, sigfile, LABEL, other, second)[0], 5)
        self.assertEqual(self.logged("adoption"), [])
        # A file that is not a table, next to a file that is not presented: "not presented" is said, not F8.
        nocolour = self.put("nocolour", NO_COLOUR)
        slots = self.not_presented(reality.propose, self.ledger, agrees(NO_COLOUR, TABLE), nocolour, absent)
        self.assertEqual(slots["file-1"], "presented")
        self.assertEqual(slots["file-2"], "unreadable")
        self.assertEqual(len(reality.entries(self.ledger)), 1)
        # With both named files, the same proposal and signature go through.
        self.assertEqual(self.parse(reality.adopt(self.ledger, raw, LABEL, signature, first, second))["outcome"],
                         "ADOPTED")
        self.assertEqual(self.parse(reality.check(self.ledger, raw, first, second))["outcome"], "HOLDS")

    def test_handwritten_proposal_and_valid_signature_do_not_adopt_a_share_agrees_non_question(self):
        nocolour = self.put("nocolour", NO_COLOUR)
        raw = agrees(TABLE, NO_COLOUR)
        signature = sign(self.key, raw)  # nothing stops a signature being made outside the program
        reality.record(self.ledger, kind="proposal", measure=raw.decode())
        self.assertTrue(reality.signed(self.ledger, LABEL, raw.decode(), signature))
        slots = self.refused("F8", reality.adopt, self.ledger, raw, LABEL, signature, self.table, nocolour)
        self.assertEqual(slots["file-1"], "passes")
        self.assertEqual(slots["file-2"], "no-such-column")
        self.assertEqual(self.logged("adoption"), [])
        self.assertEqual(len(reality.entries(self.ledger)), 1)  # only the handwritten line

    def test_check_of_a_share_agrees_non_question_is_never_recorded(self):
        nocolour, absent = self.put("nocolour", NO_COLOUR), self.ledger / "absent"
        raw = agrees(TABLE, NO_COLOUR)
        reality.record(self.ledger, kind="proposal", measure=raw.decode())
        reality.record(self.ledger, kind="adoption", measure=raw.decode(), adopter=LABEL,
                       signature=sign(self.key, raw))  # a verified adoption, written by hand
        slots = self.refused("F8", reality.check, self.ledger, raw, self.table, nocolour)
        self.assertEqual(slots["file-1"], "passes")
        self.assertEqual(slots["file-2"], "no-such-column")
        # Without every named file the program cannot see the non-question: NOT-CHECKED, and no line.
        expected = (
            ((self.table, absent), {"file-1": "presented", "file-2": "unreadable"}),
            ((absent, nocolour), {"file-1": "unreadable", "file-2": "presented"}),
            ((nocolour, self.table), {"file-1": "other-bytes", "file-2": "other-bytes"}),
        )
        for files, tokens in expected:
            with self.subTest(files=[file.name for file in files]):
                slots = self.parse(reality.check(self.ledger, raw, *files))
                self.assertEqual(slots["outcome"], "NOT-CHECKED")
                self.assertNotIn("matching-1", slots)
                for key, token in tokens.items():
                    self.assertEqual(slots[key], token)
        self.assertEqual(self.logged("check"), [])
        self.assertEqual(len(reality.entries(self.ledger)), 2)  # only the two handwritten lines

    def test_agrees_check_without_adoption_is_refused_before_not_checked(self):
        second, absent = self.put("second", made(6, 10)), self.ledger / "absent"
        raw = agrees(TABLE, made(6, 10))
        self.assertEqual(self.refused("F6", reality.check, self.ledger, raw, self.table, second)["condition"],
                         "no-adoption")
        self.refused("F6", reality.check, self.ledger, raw, self.table, absent)
        reality.propose(self.ledger, raw, self.table, second)
        slots = self.refused("F6", reality.check, self.ledger, raw, absent, absent)
        self.assertEqual(slots["condition"], "proposal-only")
        self.refused("F6", reality.check, self.ledger, raw, second, self.table)  # swapped files: F6 first
        self.assertEqual(self.logged("check"), [])
        # With a signed adoption in the ledger, the missing file gives NOT-CHECKED; the named bytes settle it.
        reality.adopt(self.ledger, raw, LABEL, sign(self.key, raw), self.table, second)
        slots = self.parse(reality.check(self.ledger, raw, self.table, absent))
        self.assertEqual(slots["outcome"], "NOT-CHECKED")
        self.assertEqual(slots["file-2"], "unreadable")
        self.assertEqual(self.logged("check"), [])
        self.assertEqual(self.parse(reality.check(self.ledger, raw, self.table, second))["outcome"], "HOLDS")

    def test_swapped_files_do_not_match_and_a_swapped_measure_is_adopted_separately(self):
        first, second = self.table, self.put("second", made(6, 10))
        raw, swapped = agrees(TABLE, made(6, 10)), agrees(made(6, 10), TABLE)
        self.assertNotEqual(reality.ident(raw.decode()), reality.ident(swapped.decode()))
        slots = self.not_presented(reality.propose, self.ledger, raw, second, first)
        self.assertEqual(slots["file-1"], "other-bytes")
        self.assertEqual(slots["file-2"], "other-bytes")
        self.assertEqual(reality.entries(self.ledger), [])
        self.adopted(raw, first, second)
        slots = self.parse(reality.check(self.ledger, raw, second, first))
        self.assertEqual(slots["outcome"], "NOT-CHECKED")
        self.assertEqual(slots["file-1"], "other-bytes")
        self.assertEqual(slots["file-2"], "other-bytes")
        self.assertEqual(self.logged("check"), [])
        # The swapped measure is different bytes. The adoption of the first does not cover it.
        self.refused("F6", reality.check, self.ledger, swapped, second, first)
        reality.propose(self.ledger, swapped, second, first)
        self.refused("F7", reality.adopt, self.ledger, swapped, LABEL, sign(self.key, raw), second, first)
        reality.adopt(self.ledger, swapped, LABEL, sign(self.key, swapped), second, first)
        self.assertEqual(self.parse(reality.check(self.ledger, swapped, second, first))["outcome"], "HOLDS")
        self.assertEqual(self.parse(reality.check(self.ledger, raw, first, second))["outcome"], "HOLDS")
        self.assertEqual([e["measure"] for e in self.logged("adoption")], [raw.decode(), swapped.decode()])

    def test_wrong_number_of_table_files_is_a_usage_error_and_records_nothing(self):
        second = self.put("second", made(6, 10))
        cases = (("share-agrees given one file", agrees(TABLE, made(6, 10)), (self.table,), "file-count"),
                 ("share-at-least given two files", measure(3, 5), (self.table, second), "file-count"),
                 ("three files", agrees(TABLE, made(6, 10)), (self.table, second, second), "usage"))
        for name, raw, files, condition in cases:
            with self.subTest(name):
                signature = sign(self.key, raw)
                question = self.put("question", raw)
                sigfile = self.put("question.sig", signature.encode())
                for argv in (("propose", self.ledger, question, *files),
                             ("adopt", self.ledger, question, sigfile, LABEL, *files),
                             ("check", self.ledger, question, *files)):
                    code, slots = self.cli(*argv)
                    self.assertEqual(code, 4, slots)
                    self.assertEqual(slots["outcome"], "NOT-RUN")
                    self.assertEqual(slots["condition"], condition)
                    if condition == "file-count":
                        self.assertEqual(slots["given"], str(len(files)))
                        self.assertEqual(slots["named"], "2" if raw.decode().split("\n")[1].endswith("agrees") else "1")
                        self.assertEqual(slots["measure"], reality.ident(raw.decode()))
                if len(files) <= 2 or True:
                    # Python reaches ask for any number; three files is WrongFiles, not usage.
                    with self.assertRaises(WrongFiles) as caught:
                        reality.propose(self.ledger, raw, *files)
                    self.assertEqual(self.parse(str(caught.exception))["condition"], "file-count")
                    with self.assertRaises(WrongFiles):
                        reality.adopt(self.ledger, raw, LABEL, signature, *files)
                    with self.assertRaises(WrongFiles):
                        reality.check(self.ledger, raw, *files)
                self.assertEqual(reality.entries(self.ledger), [])
        # Also with an adoption in the ledger: no verdict and no check line from the wrong number of files.
        raw = self.adopted(agrees(TABLE, made(6, 10)), self.table, second)
        question = self.put("question", raw)
        code, slots = self.cli("check", self.ledger, question, self.table)
        self.assertEqual(code, 4)
        self.assertEqual(slots["condition"], "file-count")
        self.assertEqual(self.logged("check"), [])

    def test_malformed_share_agrees_forms_are_refused_by_the_named_rule(self):
        good = agrees(TABLE, made(6, 10))
        self.assertIsNone(reality.form(good).bar)  # well-formed, and it has no bar
        second = b"table sha256 " + sha(made(6, 10)).encode() + b"\n"
        predicate = b"predicate column-equals colour red\n"
        cases = [
            ("F1", "not-five-lines", good + b"at-least 1 of 2\n"),  # a bar is not part of this question
            ("F1", "not-five-lines", measure(3, 5).replace(predicate, second + predicate)),
            ("F1", "not-five-lines", good.replace(second, b"")),  # four lines
            ("F1", "no-such-question", good.replace(b"share-agrees", b"share-same")),
            ("F1", "no-such-question", good.replace(b"question share-agrees", b"question same")),
            ("F1", "not-reality-1", good.replace(b"reality 1", b"reality 2")),
            ("F2", "not-a-table-line", measure(3, 5).replace(b"share-at-least", b"share-agrees")),
            ("F2", "not-a-table-line", good.replace(second, second[:-2] + b"\n")),  # 63 digits
            ("F3", "not-a-predicate-line", good.replace(b"share-agrees", b"share-at-least")),
            ("F3", "not-a-predicate-line", good.replace(predicate, b"at-least 1 of 2\n")),
            ("F3", "not-a-predicate-line", good.replace(b"column-equals colour red", b"is the same ship")),
        ]
        for rule, condition, raw in cases:
            with self.subTest(raw=raw):
                slots = self.refused(rule, reality.form, raw)
                self.assertEqual(slots["condition"], condition)

    def test_command_line_runs_share_agrees_with_two_table_files(self):
        second, lower = self.put("second", made(6, 10)), self.put("lower", made(2, 5))
        absent = self.ledger / "absent"
        raw = agrees(TABLE, made(6, 10))
        mid = reality.ident(raw.decode())
        question = self.put("question", raw)
        sigfile = self.put("question.sig", sign(self.key, raw).encode())
        self.assertEqual(self.cli("propose", self.ledger, question, self.table, second)[0], 8)
        self.assertEqual(self.cli("check", self.ledger, question, self.table, second)[0], 3)  # not adopted
        self.assertEqual(self.cli("adopt", self.ledger, question, sigfile, LABEL, self.table, second)[0], 9)
        code, slots = self.cli("check", self.ledger, question, self.table, second)
        self.assertEqual(code, 0)
        self.assertEqual(slots["outcome"], "HOLDS")
        self.assertEqual((slots["matching-1"], slots["rows-1"], slots["matching-2"], slots["rows-2"]),
                         ("3", "5", "6", "10"))
        self.assertEqual(slots["measure"], mid)
        code, slots = self.cli("check", self.ledger, question, self.table, absent)
        self.assertEqual(code, 2)
        self.assertEqual(slots["outcome"], "NOT-CHECKED")
        self.assertEqual(slots["file-1"], "presented")
        self.assertEqual(slots["file-2"], "unreadable")
        self.assertEqual(self.cli("check", self.ledger, question, second, self.table)[0], 2)  # swapped files
        self.assertEqual(len(self.logged("check")), 1)
        raw = agrees(TABLE, made(2, 5))
        question.write_bytes(raw)
        sigfile.write_bytes(sign(self.key, raw).encode())
        self.assertEqual(self.cli("propose", self.ledger, question, self.table, lower)[0], 8)
        self.assertEqual(self.cli("adopt", self.ledger, question, sigfile, LABEL, self.table, lower)[0], 9)
        code, slots = self.cli("check", self.ledger, question, self.table, lower)
        self.assertEqual(code, 1)
        self.assertEqual(slots["outcome"], "DOES-NOT-HOLD")
        self.assertEqual((slots["matching-1"], slots["rows-1"], slots["matching-2"], slots["rows-2"]),
                         ("3", "5", "2", "5"))

    # ---- step four: the answer side ----

    def test_malformed_log_line_is_unreadable_not_a_verdict(self):
        raw = self.adopted(measure(3, 5))
        question = self.put("question", raw)
        before = (self.ledger / "log").read_text()
        (self.ledger / "log").write_text(before + "\n")
        with self.assertRaises(Unreadable) as caught:
            reality.check(self.ledger, raw, self.table)
        slots = self.parse(str(caught.exception))
        self.assertEqual(slots["outcome"], "LEDGER-UNREADABLE")
        self.assertEqual(slots["condition"], "log-line-not-json")
        self.assertEqual(slots["log-line"], "3")  # proposal, adoption, then the blank line
        code, slots = self.cli("check", self.ledger, question, self.table)
        self.assertEqual(code, 6)
        self.assertNotEqual(code, 1)
        self.assertEqual(slots["condition"], "log-line-not-json")
        self.assertEqual((self.ledger / "log").read_text(), before + "\n")  # nothing recorded
        (self.ledger / "log").write_text(before + "not json\n")
        self.assertEqual(self.cli("check", self.ledger, question, self.table)[0], 6)
        (self.ledger / "log").write_text(before + json_line({"kind": "proposal"}) + "\n")
        code, slots = self.cli("check", self.ledger, question, self.table)
        self.assertEqual(code, 6)
        self.assertEqual(slots["condition"], "log-line-not-a-record")

    def test_unreadable_adopters_is_not_a_signature_failure(self):
        raw = measure(3, 5)
        reality.propose(self.ledger, raw, self.table)
        (self.ledger / "adopters").unlink()
        with self.assertRaises(Unreadable) as caught:
            reality.adopt(self.ledger, raw, LABEL, sign(self.key, raw), self.table)
        slots = self.parse(str(caught.exception))
        self.assertEqual(slots, {"outcome": "LEDGER-UNREADABLE", "condition": "adopters-unreadable"})
        self.assertEqual(self.logged("adoption"), [])
        reality.record(self.ledger, kind="adoption", measure=raw.decode(), adopter=LABEL,
                       signature=sign(self.key, raw))
        with self.assertRaises(Unreadable) as caught:
            reality.check(self.ledger, raw, self.table)
        self.assertEqual(self.parse(str(caught.exception))["condition"], "adopters-unreadable")
        self.assertEqual(self.logged("check"), [])
        code, slots = self.cli("check", self.ledger, self.put("question", raw), self.table)
        self.assertEqual(code, 6)
        self.assertEqual(slots["condition"], "adopters-unreadable")

    def test_old_english_check_lines_are_still_readable(self):
        raw = self.adopted(measure(3, 5))
        reality.record(self.ledger, kind="check", measure_id=reality.ident(raw.decode()),
                       adopter=LABEL, verdict="HOLDS", detail="3 of 5 rows match")
        slots = self.parse(reality.check(self.ledger, raw, self.table))
        self.assertEqual(slots["outcome"], "HOLDS")
        checks = self.logged("check")
        self.assertEqual(checks[0]["detail"], "3 of 5 rows match")
        self.assertEqual(self.parse(checks[1]["outcome"])["outcome"], "HOLDS")
        self.assertNotIn("detail", checks[1])
        self.assertNotIn("verdict", checks[1])

    def test_outcome_statement_offered_as_a_measure_is_refused(self):
        raw = self.adopted(measure(3, 5))
        statement = reality.check(self.ledger, raw, self.table)
        slots = self.refused("F1", reality.check, self.ledger, statement.encode(), self.table)
        self.assertEqual(slots["condition"], "not-reality-1")
        self.assertNotIn("measure", slots)
        self.assertEqual(len(self.logged("check")), 1)

    def test_unexpected_failure_is_not_a_verdict(self):
        original = reality.form
        try:
            def boom(*_args, **_kwargs):
                raise RuntimeError("secret")
            reality.form = boom
            code, slots = self.cli("propose", self.ledger, self.put("question", measure(3, 5)), self.table)
            self.assertEqual(code, 7)
            self.assertEqual(slots, {"outcome": "FAILED", "condition": "unexpected"})
            self.assertEqual(reality.entries(self.ledger), [])
        finally:
            reality.form = original

    # ---- step four, adversarial review: holes found and closed ----

    def run_script(self, *argv, stdout=None, shell_close_stdout=False):
        script = [sys.executable, str(Path(reality.__file__)), *map(str, argv)]
        if shell_close_stdout:
            script = ["sh", "-c", 'exec "$@" >&-', "sh", *script]
        return subprocess.run(script, stdout=stdout, stderr=subprocess.PIPE)

    def unwritable(self, *argv):
        """Run the program with standard output unwritable (closed/read-only, and /dev/full if present)."""
        if os.name == "nt":
            with open(os.devnull, "rb") as ro:
                runs = [self.run_script(*argv, stdout=ro)]
        else:
            runs = [self.run_script(*argv, shell_close_stdout=True)]
        if Path("/dev/full").exists():
            with open("/dev/full", "w") as full:
                runs.append(self.run_script(*argv, stdout=full))
        return [(done.returncode, done.stderr) for done in runs]

    def test_a_recorded_check_that_cannot_be_written_is_not_delivered(self):
        raw = self.adopted(measure(3, 5))
        question = self.put("question", raw)
        runs = self.unwritable("check", self.ledger, question, self.table)
        self.assertEqual(runs, [(10, b"")] * len(runs))  # was 0, then 7 (FAILED), with no statement
        checks = self.logged("check")
        self.assertEqual(len(checks), len(runs))  # each check was made and recorded
        self.assertEqual(self.parse(checks[0]["outcome"])["outcome"], "HOLDS")
        self.assertEqual(reality.CODES["NOT-DELIVERED"], 10)
        self.assertEqual([reality.CODES[k] for k in reality.KINDS[:10]], list(range(10)))  # 0 to 9 unchanged
        self.assertEqual(reality.state(outcome="NOT-DELIVERED", measure=sha(raw), **{"log-line": 3}),
                         f"outcome=NOT-DELIVERED log-line=3 measure={sha(raw)}")
        statement, undelivered = reality._check(self.ledger, raw, self.table)
        self.assertEqual(self.parse(statement)["outcome"], "HOLDS")
        self.assertEqual(self.parse(undelivered),  # the log-line is the check line just recorded
                         {"outcome": "NOT-DELIVERED", "log-line": str(len(reality.entries(self.ledger))),
                          "measure": sha(raw)})
        self.assertIsInstance(reality.check(self.ledger, raw, self.table), str)  # Python gets the verdict

    def test_an_unwritable_statement_that_recorded_no_check_is_failed(self):
        raw = measure(3, 5)
        question = self.put("question", raw)
        sig = self.ledger / "question.sig"
        sig.write_text(sign(self.key, raw))
        for argv in (("propose", self.ledger, question, self.table),
                     ("adopt", self.ledger, question, sig, LABEL, self.table),
                     ("check", self.ledger, question, self.put("other", b"x\n")),  # NOT-CHECKED: not recorded
                     ("check", self.ledger, self.put("prose", b"Is it the same ship?\n"), self.table),
                     ("propose",)):
            runs = self.unwritable(*argv)
            self.assertEqual(runs, [(7, b"")] * len(runs), argv)
        self.assertEqual(self.logged("check"), [])
        self.assertEqual(len(self.logged("proposal")), 1)  # propose recorded once, and dedupes
        self.assertEqual(len(self.logged("adoption")), len(runs))  # adopt did record: see the README

    def test_a_log_without_a_final_newline_is_not_written_to(self):
        raw = self.adopted(measure(3, 5))
        log = self.ledger / "log"
        log.write_bytes(log.read_bytes()[:-1])
        before = log.read_bytes()
        code, slots = self.cli("check", self.ledger, self.put("question", raw), self.table)
        self.assertEqual(slots, {"outcome": "NOT-RUN", "condition": "log-not-written"})  # was HOLDS
        self.assertEqual(log.read_bytes(), before)  # the adoption line is not joined to a check line
        with self.assertRaises(reality.NotRun):
            reality.propose(self.ledger, measure(2, 5), self.table)
        self.assertEqual(log.read_bytes(), before)

    def test_log_lines_are_counted_by_newline_bytes_only(self):
        raw = self.adopted(measure(3, 5))
        log = self.ledger / "log"
        before = log.read_bytes()
        for joiner in (b"\f", b"\r", b"\x1c", "\u2028".encode()):
            log.write_bytes(before + b'{"kind": "note"}' + joiner + b'{"kind": "note"}\n')
            with self.assertRaises(Unreadable) as caught:  # was HOLDS: one line not JSON, read as two records
                reality.check(self.ledger, raw, self.table)
            self.assertEqual(caught.exception.slots, {"outcome": "LEDGER-UNREADABLE",
                                                      "condition": "log-line-not-json", "log-line": 3})
        log.write_bytes(before.replace(b"\n", b"\r\n"))  # a carriage return before each newline is JSON space
        slots = self.parse(reality.check(self.ledger, raw, self.table))
        self.assertEqual((slots["outcome"], slots["adoption-line"]), ("HOLDS", "2"))

    def test_json_the_reader_cannot_take_is_an_unreadable_ledger_not_a_failure(self):
        raw = self.adopted(measure(3, 5))
        before = (self.ledger / "log").read_text()
        for line in ('{"kind": "note", "n": ' + "1" * 5000 + "}", '{"kind": "note", "n": ' + "[" * 100000 + "]" * 100000 + "}"):
            (self.ledger / "log").write_text(before + line + "\n")
            code, slots = self.cli("check", self.ledger, self.put("question", raw), self.table)
            self.assertEqual(code, 6)  # was 7, FAILED
            self.assertEqual(slots, {"outcome": "LEDGER-UNREADABLE", "condition": "log-line-not-a-record",
                                     "log-line": "3"})

    def test_a_ledger_that_cannot_be_opened_is_unreadable_not_unadopted(self):
        raw = self.adopted(measure(3, 5))
        with self.assertRaises(Unreadable) as caught:  # was F6 no-adoption
            reality.check(self.table, raw, self.table)  # a file given as the ledger
        self.assertEqual(caught.exception.slots, {"outcome": "LEDGER-UNREADABLE", "condition": "log-unreadable"})
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            self.ledger.chmod(0)
            try:
                with self.assertRaises(Unreadable):  # was FAILED
                    reality.check(self.ledger, raw, self.table)
            finally:
                self.ledger.chmod(0o700)
        with self.assertRaises(reality.Refusal) as caught:  # a ledger that does not exist holds nothing
            reality.check(self.ledger / "missing", raw, self.table)
        self.assertEqual(caught.exception.slots["condition"], "no-adoption")

    def test_adopters_file_need_only_be_readable_bytes(self):
        adopters = self.ledger / "adopters"
        adopters.write_bytes(adopters.read_bytes().rstrip(b"\n") + b" caf\xe9\n")  # ssh-keygen accepts this
        raw = self.adopted(measure(3, 5))  # was LEDGER-UNREADABLE
        self.assertEqual(self.parse(reality.check(self.ledger, raw, self.table))["outcome"], "HOLDS")

    def test_signed_measure_never_names_a_handwritten_non_question(self):
        raw = measure(3, 5)
        reality.propose(self.ledger, raw, self.table)
        for text in ("Is it the same ship?", measure(3, 5).decode() + "\n", measure(6, 5).decode()):
            reality.record(self.ledger, kind="proposal", measure=text)  # handwritten: not a question
            signature = sign(self.key, text.encode())  # verifies over that text, not over raw
            slots = self.refused("F5", reality.adopt, self.ledger, raw, LABEL, signature, self.table)
            self.assertEqual(slots["condition"], "not-verified")  # was F7 signed-measure=<id of the text>
            self.assertNotIn("signed-measure", slots)
        self.assertEqual(self.logged("adoption"), [])
        low = measure(2, 5)  # a well-formed proposed measure is still named under F7
        reality.propose(self.ledger, low, self.table)
        slots = self.refused("F7", reality.adopt, self.ledger, raw, LABEL, sign(self.key, low), self.table)
        self.assertEqual(slots["signed-measure"], reality.ident(low.decode()))

    def test_state_takes_only_integers_where_integers_are_listed(self):
        for slot, value in (("line", True), ("named", 1.0), ("line", 1.0), ("given", True), ("log-line", 2.0)):
            with self.assertRaises(ValueError):  # line=True was written as "line=True"
                reality.state(outcome="REFUSED", **{slot: value})

    def test_trusted_file_has_no_rule_sentences_or_usage_prose(self):
        text = Path(reality.__file__).read_text()
        for snippet in (
            "a question is exactly one of the closed five-line forms",
            "why it could pass for well-formed",
            "why it is not",
            "human language lets any sentence stand",
            "This program verifies signatures with ssh-keygen. It never signs.",
            "DOES NOT HOLD",
            "NOT CHECKED",
            "the named bytes were not presented",
            'ABSENT',
        ):
            self.assertNotIn(snippet, text)
        self.assertNotIn('("same"', text)

    def test_readme_states_the_trusted_line_count(self):
        here = Path(__file__).parent
        stated = re.search(r"reality\.py, (\d+) lines", (here / "README.md").read_text())
        self.assertIsNotNone(stated)
        self.assertEqual(int(stated.group(1)), len((here / "reality.py").read_text().splitlines()))


def foundation(name: str, *parents: str) -> bytes:
    return ("reality 1\nfoundation %s\n" % name + "".join("rests-on sha256 %s\n" % p for p in sorted(parents))).encode()


def tag_text(table: bytes, fid: str) -> bytes:
    return f"reality 1\ntag\ntable sha256 {sha(table)}\nrests-on sha256 {fid}\n".encode()


def undermine_text(fid: str, witness: bytes) -> bytes:
    return f"reality 1\nundermine\nfoundation sha256 {fid}\nwitness sha256 {sha(witness)}\n".encode()


EARTH, SUN = made(3, 10), made(0, 10)  # made up: a "seen from here" and a "seen from there" table
JUPITER = made(4, 10)  # made up: a third table, resting on a foundation that rests on the first one's


class Foundations(unittest.TestCase):
    """Step five: signed foundations, tags, undermines, impact. All tables made up, all keys throwaway."""
    setUpClass = classmethod(Steps.setUpClass.__func__)
    put, adopted, logged, parse, refused = Steps.put, Steps.adopted, Steps.logged, Steps.parse, Steps.refused

    def setUp(self):
        Steps.setUp(self)
        self.files = {name: self.put(name, data) for name, data in
                      (("earth", EARTH), ("sun", SUN), ("jupiter", JUPITER), ("half", made(3, 6)),
                       ("half2", made(5, 10)))}

    def found(self, raw: bytes) -> str:
        reality.adopt_foundation(self.ledger, raw, LABEL, sign(self.key, raw, reality.FOUNDATION_NAMESPACE))
        return sha(raw)

    def tagged(self, table: bytes, fid: str) -> None:
        raw = tag_text(table, fid)
        reality.tag(self.ledger, raw, LABEL, sign(self.key, raw, reality.FOUNDATION_NAMESPACE))

    def world(self):
        """earth <- epicycle; sun. EARTH table on earth, SUN on sun, JUPITER on epicycle. Witness EARTH vs SUN."""
        self.earth = self.found(foundation("observer-earth"))
        self.sun = self.found(foundation("observer-sun"))
        self.epicycle = self.found(foundation("epicycle", self.earth))
        for table, fid in ((EARTH, self.earth), (SUN, self.sun), (JUPITER, self.epicycle)):
            self.tagged(table, fid)
        self.witness = self.adopted(agrees(EARTH, SUN), self.files["earth"], self.files["sun"])
        self.jup = self.adopted(measure(1, 5, JUPITER), self.files["jupiter"])

    def knock(self, fid: str, witness: bytes = None, key=None, namespace=reality.UNDERMINE_NAMESPACE,
              tables=None) -> str:
        witness = witness or self.witness
        raw = undermine_text(fid, witness)
        return reality.undermine(self.ledger, raw, LABEL, sign(key or self.key, raw, namespace), witness,
                                 *(tables or (self.files["earth"], self.files["sun"])))

    def test_foundation_rests_only_on_foundations_already_adopted_so_no_cycle_can_form(self):
        root = foundation("root")
        child = foundation("child", sha(root))
        slots = self.refused("F9", reality.adopt_foundation, self.ledger, child, LABEL,
                             sign(self.key, child, reality.FOUNDATION_NAMESPACE))
        self.assertEqual((slots["condition"], slots["line"]), ("parent-not-adopted", "3"))
        # a handwritten adoption line with a valid signature, whose parent was never adopted, counts for nothing
        reality.record(self.ledger, kind="foundation-adoption", foundation=child.decode(), adopter=LABEL,
                       signature=sign(self.key, child, reality.FOUNDATION_NAMESPACE))
        self.refused("F9", reality.impact, self.ledger, sha(child))
        # adopting the parent afterwards does not make the earlier line count: order in the log is the order
        rid = self.found(root)
        self.assertEqual(self.parse(reality.impact(self.ledger, rid).splitlines()[0])["foundations"], "0")
        for text, condition in ((foundation("x", rid, rid), "rests-on-not-ascending"),
                                (b"reality 1\nfoundation two words\n", "not-a-foundation-line"),
                                (b"reality 1\nfoundation x\nrests-on " + rid.encode() + b"\n", "not-a-rests-on-line"),
                                (foundation("x", *[sha(bytes([i])) for i in range(4)]), "bad-line-count")):
            self.assertEqual(self.refused("F9", reality.parse_foundation, text)["condition"], condition)

    def test_foundations_and_tags_must_be_signed_by_a_listed_key_in_their_own_namespace(self):
        raw = foundation("observer-earth")
        for signature in (sign(self.unlisted, raw, reality.FOUNDATION_NAMESPACE), sign(self.key, raw),
                          sign(self.key, raw, reality.UNDERMINE_NAMESPACE)):
            self.refused("F5", reality.adopt_foundation, self.ledger, raw, LABEL, signature)
        fid = self.found(raw)
        claim = tag_text(EARTH, fid)
        self.refused("F5", reality.tag, self.ledger, claim, LABEL, sign(self.key, claim))
        unknown = tag_text(EARTH, sha(b"nothing"))
        self.assertEqual(self.refused("F9", reality.tag, self.ledger, unknown, LABEL,
                                      sign(self.key, unknown, reality.FOUNDATION_NAMESPACE))["condition"],
                         "foundation-not-adopted")
        self.assertEqual(self.logged("tag"), [])
        reality.record(self.ledger, kind="tag", tag=claim.decode(), adopter=LABEL, signature=sign(self.key, claim))
        self.assertEqual(reality._graph(self.ledger, reality._records(self.ledger)).tags, {})  # wrong namespace

    def test_undermine_recounts_the_witness_and_names_the_side_it_knocks_down(self):
        self.world()
        slots = self.parse(self.knock(self.earth))
        self.assertEqual(slots, {"outcome": "UNDERMINED", "foundation": self.earth, "side": "1",
                                 "measure": sha(self.witness), "matching-1": "3", "rows-1": "10",
                                 "matching-2": "0", "rows-2": "10", "undermine-line": str(len(reality.entries(self.ledger)))})
        self.assertEqual(self.logged("undermine")[0]["witness"], self.witness.decode())

    def test_undermine_is_refused_unless_every_condition_is_met(self):
        self.world()
        unadopted = agrees(EARTH, made(3, 9))
        self.put("e2", made(3, 9))
        reality.propose(self.ledger, unadopted, self.files["earth"], self.ledger / "e2")
        self.assertEqual(self.refused("F6", self.knock, self.earth, unadopted, None,
                                      reality.UNDERMINE_NAMESPACE, (self.files["earth"], self.ledger / "e2"))["condition"], "proposal-only")
        slots = self.refused("F10", self.knock, self.earth, None, None, reality.UNDERMINE_NAMESPACE,
                             (self.files["earth"], self.files["jupiter"]))
        self.assertEqual((slots["condition"], slots["file-2"]), ("witness-not-presented", "other-bytes"))
        holding = self.adopted(agrees(EARTH, self.put("e3", made(6, 20)).read_bytes()), self.files["earth"],
                               self.ledger / "e3")
        self.tagged(made(6, 20), self.sun)
        self.assertEqual(self.refused("F10", self.knock, self.earth, holding, None, reality.UNDERMINE_NAMESPACE,
                                      (self.files["earth"], self.ledger / "e3"))["condition"], "witness-holds")
        self.assertEqual(self.refused("F10", self.knock, self.epicycle)["condition"], "not-a-side")  # not direct
        self.tagged(SUN, self.earth)
        self.assertEqual(self.refused("F10", self.knock, self.earth)["condition"], "both-sides")
        self.assertEqual(self.refused("F10", self.knock, self.sun, self.jup, None, reality.UNDERMINE_NAMESPACE,
                                      (self.files["jupiter"],))["condition"], "not-a-comparison")
        other = undermine_text(self.sun, self.witness)
        self.assertEqual(self.refused("F10", reality.undermine, self.ledger, other, LABEL,
                                      sign(self.key, other, reality.UNDERMINE_NAMESPACE), self.jup,
                                      self.files["jupiter"])["condition"], "other-witness")
        for key, namespace in ((self.unlisted, reality.UNDERMINE_NAMESPACE), (self.key, reality.NAMESPACE),
                               (self.key, reality.FOUNDATION_NAMESPACE)):
            self.assertEqual(self.refused("F5", self.knock, self.sun, None, key, namespace)["condition"],
                             "not-verified")
        self.assertEqual(self.logged("undermine"), [])

    def test_holds_undermined_keeps_the_counts_and_two_table_comparisons_are_flagged(self):
        self.world()
        before = self.parse(reality.check(self.ledger, self.jup, self.files["jupiter"]))
        self.assertEqual(before["outcome"], "HOLDS")
        self.knock(self.earth)
        after = self.parse(reality.check(self.ledger, self.jup, self.files["jupiter"]))
        self.assertEqual(after, {**before, "outcome": "HOLDS-UNDERMINED", "undermined-foundation": self.earth,
                                 "undermines": "1"})  # via JUPITER -> epicycle -> earth; 4 of 10 unchanged
        witness = self.parse(reality.check(self.ledger, self.witness, self.files["earth"], self.files["sun"]))
        self.assertEqual((witness["outcome"], witness["undermined-foundation"]), ("DOES-NOT-HOLD", self.earth))
        pair = self.adopted(agrees(made(3, 6), made(5, 10)),  # 3/6 = 5/10: holds
                            self.files["half"], self.files["half2"])
        self.tagged(made(3, 6), self.epicycle)
        slots = self.parse(reality.check(self.ledger, pair, self.files["half"], self.files["half2"]))
        self.assertEqual((slots["outcome"], slots["matching-1"], slots["rows-1"], slots["undermined-foundation"]),
                         ("HOLDS-UNDERMINED", "3", "6", self.earth))
        sun = self.parse(reality.check(self.ledger, self.adopted(measure(1, 10, SUN), self.files["sun"]),
                                       self.files["sun"]))
        self.assertNotIn("undermined-foundation", sun)  # the side not named is not flagged
        code = reality.main(["check", str(self.ledger), str(self.put("q", self.jup)), str(self.files["jupiter"])])
        self.assertEqual(code, 12)

    def test_impact_lists_every_dependent_however_far_down(self):
        self.world()
        top = self.found(foundation("top", self.epicycle))
        self.tagged(made(3, 6), top)
        far = self.adopted(measure(1, 2, made(3, 6)), self.files["half"])
        lines = reality.impact(self.ledger, self.earth).splitlines()
        self.assertEqual(self.parse(lines[0]), {"outcome": "IMPACT", "foundation": self.earth, "undermined": "no",
                                                "foundations": "2", "measures": "3"})
        self.assertEqual(sorted(lines[1:]), sorted([f"outcome=DEPENDS foundation={self.epicycle}",
                                                    f"outcome=DEPENDS foundation={top}",
                                                    f"outcome=DEPENDS measure={sha(self.witness)}",
                                                    f"outcome=DEPENDS measure={sha(self.jup)}",
                                                    f"outcome=DEPENDS measure={sha(far)}"]))
        self.knock(self.earth)
        self.assertIn("undermined=yes", reality.impact(self.ledger, self.earth).splitlines()[0])
        self.assertEqual(reality.impact(self.ledger, self.sun).splitlines()[0].split()[-2:],
                         ["foundations=0", "measures=1"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(reality.main(["impact", str(self.ledger), self.earth]), 13)
        self.assertEqual(len(out.getvalue().splitlines()), 6)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reality.main(["impact", str(self.ledger), "earth"]), 4)

    def test_the_log_is_not_protected_a_deleted_undermine_line_is_not_noticed(self):
        self.world()
        self.knock(self.earth)
        log = self.ledger / "log"
        log.write_bytes(b"".join(line for line in log.read_bytes().splitlines(True) if b'"undermine"' not in line))
        self.assertEqual(self.parse(reality.check(self.ledger, self.jup, self.files["jupiter"]))["outcome"], "HOLDS")

    def test_undermine_line_before_witness_adoption_does_not_flag_dependents(self):
        self.world()
        self.knock(self.earth)
        log = self.ledger / "log"
        lines = log.read_bytes().splitlines(True)
        entries = [json.loads(line) for line in lines]
        adopt = next(i for i, e in enumerate(entries)
                     if e.get("kind") == "adoption" and e.get("measure") == self.witness.decode())
        und = next(i for i, e in enumerate(entries) if e.get("kind") == "undermine")
        moved = lines.pop(und)
        if und < adopt:
            adopt -= 1
        log.write_bytes(b"".join(lines[:adopt] + [moved] + lines[adopt:]))
        self.assertEqual(self.parse(reality.check(self.ledger, self.jup, self.files["jupiter"]))["outcome"], "HOLDS")

    def test_record_writes_lf_only_bytes(self):
        self.adopted(measure(3, 5))
        raw = (self.ledger / "log").read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))


def json_line(obj: dict) -> str:
    import json
    return json.dumps(obj)


if __name__ == "__main__":
    unittest.main()
