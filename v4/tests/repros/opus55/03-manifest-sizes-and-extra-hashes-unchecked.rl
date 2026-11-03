# The manifest states participants.tsv is 1 byte (it is 3002) and lists KEYS.txt with a hash
# no file has. Neither is checked; BIDS claims form on this manifest.
dataset d = sha256:43b12e773af54bb0caa8cbf6cff2635e3732de36a6da095320c957aa2d8df092
file p = sha256:d127d700f9a519338da295ea56455bf7bb46ca572f726da72ef7b57c310687b8
claim count(where(participants(bids(d)), eq("group", "equalRange"))) is 54
claim size(p) is 3002
