use si
entity Participant
individual a : Participant
individual b : Participant
let all = {a, b}
let excluded = {b}
ask count(excluded) / count(all)
