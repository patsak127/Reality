# Row 1 holds U+2028 LINE SEPARATOR and row 2 a form feed: both end a line for Python's
# str.splitlines() and for Unicode. Row 3 is "q<TAB>"<TAB>9: two cells under CSV-style quoting,
# three under Reality's reader. A CR in the same places is refused (T002) as "two readings".
file f = sha256:4c96ebade5fe6bf72b8c4d6f3b29fdf5c025b8ad4d2aa933ea41c30503ceed8e
let t = tsv(f)
claim rows(t) is 3
claim cell(t, 1, 1)
claim cell(t, 3, 1)
claim cell(t, 3, 2)
