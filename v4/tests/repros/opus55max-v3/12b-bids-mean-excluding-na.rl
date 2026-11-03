dataset d = sha256:9d661a57dcadb7f8ce968b1cb52f48bad5010ffbf82f2c3f06c8c37df7e26330
let b = bids(d)
let known = where(participants(b), ne("age", "n/a"))
claim count(known)
claim mean(known, "age")
