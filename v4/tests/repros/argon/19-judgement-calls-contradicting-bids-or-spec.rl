dataset d = sha256:dafc3f597eaf2294b56e854230490e78c784ebffbd4fc5909f48a6643171a411
file p = sha256:9ae996d8f1c85a95ea6596105e5f88d36b447659fabb63e4145616c4560f64d5
file qt = sha256:43707213916dea8844fd77840f1c35f79f430d1c0a325549be46708c8aa18d5f
claim cell(tsv(p), 1, 2) is "\"quoted free text\""
claim rows(participants(bids(d))) is 1
claim rows(tsv(qt)) is 1
