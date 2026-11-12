"""Every sentence Reality prints about requirements (req/SPEC.md section 6). Trusted.

Requirement texts and descriptions appear only inside double quotes, through q(). The verdict
words are HOLDS, DOES NOT HOLD and NOT CHECKED, always with the measure's name. Nothing here
says that a requirement is met, kept or achieved.
"""


def q(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def short(h):
    return f"sha256:{h[:8]}...{h[-4:]}"


def refused(code, msg):
    return f"{code} refused: {msg}"


def summary(n):
    return "every statement formed" if n == 0 else f"refused ({n} statement{'s' if n != 1 else ''} cannot be formed)"


def declared(kind, name):
    return f"{kind} {name}" + (": can propose measures, never own a requirement or adopt a measure" if kind == "tool" else "")


def offered(name, text, owner):
    return [f"requirement {name} recorded, OFFERED: {q(text)} (owner {owner})",
            f"Reality does not read this text. {name} cannot be delivered or checked until {owner} adopts a measure for it."]


def proposed(m, req, by, kind, says, outside, fp, n):
    out = [f"measure {m} proposed for {req} by {by} ({kind}), {short(fp)}, {n} condition{'s' if n != 1 else ''}; not adopted",
           f"the proposer's description (plain text, not checked; units in it are not checked): {q(says)}"]
    if outside:
        out.append(f"computed outside the checker, not checked: {q(outside)}")
    return out


def proposed_composite(m, req, by, kind, says, outside, fp, parts, n):
    names = ", ".join(p["name"] for p in parts)
    out = [
        f"measure {m} proposed for {req} by {by} ({kind}), {short(fp)}, composite "
        f"({len(parts)} parts: {names}), {n} condition{'s' if n != 1 else ''} across parts; not adopted",
        f"the proposer's description (plain text, not checked; units in it are not checked): {q(says)}",
    ]
    for p in parts:
        out.append(f"  part {p['name']}: fragment {q(p['path'])} {short(p['fp'])}")
    if outside:
        out.append(f"computed outside the checker, not checked: {q(outside)}")
    return out


def task_propose(t, req, who):
    return [f"task {t} formed: {who} proposes measures for {req}",
            f"done when a measure for {req} proposed by {who} is recorded; that does not adopt it"]


def task_deliver(t, req, m, data, who):
    return [f"task {t} formed: {who} delivers {req} by {m} on {short(data)}",
            f"done when 'check {req} by {m} on sha256:{data}' gives HOLDS; that is a statement about {m}"]


def g001(t, req, text, listing):
    return (f"task {t} assigns {req} ({q(text)}) as work with a done-condition, but {req} has no adopted measure, so nothing "
            f"decides when it is done. Measures for {req}: {listing}. A task whose output is proposed measures forms: "
            f"'task {t} = propose {req} assigned_to <who>'")


def g014(line, req, m, rfp, mfp, rnow, mnow):
    return (f"the adoption on line {line} was for {req}'s text sha256:{rfp} and {m}'s fragment sha256:{mfp}; they are now "
            f"sha256:{rnow} and sha256:{mnow}. A changed text or measure is not the one adopted")


def payload(word, req, rfp, m, mfp, who, at):
    first = "reality-adopt 1" if word == "adoption" else "reality-withdraw 1"
    return f"{first}\nrequirement {req} sha256:{rfp}\nmeasure {m} sha256:{mfp}\nby {who}\nat {at}\n".encode("utf-8")


def adopted(m, req, who, at, trials):
    return [f"{m} ADOPTED for {req} by {who} at {q(at)}; signature checked against {who}'s key in the allowed_signers file",
            f"{len(trials)} trial run{'s' if len(trials) != 1 else ''} of {m} before adoption" + (f" (line{'s' if len(trials) != 1 else ''} {', '.join(map(str, trials))})" if trials else "")]


def withdrawn(m, req, who, at):
    return [f"{m} WITHDRAWN for {req} by {who} at {q(at)}; signature checked. {req} has no adopted measure now",
            f"checks made under {m} stay statements about {m}"]


def check_head(subject, req, text, owner, m, ms, current, trial, data):
    if trial:
        first = f"TRIAL of {m} on {short(data)}: {m} is not adopted for {req}, and this says nothing about {req}."
        if current and current[0] == m:
            first = f"TRIAL of {m} on {short(data)}: a trial changes nothing, and says nothing about {req}."
    else:
        first = f"check {req} by {m} on {short(data)}"
    return [first,
            f"requirement {req}: {q(text)} (owner {owner})",
            f"measure {m}: {short(ms['fp'])}, proposed by {ms['by']}" + (f", adopted on line {current[1]}" if current and current[0] == m else "")]


def check_head_composite(subject, req, text, owner, m, ms, current, trial, bind_fp, parts, got):
    if trial:
        first = f"TRIAL of {m} (composite) on bindings {short(bind_fp)}: {m} is not adopted for {req}, and this says nothing about {req}."
        if current and current[0] == m:
            first = f"TRIAL of {m} (composite) on bindings {short(bind_fp)}: a trial changes nothing, and says nothing about {req}."
    else:
        first = f"check {req} by {m} (composite) on bindings {short(bind_fp)}"
    out = [first,
           f"requirement {req}: {q(text)} (owner {owner})",
           f"measure {m}: {short(ms['fp'])}, proposed by {ms['by']}" + (f", adopted on line {current[1]}" if current and current[0] == m else "")]
    for p in parts:
        out.append(f"  part {p['name']} on {short(got[p['name']])}")
    return out


def result(m, req, res, trial, outside):
    out = []
    if outside:
        out.append(f"computed outside the checker, not checked: {q(outside)}")
    for n, v in res["shown"]:
        out.append(f"  fragment line {n}: {v}")
    if res["verdict"] == "NOT CHECKED":
        return out + [f"{m} was NOT CHECKED on this data: {res['why']}", f"Nothing follows about {m} or {req}."]
    for n, msg in res["failed"]:
        out.append(f"  fragment line {n} does not hold: {msg}")
    if res["verdict"] == "HOLDS":
        out.append(f"{m} HOLDS on this data: {res['held']} of {res['total']} conditions hold.")
    else:
        out.append(f"{m} DOES NOT HOLD on this data: {res['held']} of {res['total']} conditions hold, {res['total'] - res['held']} {'does' if res['total'] - res['held'] == 1 else 'do'} not.")
    if not trial:
        out.append(f"This is a statement about {m} on this data. Reality did not decide whether {m} is the right measure "
                   f"for {req}'s text; the owner's adoption did.")
    return out


def result_composite(m, req, part_results, trial, outside):
    """AND over parts: any NOT CHECKED → overall NOT CHECKED; else any DOES NOT HOLD → DOES NOT HOLD; else HOLDS."""
    out = []
    if outside:
        out.append(f"computed outside the checker, not checked: {q(outside)}")
    verdicts = []
    for pname, res in part_results:
        out.append(f"  part {pname}:")
        for n, v in res.get("shown") or []:
            out.append(f"    fragment line {n}: {v}")
        if res["verdict"] == "NOT CHECKED":
            out.append(f"    {pname} was NOT CHECKED: {res['why']}")
            verdicts.append("NOT CHECKED")
            continue
        for n, msg in res.get("failed") or []:
            out.append(f"    fragment line {n} does not hold: {msg}")
        if res["verdict"] == "HOLDS":
            out.append(f"    {pname} HOLDS: {res['held']} of {res['total']} conditions hold.")
            verdicts.append("HOLDS")
        else:
            out.append(
                f"    {pname} DOES NOT HOLD: {res['held']} of {res['total']} conditions hold, "
                f"{res['total'] - res['held']} do not."
            )
            verdicts.append("DOES NOT HOLD")
    if "NOT CHECKED" in verdicts:
        overall = "NOT CHECKED"
        out.append(f"{m} was NOT CHECKED as a composite: at least one part was NOT CHECKED.")
        out.append(f"Nothing follows about {m} or {req}.")
    elif "DOES NOT HOLD" in verdicts:
        overall = "DOES NOT HOLD"
        held = sum(1 for v in verdicts if v == "HOLDS")
        out.append(f"{m} DOES NOT HOLD as a composite: {held} of {len(verdicts)} parts hold, {len(verdicts) - held} do not.")
    else:
        overall = "HOLDS"
        out.append(f"{m} HOLDS as a composite: all {len(verdicts)} parts hold.")
    if not trial and overall != "NOT CHECKED":
        out.append(
            f"This is a statement about composite measure {m} on these bound inputs. "
            f"Reality did not decide whether {m} is the right measure for {req}'s text; the owner's adoption did."
        )
    return out


def status(name, text, st, listing):
    return [f"{name} is {st}: {q(text)}", f"measures: {listing}"]
