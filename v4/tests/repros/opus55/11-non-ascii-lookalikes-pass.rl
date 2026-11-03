# 11-lookalikes.tsv: row 2's id is CYRILLIC DZE + "1" (renders as "S1"); row 2's group is
# "equalR" + CYRILLIC SMALL A + "nge" (renders as "equalRange"); row 3's group is "equaIRange"
# (ASCII capital I); header 3 is "gr" + CYRILLIC SMALL O + "up" (renders as "group").
file f = sha256:cb9bc0a90d4bcefe9004353efd7e981f99087dea397048a176ac9bd533d51ceb
let t = tsv(f)
claim cell(t, key(1, "S1"), 2)
claim count(where(t, eq(1, "S1")))
claim count(where(t, eq("group", "equalR\xd0\xb0nge")))
claim count(where(t, eq(2, "equalRange")))
