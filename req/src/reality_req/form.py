"""Formation rules and statuses of a ledger (req/SPEC.md sections 3-5). Trusted.

Statuses are derived, never written: OFFERED (no measure proposed), PROPOSED (measures, none
adopted), ADOPTED (exactly one current, valid adoption). Every refusal names what is absent and
never what the requirement means. Reality never reads a requirement's words.
"""
import hashlib
import pathlib
import re

from . import say
from .syntax import SyntaxRefusal, parse, split

TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}")
REFERENCE_FREE = {"now", "today", "tomorrow", "yesterday", "here", "soon", "later"}
CONDITIONS = ("exceeds(", "below(", "atleast(", "atmost(")


def kind(src):
    """A fragment line's role: 'condition' (a comparison claim), 'shown' (another claim), 'let', or None."""
    s = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src).split("#")[0].strip()
    if s.startswith("claim "):
        return "condition" if s[6:].lstrip().startswith(CONDITIONS) else "shown"
    return "let" if s.startswith("let ") else None


class Refusal(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def sha(b: bytes):
    return hashlib.sha256(b).hexdigest()


def blank(text):
    return text is None or text.strip() == "" or all(c.isspace() or c in "\u3164\u115f\u1160\u200b\ufeff" for c in text)


class Ledger:
    def __init__(self, base: pathlib.Path, runner=None, verifier=None, run_from=0):
        self.base, self.runner, self.verifier, self.run_from = base, runner, verifier, run_from
        self.kinds = {}       # name -> person | tool | requirement | measure | task | refused
        self.reqs = {}        # name -> {text, fp, owner, measures: [names], current: (measure, line) | None, stale: {measure: (line, rfp, mfp)}}
        self.measures = {}    # name -> {req, by, says, outside, path, fp, frag lines, trials: [lines], history}
        self.out = []
        self.refused = 0

    # -- names
    def new(self, st, kind):
        if st.name in self.kinds:
            raise Refusal("N002", f"'{st.name}' is already declared (as a {self.kinds[st.name]})")
        self.kinds[st.name] = kind

    def need(self, name, kind):
        have = self.kinds.get(name)
        if have == "refused":
            raise Refusal("N003", f"'{name}' was refused where it was declared, so nothing that uses it forms")
        if have != kind:
            raise Refusal("N001", f"'{name}' " + (f"is a {have}, not a {kind}" if have else f"is not declared; expected a {kind}"))
        return name

    def person(self, name, role):
        if self.kinds.get(name) == "tool":
            raise Refusal("G011", f"{name} is declared as a tool; a tool can propose measures, never own a requirement or adopt a measure")
        return self.need(name, "person")

    # -- the run
    def check(self, data: bytes):
        try:
            stmts = split(data)
        except SyntaxRefusal as e:
            self.emit(e.line, say.refused(e.code, e.msg)); self.refused += 1
            return self.out + [say.summary(self.refused)]
        for line, toks in stmts:
            try:
                st = parse(line, toks)
                lines = getattr(self, "st_" + st.kind)(st)
            except (Refusal, SyntaxRefusal) as e:
                self.refused += 1
                self.emit(line, say.refused(e.code, e.msg))
                name = toks[1][1] if len(toks) > 1 and toks[0][1] in ("person", "tool", "requirement", "measure", "task") else None
                if name and name not in self.kinds:
                    self.kinds[name] = "refused"
                continue
            self.emit(line, *lines)
        self.out.append(say.summary(self.refused))
        return self.out

    def emit(self, line, first, *more):
        self.out.append(f"line {line}: {first}")
        self.out.extend("  " + m for m in more)

    # -- declarations
    def st_person(self, st):
        self.new(st, "person"); return [say.declared("person", st.name)]

    def st_tool(self, st):
        self.new(st, "tool"); return [say.declared("tool", st.name)]

    def st_requirement(self, st):
        if blank(st.text):
            raise Refusal("E004", "a requirement's text is a non-empty text")
        owner = self.person(st.get("owner"), "owner")
        if "from" in st.clauses and blank(st.get("from")):
            raise Refusal("E004", "'from' is a non-empty text")
        self.new(st, "requirement")
        self.reqs[st.name] = dict(text=st.text, fp=sha(st.text.encode("utf-8")), owner=owner, measures=[], current=None, stale={})
        return say.offered(st.name, st.text, owner)

    def st_measure(self, st):
        req = self.need(st.get("for"), "requirement")
        by = st.get("proposed_by")
        if self.kinds.get(by) not in ("person", "tool"):
            self.need(by, "person or tool")
        for k in ("says", "outside"):
            if k in st.clauses and blank(st.get(k)):
                raise Refusal("E004", f"'{k}' is a non-empty text")
        parts_spec = st.clauses.get("parts")
        if parts_spec:
            parts = []
            for pname, path, fp in parts_spec:
                frag = self.fragment(f"{st.name}.{pname}", path, fp[7:])
                parts.append(dict(name=pname, path=path, fp=fp[7:], frag=frag))
            # One adoption hash covers every part: digest of ordered name=fragsha lines.
            body = "composite-measure-1\n" + "".join(f"part {p['name']} sha256:{p['fp']}\n" for p in parts)
            mfp = sha(body.encode("utf-8"))
            ncond = sum(self.count(p["frag"]) for p in parts)
            self.new(st, "measure")
            self.measures[st.name] = dict(
                req=req, by=by, by_kind=self.kinds[by], says=st.get("says"), outside=st.get("outside"),
                fp=mfp, frag=None, parts=parts, trials=[],
            )
            self.reqs[req]["measures"].append(st.name)
            return say.proposed_composite(
                st.name, req, by, self.kinds[by], st.get("says"), st.get("outside"), mfp, parts, ncond
            )
        path, fp = st.get("fragment")
        frag = self.fragment(st.name, path, fp[7:])
        self.new(st, "measure")
        self.measures[st.name] = dict(req=req, by=by, by_kind=self.kinds[by], says=st.get("says"), outside=st.get("outside"),
                                      fp=fp[7:], frag=frag, parts=None, trials=[])
        self.reqs[req]["measures"].append(st.name)
        return say.proposed(st.name, req, by, self.kinds[by], st.get("says"), st.get("outside"), fp[7:], self.count(frag))

    def fragment(self, m, path, fp):
        p = pathlib.PurePosixPath(path)
        if p.is_absolute() or ".." in p.parts or path == "":
            raise Refusal("G023", f"fragment path {path!r} must be relative to the ledger's folder, without '..'")
        try:
            data = (self.base / p).read_bytes()
        except OSError:
            raise Refusal("G023", f"no fragment file {path!r} next to the ledger; the measure names it, so its bytes are part of the measure")
        if sha(data) != fp:
            raise Refusal("G023", f"fragment {path!r} has sha256:{sha(data)}, not the sha256:{fp} the measure names: these are not the bytes that were proposed")
        try:
            lines = data.decode("utf-8").split("\n")
        except UnicodeDecodeError:
            raise Refusal("G023", f"fragment {path!r} is not UTF-8")
        conds = 0
        for n, ln in enumerate(lines, start=1):
            code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', ln).split("#")[0].strip()
            if not code:
                continue
            word = code.split()[0]
            if word in ("file", "dataset"):
                raise Refusal("G020", f"{m}'s fragment line {n} names data ('{word}'): a measure's fragment names no data; the data is bound by 'check' or 'try', so that one measure can be checked on any data")
            if re.search(r"\bis\b", code):
                raise Refusal("G022", f"{m}'s fragment line {n} uses 'is': a condition is a comparison, so that a refusal V001 always means a comparison the bytes contradict")
            if word not in ("let", "claim"):
                raise Refusal("G020", f"{m}'s fragment line {n} is not a 'let' or 'claim' statement")
            conds += word == "claim" and code[5:].lstrip().startswith(CONDITIONS)
        if conds == 0:
            raise Refusal("G021", f"{m} has no condition (no exceeds, below, atleast or atmost claim), so nothing in it can hold or fail")
        return lines

    @staticmethod
    def count(frag):
        return sum(1 for ln in frag if kind(ln) == "condition")

    # -- tasks
    def st_task(self, st):
        if "propose" in st.clauses:
            req = self.need(st.get("propose"), "requirement")
            who = st.get("assigned_to")
            if self.kinds.get(who) not in ("person", "tool"):
                self.need(who, "person or tool")
            self.new(st, "task")
            return say.task_propose(st.name, req, who)
        req = self.need(st.get("deliver"), "requirement")
        r = self.reqs[req]
        if "by" not in st.clauses or r["current"] is None:
            raise Refusal("G001", say.g001(st.name, req, r["text"], self.listing(req)))
        m = st.get("by")
        self.not_current(req, m, "deliver")
        if "on" not in st.clauses:
            raise Refusal("G005", f"task {st.name} delivers {req} by {m} but names no data, so its done-condition is not stated: write 'deliver {req} by {m} on sha256:<data>'")
        who = st.get("assigned_to")
        if self.kinds.get(who) not in ("person", "tool"):
            self.need(who, "person or tool")
        self.new(st, "task")
        return say.task_deliver(st.name, req, m, st.get("on")[7:], who)

    def listing(self, req):
        ms = self.reqs[req]["measures"]
        cur = self.reqs[req]["current"]
        def hist(m):   # only valid adoptions and withdrawals enter history, so a non-current measure with history was withdrawn
            h = ", ".join(f"{a}{'ed' if a == 'adopt' else 'n'} line {ln} at {say.q(at)}" for a, x, ln, at in self.reqs[req].get("history", []) if x == m)
            return h if cur and cur[0] == m else f"withdrawn; {h}" if h else "not adopted"
        return ", ".join(f"{m} ({hist(m)}; proposed by {self.measures[m]['by']})" for m in ms) or "none"

    def not_current(self, req, m, what):
        cur = self.reqs[req]["current"]
        if self.kinds.get(m) != "measure":
            self.need(m, "measure")
        if m in self.reqs[req]["stale"]:
            ln, rfp, mfp = self.reqs[req]["stale"][m]
            raise Refusal("G014", say.g014(ln, req, m, rfp, mfp, self.reqs[req]["fp"], self.measures[m]["fp"]))
        if cur is None or cur[0] != m:
            state = f"proposed for {req}, not its adopted measure" if self.measures[m]["req"] == req else f"a measure of {self.measures[m]['req']}, not of {req}"
            if any(h[0] == "withdraw" and h[1] == m for h in self.reqs[req].get("history", [])):
                state = f"withdrawn for {req}, not its adopted measure"
            raise Refusal("G003", f"{m} is {state}: a {what} by it would treat {req} as meaning {m}. 'try {m} on <data>' runs it as a trial that says nothing about {req}")

    # -- adoption and withdrawal
    def act(self, st):
        m, req = st.name, self.need(st.get("for"), "requirement")
        self.need(m, "measure")
        r = self.reqs[req]
        who = self.person(st.get("by"), "adopter")
        if who != r["owner"]:
            raise Refusal("G010", f"{who} is not the owner of {req} (owner: {r['owner']}); only the owner adopts or withdraws a measure for {req}")
        if self.measures[m]["req"] != req:
            raise Refusal("G016", f"{m} is not proposed for {req}")
        at = st.get("at")
        if at.strip().lower() in REFERENCE_FREE:
            raise Refusal("T001", f"'{at.strip()}' has no referent in Reality: there is no built-in present moment or place. Write the time with its UTC offset, e.g. \"2026-11-14T15:02:00+01:00\"")
        if not TIME.fullmatch(at):
            raise Refusal("T001", f"the time \"{at}\" names no offset or is not a time: write it with its UTC offset, e.g. \"2026-11-14T15:02:00+01:00\"")
        rfp, mfp = st.get("requirement_text")[7:], st.get("measure")[7:]
        if (rfp, mfp) != (r["fp"], self.measures[m]["fp"]):
            r["stale"][m] = (st.line, rfp, mfp)
            raise Refusal("G014", say.g014(st.line, req, m, rfp, mfp, r["fp"], self.measures[m]["fp"]))
        return m, req, r, who, at

    def signed(self, st, word, m, req, who, at):
        if "sig" not in st.clauses:
            raise Refusal("G012", f"the {word} of {m} for {req} by {who} has no signature; an adoption or withdrawal is the owner's signed act, and nothing else makes one")
        sig = pathlib.PurePosixPath(st.get("sig"))
        if sig.is_absolute() or ".." in sig.parts:
            raise Refusal("G012", f"signature path {st.get('sig')!r} must be relative to the ledger's folder, without '..'")
        payload = say.payload(word, req, self.reqs[req]["fp"], m, self.measures[m]["fp"], who, at)
        ok = self.verifier(payload, who, self.base / sig) if self.verifier else "no allowed_signers file was given, so it cannot be checked"
        if ok is not True:
            raise Refusal("G012", f"the {word} of {m} for {req} by {who} has {ok}; an adoption or withdrawal is the owner's signed act, and nothing else makes one")

    def st_adopt(self, st):
        m, req, r, who, at = self.act(st)
        if r["current"] is not None and r["current"][0] == m:
            raise Refusal("G015", f"{m} is already the adopted measure of {req} (line {r['current'][1]}); an adoption is recorded once")
        if r["current"] is not None:
            raise Refusal("G015", f"{req} already has an adopted measure, {r['current'][0]} (line {r['current'][1]}); adopting {m} as well would give {req} two meanings. To replace it, withdraw {r['current'][0]} first")
        self.signed(st, "adoption", m, req, who, at)
        r["current"] = (m, st.line)
        r["stale"].pop(m, None)
        r.setdefault("history", []).append(("adopt", m, st.line, at))
        return say.adopted(m, req, who, at, self.measures[m]["trials"])

    def st_withdraw(self, st):
        m, req, r, who, at = self.act(st)
        if r["current"] is None or r["current"][0] != m:
            raise Refusal("G017", f"{m} is not the adopted measure of {req}, so there is nothing to withdraw")
        self.signed(st, "withdrawal", m, req, who, at)
        r["current"] = None
        r.setdefault("history", []).append(("withdraw", m, st.line, at))
        return say.withdrawn(m, req, who, at)

    # -- checks, trials, status
    def st_check(self, st):
        req = self.reqs.get(st.name)
        if self.kinds.get(st.name) == "measure":
            raise Refusal("G004", f"{st.name} is a measure; a check names a requirement and its adopted measure: 'check <R> by {st.name} on <data>'")
        self.need(st.name, "requirement")
        m = st.get("by")
        if m is not None:
            self.need(m, "measure")
        withdrawn = any(h[0] == "withdraw" and h[1] == m for h in req.get("history", []))
        if m is None or (req["current"] is None and m not in req["stale"] and not withdrawn):
            adopted = req["current"][0] if req["current"] else "none"
            raise Refusal("G002", f"check of {st.name} names no adopted measure, so it has no answer: write 'check {st.name} by <M> on <data>' with {st.name}'s adopted measure. Adopted for {st.name}: {adopted}")
        self.not_current(st.name, m, "check")
        return self.run(st, m, st.name, trial=False)

    def st_try(self, st):
        if self.kinds.get(st.name) == "requirement":
            raise Refusal("G004", f"{st.name} is a requirement's text; Reality does not judge a requirement's text. A trial names a measure: 'try <M> on <data>'")
        self.need(st.name, "measure")
        self.measures[st.name]["trials"].append(st.line)
        return self.run(st, st.name, self.measures[st.name]["req"], trial=True)

    def run(self, st, m, req, trial):
        ms, r = self.measures[m], self.reqs[req]
        on = st.get("on")
        if ms.get("parts"):
            return self.run_composite(st, m, req, trial, on)
        if isinstance(on, list):
            raise Refusal(
                "G024",
                f"{m} is a simple measure (one fragment); write 'check {req} by {m} on sha256:<data>' "
                f"(or 'try {m} on sha256:<data>'), not part bindings",
            )
        head = say.check_head(st.name if not trial else m, req, r["text"], r["owner"], m, ms, r["current"], trial, on[7:])
        if st.line < self.run_from:
            return head + [f"not run here (--run-from {self.run_from}); nothing is said here about {m} or {req}."]
        if self.runner is None:
            return head + ["NOT CHECKED: no checker was given to run the measure. Nothing follows about " + m + " or " + req + "."]
        return head + say.result(m, req, self.runner(ms["frag"], on[7:]), trial, ms["outside"])

    def run_composite(self, st, m, req, trial, on):
        ms, r = self.measures[m], self.reqs[req]
        parts = ms["parts"]
        want = {p["name"] for p in parts}
        if not isinstance(on, list):
            raise Refusal(
                "G024",
                f"{m} is a composite measure with parts {', '.join(sorted(want))}; "
                f"bind each part: '{' '.join(f'on {n} sha256:<data>' for n in sorted(want))}'",
            )
        got = {}
        for pname, h in on:
            if pname not in want:
                raise Refusal("G024", f"{m} has no part named {pname}; parts: {', '.join(sorted(want))}")
            if pname in got:
                raise Refusal("G024", f"part {pname} of {m} is bound twice in this check")
            got[pname] = h[7:]
        missing = sorted(want - set(got))
        if missing:
            raise Refusal("G024", f"composite check of {m} is missing data for part{'s' if len(missing) != 1 else ''} {', '.join(missing)}")
        # Head uses a digest of the bound inputs (not a single file).
        bind_fp = sha(("\n".join(f"{n}={got[n]}" for n in sorted(got)) + "\n").encode())
        head = say.check_head_composite(
            st.name if not trial else m, req, r["text"], r["owner"], m, ms, r["current"], trial, bind_fp, parts, got
        )
        if st.line < self.run_from:
            return head + [f"not run here (--run-from {self.run_from}); nothing is said here about {m} or {req}."]
        if self.runner is None:
            return head + ["NOT CHECKED: no checker was given to run the measure. Nothing follows about " + m + " or " + req + "."]
        part_results = []
        for p in parts:
            res = self.runner(p["frag"], got[p["name"]])
            part_results.append((p["name"], res))
        return head + say.result_composite(m, req, part_results, trial, ms["outside"])

    def st_status(self, st):
        if self.kinds.get(st.name) == "refused":
            self.need(st.name, "requirement")
        if self.kinds.get(st.name) != "requirement":
            raise Refusal("G004", f"'status' names a requirement; {st.name} is " + (f"a {self.kinds[st.name]}" if st.name in self.kinds else "not declared"))
        r = self.reqs[st.name]
        status = "ADOPTED" if r["current"] else ("PROPOSED" if r["measures"] else "OFFERED")
        return say.status(st.name, r["text"], status, self.listing(st.name))
