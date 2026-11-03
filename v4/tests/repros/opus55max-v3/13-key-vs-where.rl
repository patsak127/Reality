# Finding 13: one standard of "idle" in key(), another in where().
# In this table "sub03" alone picks one row. key() refuses the redundant "trial" part as idle
# (S008, judged on these bytes); where() accepts exactly the same redundant condition, and also
# accepts a condition that removes no row of these bytes.
file f = sha256:9753ff2a3680949d679f55a475bdc58b4a906181d236c39c4adccdb1e8967ce8
let t = tsv(f)
claim cell(t, key("subject", "sub03", "trial", "t3"), "rt")
claim count(where(t, eq("subject", "sub03"), eq("trial", "t3"))) is 1
claim cell(t, key("subject", "sub03"), "rt") is "0.8"
claim count(where(t, ne("trial", "t9"))) is 5
