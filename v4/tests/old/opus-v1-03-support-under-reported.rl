use si
# The value 'delay' comes from a procedure that rests on an outside reference (a DOI "TBD",
# never read). Events built from it, and the observation itself, print a support without it.
entity Participant
artifact t = file "people.tsv" sha256 "dbc46c0f50eccb287c55ab1c9c846fa1e7b6e833af47ee8ea711825dc7278ace"
artifact paper = ref doi "TBD"
procedure guess from paper
frame lab origin o from t row 1
individual s1 : Participant from t row 1
observation delay { of: s1, aspect: Time, value: 3 second, by: guess, at: o, source: t row 1 }
event e1 = delay after o in lab
event e2 at (t: delay, x: 0 metre) in lab
ask delay
ask elapsed[lab](o, e1)
ask elapsed[lab](o, e2)
