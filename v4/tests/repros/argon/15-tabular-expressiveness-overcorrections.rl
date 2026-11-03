file f = sha256:dc95e0ed139ac3fbb66258205a33340289b885360b39ca6ccf80d34d2964513e
claim cell(tsv(f), key("subject", "sub01"), "rt") is "0.45"
let s1 = where(tsv(f), eq("subject", "sub01"))
claim count(where(s1, eq("trial", "t1"))) is 1
