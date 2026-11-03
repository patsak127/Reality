# Finding 02: a condition that no cell of any table Reality reads can meet, or fail, forms.
# A cell can never hold a double quote: the TSV reader refuses every file with one (T005;
# BIDS TSVs: B04). v3 refuses the same situation for a TAB literal (S008, "no cell holds").
file f = sha256:71b87b82cad447a40934dfc1ad1bfc91d6864e86a36df871209170a9c0763e2e
let t = tsv(f)
claim count(where(t, ne(2, "\"")))
claim count(where(t, eq(2, "\""))) is 0
claim share(where(t, ne(2, "\""))) is 3/3
# For comparison, the TAB literal (a real TAB byte inside the string) is refused:
claim count(where(t, ne(2, "a	b")))
