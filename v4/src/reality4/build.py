"""The certificate inputs' bytes (moved verbatim from decide.py, unit BLD; BB's call on Patsak's behalf 29 Oct 2026,
reversible: the trusted base shrinks only by what a checker re-checks). Model.bytes_of and what only it calls: each
slot's table, raw file, NIfTI header, JSON text, and a dataset's participants, recordings, sidecars and events files.
Untrusted: every input they build is read by the real readers and evaluator (Decide.run -> witness.evaluate), after
Decide.run has checked it is a content-addressed store (each byte blob's key its sha256; a lazily held file only one
of the trusted Periodic classes), and a form needs the real answers to differ (Decide.w2, Decide.w1's pairs,
Decide.d_confirm); a wrong input is X001 (fault) or R013 (Big), never a wrong form. Its loops are still charged or
named (tests/test_v4_loops.py scans it)."""
from . import decide as D   # the model's names, bounds and helpers, read through decide (so its bounds and patches hold here)


def bytes_of(self, case, x, seed=0):
    """The certificate input (SPEC-EXACT 6): each slot's table, the named rows at their positions
    and the unnamed ones (each type's n_t rows, in the order of the types) in the other places. Its rows are held
    while they are built (type_rows; SPEC-EXACT 8)."""
    self.cheld = [0]
    try:
        return self.bytes_of1(case, x, seed)
    finally:
        D.MEM[0] -= self.cheld[0]


def bytes_of1(self, case, x, seed):
    out = {s: self.file_bytes(s, case, x, seed) for s in self.names if s not in self.tabs}
    for s in self.tabs:
        c = case[s]
        d = len(c.types) + 1
        named = [self.row(s, t, 1 + i + seed * d, x, i) for i, t in enumerate(c.types)]
        tr = [(t, r) for t in self.types[s] for r in self.type_rows(s, t, x, case)]
        fill, fty = named[c.h:] + [r for _, r in tr], list(c.types[c.h:]) + [t for t, _ in tr]
        rows, rty, j = [], [], 0   # rty: each row's type (R2)
        for p in range(1, c.h + len(fill) + 1):
            if j < c.h and p == c.pos[j]:
                rows.append(named[j])
                rty.append(c.types[j])
                j += 1
            else:
                rows.append(fill[p - 1 - j])
                rty.append(fty[p - 1 - j])
        hdr = {k: self.htext(k, cl, seed, x.get(("z", "cell", s, "h", k))) for k, cl in c.hdr.items()}
        if s in self.tw and s in self.sl:   # (3.13h) beside a size(): each row at its least line, the first header name padded
            out[s] = self.stext(s, rty, x.get(("n", s, "size"), 0) if s in self.st else None, seed, self.lay_of(s, case, x) if s in self.lay else case[s].wc if case[s].wc != "o" else self.wo[s])
            continue
        if s in self.tw:   # (shape 1, 3.13) a bare table of the case's width: a line literal's pieces, others' cells unlike them
            rows, W0 = self.tw_rows(s, case[s].wc, rows, rty, seed), case[s].wc if case[s].wc != "o" else self.wo[s]
            hdr = {**hdr, 2: self.htext(2, ("oth", None, None), seed)} if s in self.tn and W0 >= 2 and seed else hdr   # (3.13d) the header's spelling moves on
            out[s] = self.table(s, rows, hdr, True, W0)
            continue
        if self.rb and s in self.rl:   # (G04) past a Past, near the read limit: the least table rlb counts
            out[s] = self.least_table(s, rows, rty, hdr)
            continue
        out[s] = self.stext(s, rty, x.get(("n", s, "size"), 0) if s in self.st else None, seed, self.lay_of(s, case, x) if s in self.lay else None) if s in self.sl else self.table(s, rows, hdr)
        if self.kind[s] == "pt":   # item 2b: the dataset around it: a T1w image per participant (witness._dataset); R2: its recordings
            out[s] = self.rs_dataset(s, case, x, out[s], rty) if s in self.rs else self.rec_dataset(s, self.rc(s, case), x, out[s], rty) if s in self.recs else _dataset({"subs": [ln.split("\t")[0][4:] for ln in out[s].decode("utf-8").split("\n")[1:-1]], "recs": [], "ids": []}, out[s], {})
    return out


def file_bytes(self, s, case, x, seed):
    """A raw file of its size (bytes moved on by the seed), a NIfTI header with the case's dims
    (NIfTI-1 when they fit int16, else NIfTI-2), or a JSON text built from the case (SPEC-EXACT 6)."""
    if self.kind[s] == "raw":
        n = x.get(("n", s, "size"), 0)
        if s not in self.rreg:
            return D.W.Periodic(n, seed)
        ov = [(o, (rspell(k, x[("z", "raw", s, o, k)]) or "?" * k if cl == "num" else "ab"[seed % 2] * k).encode("ascii"))
              for (o, k), cl in zip(self.rreg[s], case[s]) if o + k <= n]   # (shape 3) each range's spelling ("?": none, so confirmation fails)
        return D.RawFile(n, seed, ov)
    if self.kind[s] == "rec":
        return self.rec_dataset(s, case[s], x)
    if self.kind[s] == "rs":
        return self.rs_dataset(s, case, x)
    if s in self.nr:   # (3.10) the header padded to the size: plain, or a gzip member and zero bytes (as gzip.open reads it)
        dims, n = [x.get(("n", s, "dim", k), 1) for k in range(1, case[s] + 1)], x.get(("n", s, "size"), 544)
        h = D.W._nii(dims, 1, data=False) if max(dims) <= 32767 and case[s].z != "n2" else nii2(dims, 1, 8)
        if case[s].z != "gz":
            return D.NiiFile(h, n, seed)
        c = D.zlib.compressobj(9, D.zlib.DEFLATED, -15)
        g = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff" + c.compress(h) + c.flush() + D.struct.pack("<2I", D.zlib.crc32(h), len(h))
        if n < len(g):
            raise D.Big(f"a certificate's gzip NIfTI header takes {len(g)} bytes; a smaller file is not built (SPEC-EXACT 3.10)")
        return g + bytes(n - len(g))
    if self.kind[s] == "nifti":
        dims = [x.get(("n", s, "dim", k), 1) for k in range(1, case[s] + 1)]
        u = getattr(case[s], "unit", None)   # (f) with pixdim(): NIfTI-2, the case's unit and pixdim[4]
        u, t = 8 if u is None else u, float(x.get(("z", "pix", s), 1))
        if max(dims) <= 32767 and u == 8 and s not in self.pix:
            return D.W._nii(dims, t, unit=u, data=False)
        return nii2(dims, t, u)
    return self.jtext(s, case[s], x, seed, ()).encode("utf-8")


def type_rows(self, s, t, x, case):
    """The n_t unnamed rows of type t: each class's spelling 0; in a summed column, decimals that add
    up to the type's sum; in an ordered column, a decimal in each row's piece (SPEC-EXACT 6)."""
    n, X = x.get(("n", s, t), 0), case[None]
    D.hold(self.cheld, self.cheld[0] * D.STEP_BYTES + n * (64 + 8 * (self.width[s] + 1)))   # the rows' lists, then each column's values and texts
    rows = [["p"] * (self.width[s] + 1) for _ in range(n)]
    for k in self.cols[s]:
        c = self.cls(s, t, k)
        r, vals = self.rindex(s, k, c), [None] * n
        if n and self.agg.get((s, k)) == "both" and (s, k, r) in X.nw and t in X.sel.get((s, k), ()) and (s, t) in X.sums:
            ws = [c[1][0]] + [x.get(("z", "w", s, k, r, i), D.inside(*c[1], self.pay)) for i in range(X.nw[(s, k, r)])] + [c[1][1]]
            vals = []   # (e2) each piece's rows: at its w, or decimals between its ends adding up to its sum
            for i in range(2 * len(ws) - 3):
                q = x.get(("p", s, t, k, r, i), 0)
                v = [(ws[i // 2 + 1], q)] if i % 2 else split(x.get(("z", "ps", s, t, k, r, i), 0), q, ws[i // 2], ws[i // 2 + 1], self.pay) if q else []
                vals = None if v is None or vals is None else vals + [u for u, mm in v for _ in range(mm)]
        elif n and ("z", "y", s, t, k) in x:   # no rows: sum 0 (item 8); a point 5.4 moved off a solution: n rows of c's value
            vals = self.realize(s, t, k, x, n) if self.inside_sum((s, t), x) else split(n * c[2], n, *c[1], self.pay)
            vals = vals and [v for v, m in vals for _ in range(m)]
        elif (s, k, r) in X.nw and t in X.sel.get((s, k), ()):
            ws = [c[1][0]] + [x.get(("z", "w", s, k, r, i), D.inside(*c[1], self.pay)) for i in range(X.nw[(s, k, r)])] + [c[1][1]]
            vals = [ws[i // 2 + 1] if i % 2 else D.inside(ws[i // 2], ws[i // 2 + 1], self.pay) for i in range(2 * len(ws) - 3) for _ in range(x.get(("p", s, t, k, r, i), 0))]
        if vals is None or any(v is not None and not D.in_r(v) for v in vals) or (None in vals and vals != [None] * n):
            raise D.Big("a value the system allows only between ends closer than the numbers the reader reads (at most 1000 digits; P1, SPEC-EXACT 3.1)")
        D.hold(self.cheld, self.cheld[0] * D.STEP_BYTES + sum(D.num(D.bits([v])) for v in vals if v is not None))
        for row, v in zip(rows, vals):
            row[k - 1] = self.text(s, k, c, 0, v)
        D.hold(self.cheld, self.cheld[0] * D.STEP_BYTES + sum(49 + len(row[k - 1]) for row in rows))
    return rows


def realize(self, s, t, k, x, n):
    """n readable numbers of t's class in column k summing to its y at x (its parts' when it has parts), as runs, or None."""
    c, ps = self.cls(s, t, k), self.parts.get((s, t, k))
    if not ps or sum(x.get(("q", s, t, k, p), 0) for p in range(len(ps))) != n:
        return split(x.get(("z", "y", s, t, k), 0), n, *c[1], self.pay)
    out, B, ends = [], self.cbands((s, t, k)), {}
    for p, (i, j) in enumerate(ps):
        q = x.get(("q", s, t, k, p), 0)
        if q and i == j:
            d, r = divmod(x.get(("k", s, t, k, p), 0), q)
            out += [(B[i][0] * (B[i][1] + d + 1), r), (B[i][0] * (B[i][1] + d), q - r)]
        elif q:
            ends[p] = (q, B[i][0] * B[i][1], B[j][0] * B[j][2])
    left = x.get(("z", "yp", s, t, k), 0) - sum(q * a for q, a, _ in ends.values())
    for p, (q, a, b) in ends.items():   # the parts of more bands: each its least sum, and what is left in turn
        v = q * a + min(left, q * (b - a))
        left -= v - q * a
        v = split(v, q, D.prv(a), D.nxt(b), self.pay)
        if v is None:
            return None
        out += v
    return out


def rs_dataset(self, s, case, x, ptsv=None, rty=None):
    """(R1) a dataset: per task, its regions in the case's order, each region's recordings with its refusing kinds first
    in its order, then the answering ones; each a BOLD image (bold()), its sidecar and, by kind, its events file: a 3-D
    image (V008), no events file (V007), no trial_type column (V002). Without participants.tsv a subject per recording;
    with it (R2) a region's recordings are one participant's runs (a row of its types; the labels sort as the regions),
    and every other participant a T1w image. The answering recordings carry the sum's values (split: n - 1 equal and the
    rest), a min's one value, or a max's one value and the least others (SPEC-EXACT 3.9)."""
    files = {"dataset_description.json": b'{"Name": "certificate", "BIDSVersion": "1.0.1"}', "README": b"certificate\n"}
    q, lit = self.rsq.get(s, ("tr", None))
    fs, c = {y.fn for y in self.rsagg if y.args[0].args[0].args[0].id == s}, case[("rs", s)]
    lab, i, tot = {}, 0, 0
    for t in sorted(self.rs[s]) if ptsv else ():   # each region's participant: the first row of its types
        for r, _ in c[t][0]:
            lab.setdefault(next((j for j, ty in enumerate(rty) if ty in self.rsreg[(s, t)][r]), None), None)
    lab = {j: f"a{k:07d}" for k, j in enumerate(lab)}
    car = {}
    if s in self.rs8:   # (3.9d) a one-row region's participant carries both tasks' recordings there; two or more: one each, labels in an order both tasks' sort
        chains = []
        for ti, t in enumerate(sorted(self.rs[s])):
            ch = []
            for r, _ in c[t][0]:
                rows = [j for j, ty in enumerate(rty) if ty in self.rsreg[(s, t)][r]]
                car[(t, r)] = rows[0 if c[t][3][r] == 1 or len(rows) < 2 else ti] if rows else None
                ch += [car[(t, r)]] if rows else []
            chains.append(ch)
        lab = {j: f"a{k:07d}" for k, j in enumerate(merge_chains(chains))}
    if ptsv and 1 in self.cols[s]:   # item 4: the labels are the table's own (participant_id read)
        lab = {j: ln.split("\t")[0][4:] for j, ln in enumerate(ptsv.decode("utf-8").split("\n")[1:-1])}
    tots = {"volumes": 0, "ev": 0}
    for t in sorted(self.rs[s]):
        for r, ks in c[t][0]:
            if s in self.rsm:   # (3.9a)
                i = self.rs_recs2(s, t, r, ks, c, x, files, lab, rty if ptsv else None, i, tots)
                continue
            n = {k: x.get(("n", s, "rs", t, k, r), 0) for k in ("ok",) + D.RSBAD[q]}
            if sum(n.values()) > D.MAX_ROWS:
                raise D.Big(f"a certificate needs more than {D.MAX_ROWS} recordings (SPEC-EXACT 3.9)")
            vals, p = [None] * n["ok"], c[t][1][r] == "p"
            if p and (s, t) in self.rs7:   # (3.9e) the region's values: its sum y and its max or min m, as many recordings as they need
                m, y = int(x.get(self.rs_var(s, t, "m", r), 0)), int(x.get(self.rs_var(s, t, "y", r), 0))
                if self.rs7[(s, t)] == "min":
                    vals = [m] if c[t][4][r] == 0 else [m, y - m]
                else:
                    k = max(1, -(-y // m)) if m else 1
                    if k + sum(n.values()) - n["ok"] > D.MAX_ROWS:   # (G04c) before the list: a witness's y / m can be past any memory
                        raise D.OverRows(f"a certificate needs more than {D.MAX_ROWS} recordings (SPEC-EXACT 3.9)")
                    vals = [m] + W_split_int(y - m, k - 1) if k > 1 else [m]
                n["ok"] = len(vals)
                if sum(n.values()) > D.MAX_ROWS:
                    raise D.OverRows(f"a certificate needs more than {D.MAX_ROWS} recordings (SPEC-EXACT 3.9)")
            elif p and fs & {"min", "max"}:   # min: all at m; max: one at m, the others at the least value
                m = x.get(self.rs_var(s, t, "m", r), 0)
                vals = [m] * n["ok"] if fs != {"max"} or q == "tr" else [m] + [0 if q != "volumes" else 1] * (n["ok"] - 1)
            elif p and fs & {"sum", "mean"}:
                y = D.Fraction(x.get(self.rs_var(s, t, "y", r), 0))
                if q == "tr":
                    runs = split(y, n["ok"], D.TRLO, D.TRHI, self.pay)
                    if runs is None:
                        raise D.Big("a value the system allows only between ends closer than the numbers the reader reads (at most 1000 digits; P1, SPEC-EXACT 3.1)")
                    vals = [v for v, k in runs for _ in range(k)]
                else:
                    vals = W_split_int(y, n["ok"])
            tot += sum(vals) if q != "tr" and vals and vals[0] is not None else 0
            if tot > (D.MAX_VOL if q == "volumes" else D.MAX_ROWS):
                raise (D.Big if q == "volumes" else D.OverRows)(f"a certificate needs more than {D.MAX_ROWS} events or {D.MAX_VOL} volumes in all (SPEC-EXACT 3.9)")
            row = car[(t, r)] if (t, r) in car else next((j for j, ty in enumerate(rty) if ty in self.rsreg[(s, t)][r]), None) if ptsv else None
            for k in ks + ("ok",):
                for j in range(n[k]):
                    i += 1
                    v = vals[j] if k == "ok" else None
                    sub = lab[row] if ptsv else f"{i:07d}"
                    stem = "sub-{0}/func/sub-{0}_task-{1}".format(sub, t) + (f"_run-{i:07d}" if ptsv else "")
                    tr = v if q == "tr" and v is not None else D.Fraction(1)
                    nv = v if q == "volumes" and v is not None else 1
                    files[stem + "_bold.nii"] = bold(tr, nv, k != "3d")
                    if D.dec_seq(tr, 0) is None:
                        raise D.Big("a certificate value has no decimal the reader reads (P1, SPEC-EXACT 3.1)")
                    files[stem + "_bold.json"] = ('{"TaskName": "%s", "RepetitionTime": %s}' % (t, D.dec_seq(tr, 0))).encode()
                    if k == "noev":
                        continue
                    ne = v if q in ("events", "trials") and v is not None else 0
                    if q == "trials" and k == "ok":
                        body = "onset\tduration\ttrial_type\n" + f"0\t1\t{lit.decode('utf-8')}\n" * ne
                    else:
                        body = "onset\tduration\n" + "0\t1\n" * ne
                    files[stem + "_events.tsv"] = (body[:-1] if self.rb else body).encode("utf-8")   # (G04c) rs_evlb
    if ptsv:
        lines = ptsv.decode("utf-8").split("\n")
        for j in range(len(rty)):
            sub = lab.get(j, f"b{j:07d}")
            lines[j + 1] = "sub-" + sub + lines[j + 1][lines[j + 1].index("\t"):]
            if not any(f.startswith(f"sub-{sub}/") for f in files):
                files[f"sub-{sub}/anat/sub-{sub}_T1w.nii"] = D.W._nii((1, 1, 1), 1)
        files["participants.tsv"] = "\n".join(lines).encode("utf-8")
    blobs = {D.hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (D.R.MANIFEST_MAGIC + "\n" + "".join(f"{D.hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[D.hashlib.sha256(man).hexdigest()] = man
    return blobs, D.hashlib.sha256(man).hexdigest()


def rs_recs2(self, s, t, r, ks, c, x, files, lab, rty, i, tots):
    """(3.9a, 3.9b) region r's recordings when two or more quantities are read: per kind (J) as many recordings as the
    solution says, ordered by the events file's kind as the case's order (ks), then the answering; volumes split over
    the 4-D images (W_split_int); per events-file class its quantities' sums split over its recordings, trials of each
    type as rows of that type, and events beyond the trials (a file with a trial_type column) as filler rows on its
    first recording, of a type no read type looks like. The next recording number."""
    Q, st = self.rsm[s], c[t][1][r]
    n = {J: x.get(("n", s, "rs", t, J, r), 0) for J in self.rs_jk(s)}
    if sum(n.values()) > D.MAX_ROWS:
        raise D.Big(f"a certificate needs more than {D.MAX_ROWS} recordings (SPEC-EXACT 3.9)")
    qs, val = self.rsqs(s), lambda key: int(x.get(self.rs_var(s, t, "y", r, key), 0))   # noqa: E731
    lits = [lit for q, lit in Q if q == "trials"]
    fill = next(f for f in D.fills(("z", "y", "x", "w", "v")) if all(D.skeleton(f) != D.skeleton(b.decode("utf-8")) for b in lits))
    order = list(ks) + [k for k in ("noev", "nocol") if k not in ks] + ["ok"]
    recs = [J for J in sorted(n, key=lambda J: (order.index(self.rs_cls(s, J)), J)) for _ in range(n[J])]
    iv = next((j for j, (q, _) in enumerate(Q) if q == "volumes"), None)
    vols = iter(W_split_int(val(iv), sum(1 for J in recs if J[iv] == "ok")) if iv is not None and any(J[iv] == "ok" for J in recs) else [])
    ev = {}   # per recording index: (events rows of no read type, {lit: rows})
    for ci, cl in enumerate(self.rs_evc(s)):
        idx = [k for k, J in enumerate(recs) if self.rs_cls(s, J) == cl]
        if not idx or st == "e" or st[ci] != "p":
            continue
        tr = {lit: W_split_int(val((j, "ok")), len(idx)) if cl == "ok" else [0] * len(idx) for j, (q, lit) in enumerate(Q) if q == "trials"}
        ie = next((j for j, (q, _) in enumerate(Q) if q == "events"), None)
        if ie is None:
            extra = [0] * len(idx)
        elif cl == "ok" and lits:
            extra = [val((ie, "ok")) - sum(val((j, "ok")) for j, (q, _) in enumerate(Q) if q == "trials")] + [0] * (len(idx) - 1)
        else:
            extra = W_split_int(val((ie, cl)), len(idx))
        for m, k in enumerate(idx):
            ev[k] = (extra[m], {lit: v[m] for lit, v in tr.items()})
    row = next((j for j, ty in enumerate(rty) if ty in self.rsreg[(s, t)][r]), None) if rty is not None else None
    for k, J in enumerate(recs):
        i += 1
        nv = next(vols) if iv is not None and J[iv] == "ok" else 1
        extra, tt = ev.get(k, (0, {}))
        tots["volumes"] += nv if iv is not None and J[iv] == "ok" else 0
        tots["ev"] += extra + sum(tt.values())
        if tots["volumes"] > D.MAX_VOL or tots["ev"] > D.MAX_ROWS:
            raise (D.OverRows if tots["ev"] > D.MAX_ROWS else D.Big)(f"a certificate needs more than {D.MAX_ROWS} events or {D.MAX_VOL} volumes in all (SPEC-EXACT 3.9)")
        sub = lab[row] if rty is not None else f"{i:07d}"
        stem = "sub-{0}/func/sub-{0}_task-{1}".format(sub, t) + (f"_run-{i:07d}" if rty is not None else "")
        files[stem + "_bold.nii"] = bold(D.Fraction(1), nv, iv is None or J[iv] != "3d")
        files[stem + "_bold.json"] = ('{"TaskName": "%s", "RepetitionTime": 1}' % t).encode()
        cl = self.rs_cls(s, J)
        if cl == "noev":
            continue
        if cl == "ok" and lits:
            body = "onset\tduration\ttrial_type\n" + "".join(f"0\t1\t{lit.decode('utf-8')}\n" * v for lit, v in tt.items()) + f"0\t1\t{fill}\n" * extra
        else:
            body = "onset\tduration\n" + "0\t1\n" * extra
        files[stem + "_events.tsv"] = body.encode("utf-8")
    return i


def rec_dataset(self, s, c, x, ptsv=None, rty=None):
    """(2c) a dataset: per named recording that is there, its BOLD image (NIfTI-2, dims 1 x 1 x 1 [x volumes], a
    byte per voxel; pixdim[4] the float64 nearest to tr in s, or in us below 2^-1075 s), its sidecar (3.8a: in the folder
    rdep gives, above every named recording whose labels hold its own, so theirs override it) and its events file (row
    i at its onset, others at 0, durations 1); volumes x tr above every onset (SPEC-EXACT 3.8). (3.8b) With
    participants.tsv (ptsv, its rows' types rty): each recording's subject is a row, its literal's or a row whose label
    is no literal (any row when participant_id is not read) relabelled sub-L; a made-up label that looks like one moves
    on; every other row a T1w image."""
    files = {"dataset_description.json": b'{"Name": "certificate", "BIDSVersion": "1.0.1"}', "README": b"certificate\n"}
    if ptsv is not None:
        lines, subs = ptsv.decode("utf-8").split("\n"), {dict(E)["sub"] for E in c}
        labs, there = [ln.split("\t", 1)[0] for ln in lines[1:-1]], sorted({dict(E)["sub"] for E, st in c.items() if st is not None})
        j0, lit = (self.cols[s].index(1) if 1 in self.cols[s] else None), set(self.lits.get((s, 1), ()))
        free = [j for j in range(len(labs)) if labs[j].encode() not in lit and (j0 is None or self.classes[(s, 1)][rty[j][j0]][0] == "oth")]
        for L in there:
            if "sub-" + L not in labs and free:   # the case's atoms leave a row for each (else B11: not confirmed, X001)
                labs[free.pop(0)] = "sub-" + L
        taken = {D.skeleton(t) for t in labs if t.encode() in lit or t[4:] in subs}
        for j, t in enumerate(labs):   # a made-up label that looks like a literal or a recording's subject moves on
            if t.encode() not in lit and t[4:] not in subs and D.skeleton(t) in taken:
                labs[j] = next(u for u in (f"sub-{a}{j + 1}" for a in D.fills("wvqxyz" + "abcdefghijkmnoprstu")) if D.skeleton(u) not in taken)
            taken.add(D.skeleton(labs[j]))
        files["participants.tsv"] = "\n".join([lines[0]] + [lab + ln[ln.index("\t"):] if "\t" in ln else lab for lab, ln in zip(labs, lines[1:-1])] + [""]).encode("utf-8")
        for t in labs:
            if t[4:] not in there:
                files[f"{t}/anat/{t}_T1w.nii"] = D.W._nii((1, 1, 1), 1)
    for E, st in c.items():
        if st is None:
            continue
        e = dict(E)
        I = self.rrows(s, E)
        ons = {i: x.get(("z", "on", s, E, i), D.Fraction(0)) for i in I[:st[1] or 0]}
        dus = {i: x.get(("z", "du", s, E, i), D.Fraction(1)) for i in I[:st[1] or 0]}
        K = {v[4]: x.get(v, 0) for v in self.rtt(s, E)} if st[2] else {}   # trials() read and a trial_type column
        mo, v = max(ons.values(), default=0), x.get(("n", s, "vol", E))   # item 3: volumes read: tr above the onsets / volumes
        tr = x.get(("z", "tr", s, E), (max(D.Fraction(1), mo + 1) if mo < D.TRHI - 1 else D.TRHI - 1) if v is None or not ons else D.inside(max(D.TRLO, mo / (v if st[0] else 1)), D.TRHI, self.pay))
        if tr is None:
            raise D.Big("a value the system allows only between ends closer than the numbers the reader reads (at most 1000 digits; P1, SPEC-EXACT 3.1)")
        v = max([1] + [D.floor(o / tr) + 1 for o in ons.values()]) if v is None else v
        if v > D.MAX_VOL:
            raise D.Big(f"a certificate's BOLD image needs more than {D.MAX_VOL} volumes (SPEC-EXACT 3.8)")
        stem = "sub-{0}/func/sub-{0}_task-{1}".format(e["sub"], e["task"]) + "".join(f"_{k}-{e[k]}" for k in ("acq", "rec", "run") if k in e)
        files[stem + "_bold.nii"] = bold(tr, v, st[0])
        t = D.dec_seq(tr, 0)
        if t is None or any(D.dec_seq(o, 0) is None for o in list(ons.values()) + list(dus.values())):
            raise D.Big("a certificate value has no decimal the reader reads (P1, SPEC-EXACT 3.1)")
        side = ["", f"sub-{e['sub']}/", f"sub-{e['sub']}/func/"][self.rdep[(s, E)]] + stem.rsplit("/", 1)[1]   # (3.8a) above the recordings it is inherited by
        files[side + "_bold.json"] = ('{"TaskName": "%s", "RepetitionTime": %s}' % (e["task"], t)).encode()
        if st[1] is not None:   # item 3: as many rows as events() says (else the last named row), trial types as trials() say
            n = x.get(("n", s, "ev", E), max([I[st[1] - 1] if st[1] else 0, sum(K.values())]))
            if n > D.MAX_ROWS:   # (G04c) a Past: decided again with the events files' read limit
                raise D.OverRows(f"a certificate's events file needs more than {D.MAX_ROWS} rows (SPEC-EXACT 3.8)")
            col = bool(K)   # a trial_type column: the type's rows, then rows of a type that looks like none of them
            tts = [b.decode("utf-8") for b, k in sorted(K.items()) for _ in range(k)]
            fl = (f for f in D.itertools.chain(["z", "y", "x", "w", "v"] if self.rb else [], (f"n{j}" for j in D.itertools.count())) if all(D.skeleton(f) != D.skeleton(b.decode("utf-8")) for b in K))
            tts += [next(fl)] * (n - len(tts)) if col else []   # (G04c) in the read-limit pass a one-letter type, the last line feed dropped (evlb)
            ev = (("onset\tduration\ttrial_type\n" if col else "onset\tduration\n") + "".join(
                f"{D.dec_seq(ons[i], 0) if i in ons else '0'}\t{D.dec_seq(dus[i], 0) if i in dus else '1'}" + (f"\t{tts[i - 1]}" if col else "") + "\n" for i in range(1, n + 1)))
            files[stem + "_events.tsv"] = (ev[:-1] if self.rb else ev).encode("utf-8")
    blobs = {D.hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (D.R.MANIFEST_MAGIC + "\n" + "".join(f"{D.hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files))).encode()
    blobs[D.hashlib.sha256(man).hexdigest()] = man
    return blobs, D.hashlib.sha256(man).hexdigest()


def jtext(self, s, c, x, seed, path):
    """The JSON text of one node: named members that are there, arrays as long as the case says
    (other items 0), numbers from the solution, strings and filler moved on by the seed."""
    k, kids = c.kind[path], sorted((q for q in c.kind if len(q) == len(path) + 1 and q[:-1] == path), key=repr)
    if k == "obj":
        items = [D.json.dumps(q[-1][1].decode("utf-8")) + ": " + self.jtext(s, c, x, seed, q) for q in kids if q[-1][0] == "m" and c.there.get(q)]
        named = {D.skeleton(q[-1][1].decode("utf-8")) for q in kids if q[-1][0] == "m"}   # (G09) the filler is no named member and looks like none
        fill = next(w for w in [""] + [chr(i) for i in range(97, 123)] + [f"f{i}" for i in range(len(named) + 1)] if D.skeleton(w) not in named)
        return "{" + ", ".join(items + ([f"{D.json.dumps(fill)}: {seed}"] if seed else [])) + "}"
    if k == "arr":
        h, ix = c.length.get(path, (0, []))
        byi = {q[-1][1]: q for q in kids if q[-1][0] == "i"}
        n = ix[h - 1] if h else 0
        more = seed and n + 1 not in ix   # one more item, where no named index sees it
        return "[" + ", ".join([self.jtext(s, c, x, seed, byi[i]) if i in byi else str(seed) for i in range(1, n + 1)] + ([str(seed)] if more else [])) + "]"
    if k == "num":
        return D.dec_seq(x.get(("z", "j", s, path), D.Fraction(0)), 0)
    if k == "str":
        return D.json.dumps(f"s{seed}.{sorted(c.kind, key=repr).index(path)}")
    return "null"


def least_table(self, s, rows, rty, hdr):
    """(G04) The table of these rows at the least text decide.Model.rlb counts: one-byte header names (a header cell the
    decision reads keeps its text), no extra column, each cell the least of its class (Model.cmin) or, in a column whose
    values the decision reads (an aggregate, a cell, number()), its value's least spelling (Model.vmin); the last line
    feed dropped. Untrusted: the reader and the evaluator check it (a wrong one is X001 or R013)."""
    w, csv = self.width[s], self.kind[s] == "csv"
    fixed = {k for k in self.cols[s] if (s, k) in self.agg or (s, k) in self.cells or ("cell", s, k) in self.num}
    q = lambda c: len(c.encode("utf-8")) + (2 + c.count('"') if csv and any(x in c for x in ',";\t') else 0)  # noqa: E731
    out = []
    for r, t in zip(rows, rty):
        cells = []
        for k in range(1, w + 1):
            c = self.cls(s, t, k) if k in self.cols[s] else ("oth", None, None)
            kk = k if k in self.cols[s] else None
            if k in fixed and c[0] in ("pt", "iv"):
                v = D.R.decimal(r[k - 1])
                cells.append(self.vmin(s, k, v) or r[k - 1])
                continue
            n, cell = self.cmin(s, kk, c, w == 1, q)
            if w == 1 and csv:
                n2, cell2 = self.cmin(s, kk, c, False, q, quoted=True)
                if n2 < n:
                    cell = "\0"   # '""' after writing
            cells.append(r[k - 1] if cell is None else cell)
        out.append(cells)
    fill = next(c for c in "abcdefghjkmnpqrstuvwxyz" if all(c != str(x) for x in hdr.values()))   # names need not differ (readers: non-empty)
    hs = {k: hdr.get(k, fill) for k in range(1, w + 1)}
    data = self.table(s, out, hs, True, w).replace(b"\0", b'""')
    return data[:-1] if out else data


def vmin(self, s, k, v):
    """(G04; SPL, from decide.py) The least spelling of the number v in column k that is no literal and looks like none
    (a least_table cell whose value the decision fixed). Untrusted: only least_table's bytes use it, and the reader and
    the evaluator check those (a wrong spelling is X001 or R013); the bound (Model.cmin, rlb) does not use it."""
    strs = {b.decode("utf-8") for b in self.lits.get((s, k), ())}
    sks = {D.skeleton(x) for x in strs}
    ell = D.dec_len(v)
    while ell is not None and ell <= 2 * D.DIG + 16:
        w = next((w for w in D.dec_spells(v, ell) if w not in strs and D.skeleton(w) not in sks), None)
        if w is not None:
            return w
        ell += 1
    return None


def stext(self, s, rty, n, seed, w=None):
    """(shape 2, 3.12) the table of these row types at exactly n bytes: one-byte header names, each row's least line,
    the last LF dropped (n is the least), or kept and the first header name padded; w: its width (3.12b)."""
    w = w or self.width[s]
    hs = [chr(97 + (i + seed) % 26) for i in range(w)]
    rows = [self.sline(s, t, True, w) for t in rty]
    if w == 1 and self.kind[s] == "csv":   # (3.12b) its quoted empty cells, as sline spells them
        rows = [["\0"] if r == ['""'] else r for r in rows]
    tb = lambda: self.table(s, rows, dict(enumerate(hs, 1)), True, w).replace(b"\0", b'""')  # noqa: E731
    n = len(tb()) - 1 if n is None else n   # (3.12a) a table beside one: its least
    d = n - len(tb()) + 1
    D.hold(self.cheld, self.cheld[0] * D.STEP_BYTES + 2 * max(n, 0))
    hs[0] += "z" * max(d - 1, 0)
    out = tb()
    return out[:-1] if d == 0 else out


def tw_rows(self, s, wc, rows, rty, seed=0):
    """(shape 1) rows of a file read by both readers in a table of csv width wc ('o': self.wo): a row whose line is a
    literal b holds b's pieces; another row holds, in each column it does not read, a text that is no piece there."""
    W0 = wc if wc != "o" else self.wo[s]
    ps = [c[1].split(b",") for c in self.classes[(s, 0)] if c[0] == "lit" and c[1].count(b",") + 1 == W0]
    out = []
    for r, t in zip(rows, rty):
        c0, r = self.cls(s, t, 0), (list(r) + [""] * W0)[:W0]
        for k in range(1, W0 + 1):
            if c0[0] == "lit":
                r[k - 1] = c0[1].split(b",")[k - 1].decode("utf-8")
            elif k not in self.cols[s]:
                taken = {D.skeleton(p[k - 1].decode("utf-8")) for p in ps}
                av = [w for w in "pqrstuvwxyz" if D.skeleton(w) not in taken]
                r[k - 1] = av[seed % len(av)]   # (3.13b) moved on by the seed: a line's spelling is free there
        out.append(r)
    return out


def lay_of(self, s, case, x):
    """(3.12b) the layout a solution x is in (one column when its atoms hold there); (3.13h) a file read by both: its width."""
    if s in self.tw:
        if case[s].wc != "o":
            return case[s].wc
        L, m = self.smin(s, case, 1)
        none = [t for t in sorted(self.tok[(s, "o")]) if self.st_len[(s, t, 1)] is None]
        ok = all(x.get(("n", s, t), 0) == 0 for t in none) and not any(t in none for t in case[s].types)
        return 1 if ok and x.get(("n", s, "size"), 0) >= m + sum(a * x.get(next(iter(v)), 0) for a, v in L) else self.wo2[s]
    L, m = self.smin(s, case, 1)
    ok = all(self.st_len[(s, t)] is not None or x.get(("n", s, t), 0) == 0 for t in self.types[s]) and all(self.st_len[(s, t)] is not None for t in case[s].types)
    return 1 if ok and x.get(("n", s, "size"), 0) >= m + sum(a * x.get(v and next(iter(v)), 0) for a, v in L) else 2


def inside_sum(self, st, x):
    """A summed type at x: no rows and sum 0, or rows and each sum strictly inside its class times its rows."""
    s, t = st
    n = x.get(("n", s, t), 0)
    for k in self.cols[s]:
        c, y = self.cls(s, t, k), x.get(("z", "y", s, t, k), 0)
        if self.agg.get((s, k)) in ("sum", "both") and c[0] == "iv" and (y != 0 if n == 0 else c[1][0] is not None and y <= n * c[1][0] or c[1][1] is not None and y >= n * c[1][1]):
            return False
    return True


def split(y, n, lo, hi, pay):
    """n decimals in (lo, hi) whose sum is the decimal y (n - 1 equal ones and the rest; SPEC-EXACT 6), each one the
    reader reads (P1), as runs [(value, how many)], or None where that is not found down to the reader's finest step."""
    if n == 1:
        return [(y, 1)] if D.in_r(y) else None
    m = y / n
    gap = min(m - lo if lo is not None else 1, hi - m if hi is not None else 1)
    d = 1
    while d <= 10 ** -D.LOW:
        pay[0] += 1
        a = D.Fraction(D.floor(m * d), d)
        if abs(a - m) * (n - 1) < gap and D.in_r(a) and D.in_r(y - (n - 1) * a):
            return [(a, n - 1), (y - (n - 1) * a, 1)]
        d *= 10
    return None


def spell1(m, w, c, t):
    for lx in range(0, 7):
        for xs in ((0, 1) if lx else (0,)):
            rest = m - (1 + xs + lx if lx else 0)
            for lb in range(0, rest):
                la = rest - (1 + lb if lb else 0)
                if la < 1 or la + lb > D.R.MAX_DIGITS:
                    continue
                hi = min(10 ** lx - 1, D.R.MAX_EXPONENT) if lx else 0
                E = (0 if not w else min(hi, t + lb)) if la == 1 else len(str(c)) + t - la
                if not (-hi if xs else 0) <= E <= hi or (w and t - E + lb < 0):
                    continue
                M = c * 10 ** (t - E + lb) if w else 0
                if not (M < 10 ** (1 + lb) if la == 1 else 10 ** (la - 1 + lb) <= M < 10 ** (la + lb)):
                    continue
                ds = str(M).rjust(la + lb, "0")
                s = ds[:la] + ("." + ds[la:] if lb else "") + ("e" + ("-" if E < 0 else "+" if xs else "") + str(abs(E)).rjust(lx, "0") if lx else "")
                return s
    return None


def rspell(n, v):
    """One spelling of v in exactly n bytes, or None (then v is no number of n bytes)."""
    w = abs(D.Fraction(v))
    ct = dec_ct(w) if w else (0, 0)
    if ct is None or n > D.RAW_LONG:
        return None
    c, t = ct
    for neg in ((v < 0,) if v else (False, True)):   # 0 also as '-0'
        s = spell1(n - neg, w, c, t)
        if s is not None:
            return ("-" if neg else "") + s
    return None


def dec_ct(w):
    """w > 0 as c·10^t, c an integer not ending in 0; None when w is no decimal."""
    d, k = w.denominator, 0
    while d % 10 == 0 or d % 2 == 0 or d % 5 == 0:
        d, k = (d // 10, k + 1) if d % 10 == 0 else (d // 2, k + 1) if d % 2 == 0 else (d // 5, k + 1)
    if d != 1:
        return None
    c, t = w.numerator * 10 ** k // w.denominator, -k
    while c % 10 == 0:
        c, t = c // 10, t + 1
    return c, t


def nii2(dims, t, u):
    """A NIfTI-2 header: dims, pixdim[4] = t in unit u (SPEC-EXACT 6)."""
    b = bytearray(544)
    D.struct.pack_into("<i", b, 0, 540)
    b[4:12] = b"n+2\x00\r\n\x1a\n"
    D.struct.pack_into("<2h", b, 12, 2, 8)
    D.struct.pack_into("<8q", b, 16, len(dims), *dims, *[1] * (7 - len(dims)))
    D.struct.pack_into("<8d", b, 104, 1, 1, 1, 1, t, 0, 0, 0)
    D.struct.pack_into("<q", b, 168, 544)
    D.struct.pack_into("<i", b, 500, u | 2)
    return bytes(b)


def bold(tr, v, d4):
    """A BOLD image (NIfTI-2, dims 1 x 1 x 1 [x v], a byte per voxel): pixdim[4] the float64 nearest to tr in s, or in us
    below 2^-1075 s (SPEC-EXACT 3.8)."""
    u = 8 if D.B.nearest(tr, 2) > 0 else 24
    return nii2((1, 1, 1, v) if d4 else (1, 1, 1), float(D.B.nearest(tr / D.R.TIME_UNITS[u], 2)), u) + bytes(v if d4 else 1)


def merge_chains(chains):
    """(3.9d) one order of the items of chains (each a sequence; shared items in one relative order in all) that keeps
    every chain's order: repeatedly the first chain head no chain holds later."""
    chains, out = [list(dict.fromkeys(c)) for c in chains], []
    while any(chains):
        h = next(c[0] for c in chains if c and not any(c[0] in d[1:] for d in chains))
        out.append(h)
        chains = [[y for y in c if y != h] for c in chains]
    return out


def W_split_int(y, n):
    """(R1) n whole numbers adding up to y, as equal as can be."""
    y = int(y)
    return [y // n + (j < y % n) for j in range(n)]


def _cols(tsv):
    lines = tsv.decode("utf-8", "surrogateescape").split("\n")[:-1]
    return lines[0].split("\t"), [ln.split("\t") for ln in lines[1:]]


def _dataset(info, ptsv, over):
    """One made-up dataset: the participants candidate, one BOLD recording (with its own sidecar
    and events) per recording the statement names, and a T1w image for every other subject."""
    files = {"dataset_description.json": b'{"Name": "witness", "BIDSVersion": "1.0.1"}', "README": b"witness\n"}
    hs, rows = _cols(ptsv)
    if "participant_id" not in hs:   # it is the first column (S0556, BB's call 12); one named only by position 1 becomes it
        hs, rows = (hs, rows) if hs[0] in ("c1", "d1") else (["participant_id"] + hs, [[""] + r for r in rows])
        hs = ["participant_id"] + hs[1:]
    i = hs.index("participant_id")
    hs, rows = [hs[i]] + hs[:i] + hs[i + 1:], [[r[i]] + r[:i] + r[i + 1:] for r in rows]
    need = list(info["subs"])
    rows += [["n/a"] * len(hs) for _ in range(len(need) - len(rows))]
    pool = [x for x in info["ids"] if x not in need] + [f"w{i}" for i in range(1, len(rows) + 1)]
    labels = need + [w for w in pool if w not in need][:len(rows) - len(need)]
    for r, lab in zip(rows, labels):
        r[hs.index("participant_id")] = "sub-" + lab
    files["participants.tsv"] = ("\n".join("\t".join(r) for r in [hs] + rows) + "\n").encode("utf-8", "surrogateescape")
    recs = list(info["recs"])
    for t in info.get("tasks", []):
        recs += [{"sub": lab, "task": t} for lab in labels if {"sub": lab, "task": t} not in recs]
    for j, ents in enumerate(recs):
        ev, tr, v = over.get(j if j < len(info["recs"]) else "auto", (None, None, None))
        tr = tr or D.W.Fraction(2)
        eh, er = _cols(ev) if ev else (["onset", "duration"], [["0.5", "1"]])
        eh = [{"c1": "onset", "d1": "onset", "c2": "duration", "d2": "duration"}.get(h, h) for h in eh]
        if eh[:1] != ["onset"]:
            eh, er = ["onset"] + eh, [["0.5"] + r for r in er]
        if eh[1:2] != ["duration"]:
            eh, er = eh[:1] + ["duration"] + eh[1:], [r[:1] + ["1"] + r[1:] for r in er]
        ons = [D.W.R.decimal(r[0]) for r in er]
        if v is None:
            v = max([5] + [int(o / tr) + 2 for o in ons if o is not None])
        if D.W.dec_text(tr) is None or v > 100_000 or "sub" not in ents or "task" not in ents:
            return None
        stem = "sub-{0}/func/sub-{0}_task-{1}".format(ents["sub"], ents["task"]) + "".join(f"_{k}-{ents[k]}" for k in ("acq", "rec", "run") if k in ents)
        files[stem + "_bold.nii"] = D.W._nii((1, 1, 1, v), tr)
        files[stem + "_bold.json"] = ('{"TaskName": "%s", "RepetitionTime": %s}' % (ents["task"], D.W.dec_text(tr))).encode()
        files[stem + "_events.tsv"] = ("\n".join("\t".join(r) for r in [eh] + er) + "\n").encode("utf-8", "surrogateescape")
    for lab in labels:
        if not any(p.startswith(f"sub-{lab}/") for p in files):
            files[f"sub-{lab}/anat/sub-{lab}_T1w.nii"] = D.W._nii((1, 1, 1), 1)
    blobs = {D.W.hashlib.sha256(b).hexdigest(): b for b in files.values()}
    man = (D.W.R.MANIFEST_MAGIC + "\n" + "".join(f"{D.W.hashlib.sha256(files[p]).hexdigest()}\t{len(files[p])}\t{p}\n" for p in sorted(files, key=lambda p: p.encode("utf-8", "surrogateescape")))).encode("utf-8", "surrogateescape")
    mh = D.W.hashlib.sha256(man).hexdigest()
    blobs[mh] = man
    return blobs, mh
